import getpass
import json
import requests

BASE_URL = "http://127.0.0.1:8010"
MCP_URL = f"{BASE_URL}/mcp/"

api_key = getpass.getpass("Enter an active member API key: ")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

def mcp_request(payload):
    response = requests.post(
        MCP_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    print("HTTP status:", response.status_code)

    if response.status_code != 200:
        print("Request failed:", response.text[:500])
        return None

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()

    # Streamable HTTP may return Server-Sent Events.
    for line in response.text.splitlines():
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue

    print("Could not parse MCP response.")
    return None

try:
    # 1. Discover the available tools.
    result = mcp_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    })

    if result:
        tools = result.get("result", {}).get("tools", [])
        print("Tools discovered:", len(tools))
        for tool in tools:
            print("-", tool["name"])

        # 2. Make a read-only call to list WooCommerce orders.
        if any(t["name"] == "woocommerce__list_orders" for t in tools):
            result = mcp_request({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "woocommerce__list_orders",
                    "arguments": {},
                },
            })
            if result:
                print("Tool-call response received.")
                print(json.dumps(result, indent=2)[:1500])
        else:
            print("Read-only WooCommerce order tool not available.")

except requests.RequestException as exc:
    print("Connection error:", exc)
finally:
    api_key = None
    headers = None