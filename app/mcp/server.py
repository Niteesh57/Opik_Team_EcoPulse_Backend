import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP

# =========================
# MCP SERVER SETUP
# =========================

mcp = FastMCP(
    "Amazon Scraper",
    instructions="""
    Amazon product scraper MCP server.

    Tools:
    - scrape_product(product_url)
    - search_products(query, max_results)

    Extracts:
    - Product name
    - Price
    - Image
    - Rating
    - Reviews
    """
)

# =========================
# HELPERS
# =========================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

async def fetch_page(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text

def clean_price(text: str) -> str:
    if not text:
        return "Price not available"
    match = re.search(r"[\d,.]+", text)
    return f"${match.group()}" if match else "Price not available"

def extract_asin(url: str) -> str | None:
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else None

# =========================
# PRODUCT PAGE SCRAPER
# =========================

def extract_product(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    data = {
        "name": "Not found",
        "price": "Not available",
        "image": "Not found",
        "rating": "Not available",
        "reviews": "Not available",
        "url": url
    }

    title = soup.select_one("#productTitle")
    if title:
        data["name"] = title.get_text(strip=True)

    price = soup.select_one(".a-price .a-offscreen")
    if price:
        data["price"] = clean_price(price.text)

    img = soup.select_one("#landingImage")
    if img:
        data["image"] = img.get("src")

    rating = soup.select_one(".a-icon-alt")
    if rating:
        data["rating"] = rating.text

    reviews = soup.select_one("#acrCustomerReviewText")
    if reviews:
        data["reviews"] = reviews.text

    return data

# =========================
# SEARCH RESULTS SCRAPER
# =========================

def extract_search_results(html: str, base_domain: str, max_results: int) -> list:
    soup = BeautifulSoup(html, "html.parser")
    products = []

    results = soup.select('[data-component-type="s-search-result"]')

    for item in results:
        if len(products) >= max_results:
            break

        title_link = item.select_one("h2 a")
        if not title_link:
            continue

        href = title_link.get("href", "")
        if "/dp/" not in href:
            continue

        clean_url = base_domain + href.split("?")[0]
        asin = extract_asin(clean_url)
        if not asin:
            continue

        name = title_link.select_one("span")
        price = item.select_one(".a-price .a-offscreen")
        image = item.select_one("img.s-image")
        rating = item.select_one(".a-icon-alt")

        products.append({
            "name": name.text.strip() if name else "Not found",
            "price": clean_price(price.text) if price else "Not available",
            "image": image.get("src") if image else "Not found",
            "rating": rating.text if rating else "Not available",
            "url": clean_url
        })

    return products

# =========================
# FORMATTERS
# =========================

def format_product(p: dict) -> str:
    return (
        f"# {p['name']}\n\n"
        f"Price: {p['price']}\n"
        f"Rating: {p['rating']}\n"
        f"Reviews: {p['reviews']}\n"
        f"Image: {p['image']}\n"
        f"URL: {p['url']}\n"
    )

def format_search(products: list, query: str) -> str:
    out = f"# Search results for '{query}'\n\n"
    for i, p in enumerate(products, 1):
        out += (
            f"## {i}. {p['name']}\n"
            f"Price: {p['price']}\n"
            f"Rating: {p['rating']}\n"
            f"URL: {p['url']}\n\n"
        )
    return out

# =========================
# MCP TOOLS
# =========================

@mcp.tool()
async def scrape_product(product_url: str) -> str:
    parsed = urlparse(product_url)
    if "amazon" not in parsed.netloc:
        return "Invalid Amazon URL"

    html = await fetch_page(product_url)
    product = extract_product(html, product_url)
    return format_product(product)

@mcp.tool()
async def search_products(query: str, max_results: int = 5) -> str:
    search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
    parsed = urlparse(search_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"

    html = await fetch_page(search_url)
    products = extract_search_results(html, base_domain, max_results)

    if not products:
        return "No products found."

    return format_search(products, query)

# =========================
# START SERVER
# =========================

if __name__ == "__main__":
    print("🚀 Amazon Scraper MCP Server running...")
    mcp.run(transport="stdio")
