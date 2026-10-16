import asyncio
import json
import math
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
import requests
from requests_oauthlib import OAuth1
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


# --------------------------------------------------
# WooCommerce configuration
# --------------------------------------------------

STORE_URL = os.environ.get(
    "WOOCOMMERCE_URL",
    "http://urumi-wordpress.urumi.svc.cluster.local",
).rstrip("/")

# WordPress uses this URL when validating OAuth signatures.
OAUTH_SIGNATURE_URL = os.environ.get(
    "WOOCOMMERCE_OAUTH_SIGNATURE_URL",
    "http://shop.urumi.local",
).rstrip("/")

CONSUMER_KEY = os.environ.get("WOOCOMMERCE_CONSUMER_KEY", "")
CONSUMER_SECRET = os.environ.get("WOOCOMMERCE_CONSUMER_SECRET", "")

if not CONSUMER_KEY or not CONSUMER_SECRET:
    raise RuntimeError(
        "WooCommerce API credentials must be configured."
    )


# --------------------------------------------------
# MCP server configuration
# --------------------------------------------------

mcp = FastMCP(
    "WooCommerce MCP Server",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
)


# --------------------------------------------------
# Validation helpers
# --------------------------------------------------

def validate_limit(limit: int, maximum: int = 100) -> int:
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= maximum
    ):
        raise ValueError(f"limit must be between 1 and {maximum}.")

    return limit


# --------------------------------------------------
# WooCommerce HTTP authentication
# --------------------------------------------------

def _oauth_request(
    method: str,
    url: str,
    params: dict[str, Any] | None,
    payload: dict[str, Any] | None,
) -> tuple[int, str]:
    """Sign using the WordPress site URL and connect internally."""

    # The internal service and public site must use the same API path.
    internal = urlsplit(url)
    signing_base = urlsplit(OAUTH_SIGNATURE_URL)

    if not internal.scheme or not internal.netloc:
        raise ValueError("Invalid internal WooCommerce URL.")

    if not signing_base.scheme or not signing_base.netloc:
        raise ValueError("Invalid OAuth signature URL.")

    # Construct the URL used for signing, retaining the API path.
    signing_url = urlunsplit((
        signing_base.scheme,
        signing_base.netloc,
        internal.path,
        "",
        "",
    ))

    auth = OAuth1(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        signature_method="HMAC-SHA1",
        signature_type="QUERY",
    )

    # Prepare OAuth parameters against WordPress's configured URL.
    prepared = requests.Request(
        method=method,
        url=signing_url,
        params=params,
        json=payload,
        auth=auth,
    ).prepare()

    # Connect to the internal Kubernetes service while preserving
    # the OAuth parameters and signature generated above.
    signed_query = urlsplit(prepared.url).query
    internal_url = urlunsplit((
        internal.scheme,
        internal.netloc,
        internal.path,
        signed_query,
        "",
    ))

    response = requests.request(
        method=method,
        url=internal_url,
        json=payload,
        timeout=15,
        allow_redirects=False,
    )

    return response.status_code, response.text


async def woo_request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> Any:
    """Execute an authenticated WooCommerce REST API request."""

    url = f"{STORE_URL}/wp-json/wc/v3/{path.lstrip('/')}"

    if STORE_URL.startswith("https://"):
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=payload,
                auth=(CONSUMER_KEY, CONSUMER_SECRET),
            )

        status_code = response.status_code
        response_text = response.text

    elif STORE_URL.startswith("http://"):
        status_code, response_text = await asyncio.to_thread(
            _oauth_request,
            method,
            url,
            params,
            payload,
        )

    else:
        raise ValueError(
            "WOOCOMMERCE_URL must use HTTP or HTTPS."
        )

    if 300 <= status_code < 400:
        raise RuntimeError(
            "WooCommerce returned a redirect. Check the store URL "
            "and WordPress site URL."
        )

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(
            f"WooCommerce API returned HTTP {status_code}: "
            f"{response_text[:500]}"
        )

    try:
        return json.loads(response_text)
    except ValueError as exc:
        raise RuntimeError(
            "WooCommerce returned an invalid JSON response."
        ) from exc


# --------------------------------------------------
# Tool 1: List products
# --------------------------------------------------

@mcp.tool()
async def list_products(limit: int = 10) -> list[dict[str, Any]]:
    """List WooCommerce products, including ID, name, price and stock status."""

    limit = validate_limit(limit)

    products = await woo_request(
        "GET",
        "products",
        params={"per_page": limit},
    )

    return [
        {
            "id": item["id"],
            "name": item["name"],
            "price": item["price"],
            "status": item["status"],
            "stock_status": item["stock_status"],
        }
        for item in products
    ]


# --------------------------------------------------
# Tool 2: Create product
# --------------------------------------------------

@mcp.tool()
async def create_product(
    name: str,
    regular_price: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a published WooCommerce simple product."""

    if not name or not name.strip() or len(name) > 200:
        raise ValueError(
            "Product name must contain 1–200 characters."
        )

    if len(description) > 5000:
        raise ValueError(
            "Description must not exceed 5000 characters."
        )

    try:
        price = float(regular_price)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "regular_price must be a valid non-negative number."
        ) from exc

    if not math.isfinite(price) or price < 0:
        raise ValueError(
            "regular_price must be a valid non-negative number."
        )

    result = await woo_request(
        "POST",
        "products",
        payload={
            "name": name.strip(),
            "type": "simple",
            "regular_price": format(price, ".2f"),
            "description": description,
            "status": "publish",
        },
    )

    return {
        "id": result["id"],
        "name": result["name"],
        "price": result["price"],
        "status": result["status"],
    }


# --------------------------------------------------
# Tool 3: List orders
# --------------------------------------------------

@mcp.tool()
async def list_orders(
    limit: int = 10,
    after: str | None = None,
    before: str | None = None,
) -> list[dict[str, Any]]:
    """List WooCommerce orders, including their products and date range.

    Args:
        limit: Maximum number of orders to return (1-100).
        after: Optional ISO-8601 timestamp; only return orders created after it.
        before: Optional ISO-8601 timestamp; only return orders created before it.

    For requests such as "orders received today", provide both `after` and
    `before` to bound the query to the store's relevant calendar day. Timestamps
    should use the WooCommerce store's expected timezone/format.
    """

    limit = validate_limit(limit)

    params: dict[str, Any] = {"per_page": limit}

    # Validate date filters locally so invalid input produces a clear tool error.
    for field_name, value in (("after", after), ("before", before)):
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty ISO-8601 timestamp.")
            try:
                datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(
                    f"{field_name} must be a valid ISO-8601 timestamp."
                ) from exc
            params[field_name] = value.strip()

    orders = await woo_request(
        "GET",
        "orders",
        params=params,
    )

    return [
        {
            "id": item["id"],
            "status": item["status"],
            "total": item["total"],
            "currency": item["currency"],
            "date_created": item.get("date_created"),
            "date_created_gmt": item.get("date_created_gmt"),
            "line_items": [
                {
                    "product_id": line_item.get("product_id"),
                    "name": line_item.get("name", "Unknown product"),
                    "quantity": line_item.get("quantity", 0),
                    "total": line_item.get("total", "0.00"),
                }
                for line_item in item.get("line_items", [])
            ],
        }
        for item in orders
    ]


# --------------------------------------------------
# Tool 4: Get a specific order
# --------------------------------------------------

@mcp.tool()
async def get_order(order_id: int) -> dict[str, Any]:
    """Retrieve a WooCommerce order by its numeric ID."""

    if (
        not isinstance(order_id, int)
        or isinstance(order_id, bool)
        or order_id <= 0
    ):
        raise ValueError("order_id must be a positive integer.")

    order = await woo_request("GET", f"orders/{order_id}")

    return {
        "id": order["id"],
        "status": order["status"],
        "total": order["total"],
        "currency": order["currency"],
        "date_created": order["date_created"],
        "line_items": [
            {
                "product_id": item["product_id"],
                "name": item["name"],
                "quantity": item["quantity"],
                "total": item["total"],
            }
            for item in order.get("line_items", [])
        ],
    }


# --------------------------------------------------
# Tool 5: Update order status
# --------------------------------------------------

@mcp.tool()
async def update_order_status(
    order_id: int,
    status: str,
) -> dict[str, Any]:
    """Update an order to an allowed WooCommerce status."""

    if (
        not isinstance(order_id, int)
        or isinstance(order_id, bool)
        or order_id <= 0
    ):
        raise ValueError("order_id must be a positive integer.")

    allowed_statuses = {
        "pending",
        "processing",
        "on-hold",
        "completed",
        "cancelled",
        "refunded",
        "failed",
    }

    if status not in allowed_statuses:
        raise ValueError(
            "Unsupported status. Choose one of: "
            + ", ".join(sorted(allowed_statuses))
        )

    order = await woo_request(
        "PUT",
        f"orders/{order_id}",
        payload={"status": status},
    )

    return {
        "id": order["id"],
        "status": order["status"],
        "total": order["total"],
    }


# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

async def health(_request):
    return JSONResponse({
        "status": "ok",
        "service": "woo-mcp-server",
    })


# --------------------------------------------------
# Starlette application
# --------------------------------------------------

@asynccontextmanager
async def lifespan(_app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route(
            "/mcp",
            mcp.streamable_http_app(),
            methods=["GET", "POST", "DELETE"],
        ),
    ],
    lifespan=lifespan,
)