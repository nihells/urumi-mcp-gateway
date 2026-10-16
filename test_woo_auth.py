import os
import asyncio
import httpx

async def main():
    url = os.environ["WOOCOMMERCE_URL"].rstrip("/")
    key = os.environ["WOOCOMMERCE_CONSUMER_KEY"]
    secret = os.environ["WOOCOMMERCE_CONSUMER_SECRET"]

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            f"{url}/wp-json/wc/v3/products",
            params={"per_page": 1},
            auth=(key, secret),
        )

    print("HTTP status:", response.status_code)

    if response.status_code == 200:
        print("WooCommerce authentication successful.")
        print("Product data received:", isinstance(response.json(), list))
    elif response.status_code in (401, 403):
        print("Authentication or permission rejected.")
    else:
        print("Request failed. Response body:", response.text[:300])

asyncio.run(main())