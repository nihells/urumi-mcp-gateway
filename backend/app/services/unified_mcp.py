import json
import time
from contextvars import ContextVar
from typing import Any

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from app.database import SessionLocal
from app.models import ApiKey, AuditLog, MCPServer, User
from app.security import hash_api_key
from app.services.gateway import MCPGateway


gateway = MCPGateway(timeout_seconds=20.0)

# Holds the authenticated user ID for the current request.
request_user_context: ContextVar[int | None] = ContextVar(
    "request_user_context",
    default=None,
)

# Only administrators may use these mutating WooCommerce tools.
# Keep these names aligned with the gateway's server-prefixed tool names.
ADMIN_ONLY_TOOLS = {
    "woocommerce__create_product",
    "woocommerce__update_order_status",
}


def get_user_role(user_id: int) -> str | None:
    """Return the role for an existing, active user."""
    db: Session = SessionLocal()

    try:
        user = db.get(User, user_id)
        if user is None or not user.active:
            return None
        return user.role
    finally:
        db.close()


def authenticate_api_key(raw_key: str) -> int | None:
    """Return the active user's ID for a valid, non-revoked API key."""
    if not raw_key:
        return None

    db: Session = SessionLocal()

    try:
        key_hash = hash_api_key(raw_key)

        record = (
            db.query(ApiKey)
            .filter(
                ApiKey.key_hash == key_hash,
                ApiKey.revoked.is_(False),
            )
            .first()
        )

        if record is None:
            return None

        user = db.get(User, record.user_id)
        if user is None or not user.active:
            return None

        return user.id
    finally:
        db.close()


class ApiKeyAuthMiddleware:
    """Protect every request to the unified MCP endpoint."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }

        authorization = headers.get(b"authorization", b"").decode(
            "utf-8",
            errors="ignore",
        )

        scheme, separator, token = authorization.partition(" ")
        user_id = None

        if separator and scheme.lower() == "bearer" and token.strip():
            user_id = authenticate_api_key(token.strip())

        if user_id is None:
            body = json.dumps(
                {"detail": "Invalid or missing API key."}
            ).encode("utf-8")

            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"www-authenticate", b"Bearer"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )
            return

        token_context = request_user_context.set(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            request_user_context.reset(token_context)


def get_enabled_servers() -> list[dict[str, Any]]:
    db = SessionLocal()

    try:
        return [
            {
                "id": server.id,
                "name": server.name,
                "url": server.url,
            }
            for server in (
                db.query(MCPServer)
                .filter(MCPServer.enabled.is_(True))
                .order_by(MCPServer.id)
                .all()
            )
        ]
    finally:
        db.close()


async def discover_all_tools() -> list[dict[str, Any]]:
    """Discover tools from enabled upstream MCP servers."""
    discovered = []
    used_names = set()

    for server in get_enabled_servers():
        try:
            tools = await gateway.discover_tools(
                server_name=server["name"],
                server_url=server["url"],
            )

            for tool in tools:
                public_name = tool.public_name

                # Do not expose ambiguous names if prefixes collide.
                if public_name in used_names:
                    continue

                used_names.add(public_name)
                discovered.append(
                    {
                        "name": public_name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                    }
                )
        except Exception:
            # One unavailable server must not disable other servers.
            continue

    return discovered


async def call_unified_tool(
    public_name: str,
    arguments: dict[str, Any],
    user_id: int,
) -> dict[str, Any]:
    """Route a tool call, enforce role permissions, and audit its outcome."""
    started = time.perf_counter()
    server_name = "unknown"
    outcome = "error"
    error_message = None

    try:
        if "__" not in public_name:
            raise ValueError("Invalid tool name.")

        prefix, original_name = public_name.split("__", 1)
        servers = get_enabled_servers()

        matching_servers = [
            item
            for item in servers
            if gateway.safe_prefix(item["name"]) == prefix
        ]

        if len(matching_servers) != 1:
            raise ValueError("Unknown, disabled, or ambiguous MCP server.")

        server = matching_servers[0]
        server_name = server["name"]

        # Enforce permissions here so MCP clients, dashboard REST calls,
        # and chat-agent calls all pass through the same policy.
        if public_name in ADMIN_ONLY_TOOLS:
            role = get_user_role(user_id)
            if role is None:
                raise PermissionError("Access denied: active user required.")
            if role != "admin":
                raise PermissionError(
                    f"Access denied: {public_name} is restricted to administrators."
                )

        result = await gateway.call_tool(
            server_name=server_name,
            server_url=server["url"],
            tool_name=original_name,
            arguments=arguments,
        )

        outcome = "error" if result.get("is_error") else "success"
        if outcome == "error":
            error_message = "Upstream MCP tool returned an error."

        return result

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        raise

    finally:
        # Rejected calls are also recorded in the audit trail.
        db = SessionLocal()
        try:
            db.add(
                AuditLog(
                    user_id=user_id,
                    server_name=server_name,
                    tool_name=public_name,
                    duration_ms=int(
                        (time.perf_counter() - started) * 1000
                    ),
                    outcome=outcome,
                    error_message=error_message,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


mcp_server = Server(
    "urumi-mcp-gateway",
    version="0.1.0",
    instructions=(
        "Unified MCP gateway. Tools are routed to enabled upstream "
        "MCP servers and tool calls are audited. Mutating WooCommerce "
        "tools are restricted to administrators."
    ),
)


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List enabled tools filtered by the authenticated user's role."""
    user_id = request_user_context.get()
    if user_id is None:
        raise RuntimeError("Authentication required.")

    role = get_user_role(user_id)
    if role is None:
        raise RuntimeError("Active user required.")

    discovered = await discover_all_tools()

    if role != "admin":
        discovered = [
            item
            for item in discovered
            if item["name"] not in ADMIN_ONLY_TOOLS
        ]

    return [
        Tool(
            name=item["name"],
            description=item["description"],
            inputSchema=item["inputSchema"],
        )
        for item in discovered
    ]


@mcp_server.call_tool()
async def call_tool(
    name: str,
    arguments: dict[str, Any] | None,
) -> list[TextContent]:
    # ContextVar.get() retrieves the authenticated user for this request.
    user_id = request_user_context.get()
    if user_id is None:
        raise RuntimeError("Authentication required.")

    result = await call_unified_tool(
        public_name=name,
        arguments=arguments or {},
        user_id=user_id,
    )

    return [
        TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, default=str),
        )
    ]


# Stateless HTTP sessions avoid carrying authentication context
# between different clients' requests.
session_manager = StreamableHTTPSessionManager(
    app=mcp_server,
    json_response=True,
    stateless=True,
)


class UnifiedMCPASGIApp:
    """Run the MCP session manager as an authenticated ASGI application."""

    def __init__(self):
        self.authenticated_app = ApiKeyAuthMiddleware(self._handle_request)

    async def _handle_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await session_manager.handle_request(scope, receive, send)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        await self.authenticated_app(scope, receive, send)


unified_mcp_app = UnifiedMCPASGIApp()
