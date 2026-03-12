# walmart_next_data.py

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


# STEP 1: Live Walmart product URL and output paths
URL = "https://www.walmart.com/ip/Noxzema-Original-Facial-Cleanser-Cream-Daily-Deep-Face-Cleansing-for-All-Skin-Types-12-oz/14122693"
OUTPUT_JSON = "output/walmart_next_data.json"
OUTPUT_CSV = "output/walmart_next_data.csv"
DEBUG_HTML = "output/debug/walmart_next_data.html"
PROFILE_DIR = "output/chrome_profile"


# STEP 2: Clean text safely
def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or None


# STEP 3: Save raw HTML for debugging
def save_debug_html(html: str) -> None:
    Path("output/debug").mkdir(parents=True, exist_ok=True)
    with open(DEBUG_HTML, "w", encoding="utf-8") as f:
        f.write(html)


# STEP 4: Fetch page HTML with a persistent Playwright browser session
def get_html(url: str) -> Tuple[int, str]:
    """
    Launch a persistent Chromium profile so cookies/storage survive across runs.
    This behaves more like a real browser session than requests or a fresh context.
    """
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,  # keep False while debugging Walmart challenges
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",
            },
            java_script_enabled=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Patch a few obvious automation fingerprints before page scripts run
        context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            """
        )

        page = context.pages[0] if context.pages else context.new_page()
        status_code = 0
        html = ""

        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=90000)
            if response:
                status_code = response.status

            # Let hydration happen
            page.wait_for_timeout(4000)

            # Gentle browser-like movement
            try:
                page.mouse.move(200, 250)
                page.wait_for_timeout(800)
                page.mouse.move(500, 350)
                page.wait_for_timeout(700)
                page.mouse.wheel(0, 500)
                page.wait_for_timeout(1500)
                page.mouse.wheel(0, -200)
                page.wait_for_timeout(1200)
            except Exception:
                pass

            # Check whether Walmart shows a visible challenge
            try:
                body_text = page.locator("body").inner_text(timeout=5000).lower()
            except Exception:
                body_text = ""

            if (
                "press and hold" in body_text
                or "verify you are human" in body_text
                or "robot or human" in body_text
                or "security check" in body_text
            ):
                print("[INFO] Challenge detected in browser. Solve it manually if visible...")
                page.wait_for_timeout(20000)

            # Final wait after possible challenge
            page.wait_for_timeout(5000)
            html = page.content()

        except PlaywrightTimeoutError:
            html = page.content()
        finally:
            context.close()

    return status_code, html


# STEP 5: Detect anti-bot or block pages
def is_block_page(html: str) -> bool:
    text = html.lower()
    blocked_markers = [
        "robot or human",
        "activate and hold the button",
        "sorry for the wait",
        "verify you are human",
        "access denied",
        "captcha",
        "press and hold",
        "are you a human",
        "security check",
        "perimeterx",
        "px-captcha",
    ]
    return any(marker in text for marker in blocked_markers)


# STEP 6: Detect real not-found pages more strictly
def is_not_found_page(status_code: int, html: str) -> bool:
    if status_code == 404:
        return True

    text = html.lower()
    explicit_not_found_markers = [
        "<h1>we couldn’t find this page</h1>",
        "<h1>we couldn't find this page</h1>",
        "<title>page not found",
        "we couldn’t find this page",
        "we couldn't find this page",
    ]
    return any(marker in text for marker in explicit_not_found_markers)


# STEP 7: Confirm page looks like a real product page
def looks_like_product_page(html: str) -> bool:
    text = html.lower()
    positive_signals = [
        "noxzema",
        "12 oz",
        "current price",
        "add to cart",
        "facial cleanser",
        '"@type":"product"',
        '"__typename":"product"',
    ]
    return sum(signal in text for signal in positive_signals) >= 2


# STEP 8: Extract meta tag content
def get_meta_content(soup: BeautifulSoup, attr_name: str, attr_value: str) -> Optional[str]:
    tag = soup.find("meta", attrs={attr_name: attr_value})
    if tag:
        return clean_text(tag.get("content"))
    return None


# STEP 9: Extract JSON-LD if present
def extract_json_ld_product(soup: BeautifulSoup) -> Dict[str, Any]:
    scripts = soup.select('script[type="application/ld+json"]')

    for script in scripts:
        raw = script.string or script.get_text(strip=False)
        if not raw:
            continue

        try:
            obj = json.loads(raw)
        except Exception:
            continue

        items = obj if isinstance(obj, list) else [obj]

        for item in items:
            if not isinstance(item, dict):
                continue

            item_type = str(item.get("@type", "")).lower()
            if "product" in item_type:
                return item

    return {}


# STEP 10: Extract first regex match
def extract_first(pattern: str, text: str, flags: int = 0) -> Optional[str]:
    match = re.search(pattern, text, flags)
    if match:
        return clean_text(match.group(1) if match.groups() else match.group(0))
    return None


# STEP 11: Normalize image URL
def normalize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None

    url = url.strip()

    if url.startswith("//"):
        return f"https:{url}"

    return url


# STEP 12: Filter bad images
def is_valid_image(url: Optional[str]) -> bool:
    if not url:
        return False

    lower = url.lower()
    bad_patterns = [
        "spark-icon",
        "logo",
        "icon",
        "sprite",
        ".svg",
        "data:image/",
    ]
    return not any(p in lower for p in bad_patterns)


# STEP 13: Recursively search JSON for likely product fields
def find_first_key(obj: Any, target_keys: set) -> Optional[Any]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in target_keys and value not in (None, "", [], {}):
                return value
            nested = find_first_key(value, target_keys)
            if nested not in (None, "", [], {}):
                return nested

    elif isinstance(obj, list):
        for item in obj:
            nested = find_first_key(item, target_keys)
            if nested not in (None, "", [], {}):
                return nested

    return None


# STEP 14: Extract product data from __NEXT_DATA__ if present
def extract_from_next_data(html: str) -> Dict[str, Optional[str]]:
    result = {
        "product_name": None,
        "brand": None,
        "price": None,
        "description": None,
        "image": None,
        "size_volume": None,
    }

    match = re.search(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        flags=re.I | re.S,
    )
    if not match:
        return result

    raw_json = match.group(1)

    try:
        data = json.loads(raw_json)
    except Exception:
        return result

    product_name = find_first_key(data, {"productName", "name", "title"})
    brand = find_first_key(data, {"brand", "brandName"})
    price = find_first_key(data, {"price", "currentPrice", "priceString"})
    description = find_first_key(data, {"description", "shortDescription", "longDescription"})
    image = find_first_key(data, {"image", "imageUrl", "thumbnailUrl"})
    size_volume = find_first_key(data, {"size", "sizeVolume", "variantSize"})

    if isinstance(brand, dict):
        brand = brand.get("name") or brand.get("brandName")

    if isinstance(price, (int, float)):
        price = f"${price}"
    elif isinstance(price, str):
        price = clean_text(price)
        if price and re.fullmatch(r"\d+(?:\.\d{1,2})?", price):
            price = f"${price}"

    if isinstance(image, list) and image:
        image = image[0]
    if isinstance(image, dict):
        image = image.get("url") or image.get("imageUrl")

    result["product_name"] = clean_text(str(product_name)) if product_name is not None else None
    result["brand"] = clean_text(str(brand)) if brand is not None else None
    result["price"] = clean_text(str(price)) if price is not None else None
    result["description"] = clean_text(str(description)) if description is not None else None
    result["image"] = normalize_url(clean_text(str(image))) if image is not None else None
    result["size_volume"] = clean_text(str(size_volume)) if size_volume is not None else None

    if not is_valid_image(result["image"]):
        result["image"] = None

    return result


# STEP 15: Main HTML parsing logic
def extract_product_record_from_html(html: str, url: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = clean_text(soup.get_text(" ", strip=True)) or ""

    json_ld = extract_json_ld_product(soup)
    next_data = extract_from_next_data(html)

    # Product name
    product_name = (
        next_data.get("product_name")
        or (clean_text(json_ld.get("name")) if json_ld else None)
        or get_meta_content(soup, "property", "og:title")
    )

    if not product_name:
        product_name = extract_first(
            r"(Noxzema[^|]{0,200}?12\s*oz)",
            page_text,
            flags=re.I,
        )

    # Brand
    brand = next_data.get("brand")
    if not brand and json_ld:
        brand_data = json_ld.get("brand")
        if isinstance(brand_data, dict):
            brand = clean_text(brand_data.get("name"))
        elif isinstance(brand_data, str):
            brand = clean_text(brand_data)

    if not brand:
        brand = extract_first(r"\b(Noxzema)\b", page_text, flags=re.I)

    # Price
    price = next_data.get("price")
    if not price and json_ld:
        offers = json_ld.get("offers")
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            price_val = offers.get("price")
            if price_val is not None:
                price = clean_text(f"${price_val}")

    if not price:
        price = (
            extract_first(r'"price"\s*:\s*"(\d+(?:\.\d{1,2})?)"', html, flags=re.I)
            or extract_first(r'"currentPrice"\s*:\s*"?(\d+(?:\.\d{1,2})?)"?', html, flags=re.I)
            or extract_first(r"\$ ?(\d+(?:\.\d{1,2})?)", page_text, flags=re.I)
        )
        if price and not price.startswith("$"):
            price = f"${price}"

    # Description
    description = (
        next_data.get("description")
        or (clean_text(json_ld.get("description")) if json_ld else None)
        or get_meta_content(soup, "name", "description")
    )

    if not description:
        description = extract_first(
            r"(Daily[^.]{0,250})",
            page_text,
            flags=re.I,
        )

    # Size / volume
    size_volume = (
        next_data.get("size_volume")
        or extract_first(
            r"\b(\d+(?:\.\d+)?\s*(?:oz|fl oz|ml|l|g|kg|lb|ct))\b",
            page_text,
            flags=re.I,
        )
    )

    # Image
    image = (
        next_data.get("image")
        or (
            clean_text(json_ld.get("image")[0])
            if json_ld and isinstance(json_ld.get("image"), list) and json_ld.get("image")
            else None
        )
        or (
            clean_text(json_ld.get("image"))
            if json_ld and isinstance(json_ld.get("image"), str)
            else None
        )
        or get_meta_content(soup, "property", "og:image")
    )

    image = normalize_url(image)
    if not is_valid_image(image):
        image = None

    return {
        "source": "walmart_next_data",
        "url": url,
        "product_name": clean_text(product_name),
        "brand": clean_text(brand),
        "size_volume": clean_text(size_volume),
        "price": clean_text(price),
        "description": clean_text(description),
        "image": clean_text(image),
        "blocked_or_unavailable": False,
    }


# STEP 16: Empty fallback record
def empty_record(url: str) -> Dict[str, Optional[str]]:
    return {
        "source": "walmart_next_data",
        "url": url,
        "product_name": None,
        "brand": None,
        "size_volume": None,
        "price": None,
        "description": None,
        "image": None,
        "blocked_or_unavailable": True,
    }


# STEP 17: Save JSON and CSV
def save_outputs(record: Dict[str, Optional[str]]) -> None:
    Path("output").mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump([record], f, indent=2, ensure_ascii=False)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(record.keys()))
        writer.writeheader()
        writer.writerow(record)


# STEP 18: Main run flow
def main() -> None:
    try:
        status_code, html = get_html(URL)
        save_debug_html(html)

        print(f"[INFO] HTTP status -> {status_code}")
        print(f"[INFO] Debug HTML  -> {DEBUG_HTML}")

        if is_block_page(html):
            save_outputs(empty_record(URL))
            print("[WARN] Walmart returned a bot/challenge page, not a product page.")
            return

        if is_not_found_page(status_code, html) and not looks_like_product_page(html):
            save_outputs(empty_record(URL))
            print("[WARN] Walmart returned a not-found page for this URL.")
            return

        if not looks_like_product_page(html):
            save_outputs(empty_record(URL))
            print("[WARN] Page loaded, but it does not clearly look like the expected product page.")
            return

        record = extract_product_record_from_html(html, URL)
        save_outputs(record)

        print("[INFO] Saved JSON ->", OUTPUT_JSON)
        print("[INFO] Saved CSV  ->", OUTPUT_CSV)
        print("[INFO] Product    ->", record["product_name"])
        print("[INFO] Price      ->", record["price"])
        print("[INFO] Blocked    ->", record["blocked_or_unavailable"])

    except Exception as e:
        save_outputs(empty_record(URL))
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()
    