import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, MCPServer, User
from app.routers.auth import get_current_user
from app.services.gateway import MCPGateway

router = APIRouter(prefix="/gateway", tags=["MCP Gateway"])

gateway = MCPGateway(timeout_seconds=20.0)

# These exact public tool names are restricted to administrators.
# Keep this policy aligned with backend/app/services/unified_mcp.py.
ADMIN_ONLY_TOOLS = {
    "woocommerce__create_product",
    "woocommerce__update_order_status",
}


class ToolCallRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    arguments: dict = Field(default_factory=dict)


def get_enabled_servers(db: Session):
    """Return enabled MCP servers in a consistent order."""
    return (
        db.query(MCPServer)
        .filter(MCPServer.enabled.is_(True))
        .order_by(MCPServer.id)
        .all()
    )


def find_server_by_prefix(servers, prefix: str):
    """Find a server using the same prefix logic used for discovery."""
    matches = [
        server
        for server in servers
        if gateway.safe_prefix(server.name) == prefix
    ]
    # Refuse ambiguous prefixes rather than silently routing to the first.
    return matches[0] if len(matches) == 1 else None


@router.get("/tools")
async def discover_tools(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Discover enabled upstream tools, filtered by the user's role."""
    servers = get_enabled_servers(db)

    discovered = []
    failures = []

    for server in servers:
        try:
            tools = await gateway.discover_tools(
                server_name=server.name,
                server_url=server.url,
            )

            for tool in tools:
                public_name = tool.public_name

                # Members must not even see administrator-only tools.
                if (
                    current_user.role != "admin"
                    and public_name in ADMIN_ONLY_TOOLS
                ):
                    continue

                discovered.append(
                    {
                        "name": public_name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                        "server": tool.server_name,
                    }
                )

        except Exception as exc:
            causes = []

            for item in getattr(exc, "exceptions", []):
                causes.append(
                    {
                        "type": type(item).__name__,
                        "message": str(item),
                    }
                )

            failures.append(
                {
                    "server": server.name,
                    "error": type(exc).__name__,
                    "details": str(exc),
                    "causes": causes,
                }
            )

    return {
        "tools": discovered,
        "unavailable_servers": failures,
    }


@router.post("/tools/call")
async def call_tool(
    request: ToolCallRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Call an upstream MCP tool with role enforcement and audit logging."""
    started = time.perf_counter()

    server_name = "unknown"
    outcome = "error"
    error_message = None

    try:
        if "__" not in request.name:
            raise HTTPException(
                status_code=400,
                detail="Tool name must include its server prefix.",
            )

        prefix, original_tool_name = request.name.split("__", 1)

        if not prefix or not original_tool_name:
            raise HTTPException(
                status_code=400,
                detail="Invalid tool name. Expected server_prefix__tool_name.",
            )

        servers = get_enabled_servers(db)
        server = find_server_by_prefix(servers, prefix)

        if server is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No unique enabled MCP server matches prefix '{prefix}'. "
                    "Use GET /gateway/tools to retrieve the exact tool name."
                ),
            )

        server_name = server.name

        # Enforce at execution time as well as hiding tools during discovery.
        # The finally block below records denied calls in the audit log.
        if (
            current_user.role != "admin"
            and request.name in ADMIN_ONLY_TOOLS
        ):
            error_message = "Access denied: tool is restricted to administrators."
            raise HTTPException(
                status_code=403,
                detail=error_message,
            )

        result = await gateway.call_tool(
            server_name=server.name,
            server_url=server.url,
            tool_name=original_tool_name,
            arguments=request.arguments,
        )

        if result.get("is_error", False):
            outcome = "error"
            error_message = "Upstream MCP tool returned an error."
        else:
            outcome = "success"

        return {
            "server": server.name,
            "tool": request.name,
            "result": result,
        }

    except HTTPException as exc:
        if error_message is None:
            error_message = str(exc.detail)
        raise

    except (TimeoutError, asyncio.TimeoutError) as exc:
        error_message = "Upstream MCP server timed out."

        raise HTTPException(
            status_code=504,
            detail=error_message,
        ) from exc

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {str(exc)}"

        raise HTTPException(
            status_code=502,
            detail="Upstream MCP server call failed.",
        ) from exc

    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)

        try:
            audit_entry = AuditLog(
                user_id=current_user.id,
                server_name=server_name,
                tool_name=request.name,
                duration_ms=duration_ms,
                outcome=outcome,
                error_message=error_message,
            )

            db.add(audit_entry)
            db.commit()

        except Exception:
            db.rollback()
