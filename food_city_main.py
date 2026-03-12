# food_city_main.py

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# STEP 1: Product URL and output paths
URL = "https://foodcityships.com/p/3085/Noxzema-Deep-Original-Classic-Clean-Cleansing-Cream--12-oz"
OUTPUT_JSON = "output/food_city.json"
OUTPUT_CSV = "output/food_city.csv"
STATE_DIR = "state/food_city_profile"


class FoodCityScraper:
    def __init__(self, headless: bool = False):
        # Open browser visibly for testing/debugging
        self.headless = headless

        # Final scraped records will be stored here
        self.data: List[Dict[str, Any]] = []

    # STEP 2: Clean messy text
    def clean_text(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value = re.sub(r"\s+", " ", value).strip()
        return value or None

    # STEP 3: Safely read visible text
    def safe_text(self, page, selector: str, timeout: int = 3000) -> Optional[str]:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            return self.clean_text(locator.text_content())
        except Exception:
            return None

    # STEP 4: Safely read attribute value
    def safe_attr(self, page, selector: str, attr: str, timeout: int = 3000) -> Optional[str]:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="attached", timeout=timeout)
            value = locator.get_attribute(attr)
            return self.clean_text(value)
        except Exception:
            return None

    # STEP 5: Read all visible page text
    def page_text(self, page) -> str:
        try:
            return page.locator("body").inner_text(timeout=3000)
        except Exception:
            return ""

    # STEP 6: Save debug screenshot and HTML for inspection
    def save_debug_files(self, page, prefix: str) -> None:
        Path("output/debug").mkdir(parents=True, exist_ok=True)

        try:
            page.screenshot(path=f"output/debug/{prefix}.png", full_page=True)
        except Exception:
            pass

        try:
            html = page.content()
            with open(f"output/debug/{prefix}.html", "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

    # STEP 7: Detect browser error pages / block pages / unavailable pages
    def is_blocked(self, page) -> bool:
        text = self.page_text(page).lower()

        blocked_markers = [
            "sorry for the wait",
            "busier than we expected",
            "thanks for your patience",
            "we couldn’t find this page",
            "we couldn't find this page",
            "having trouble finding that site",
            "this site can’t be reached",
            "this site can't be reached",
            "access denied",
            "captcha",
            "verify you are human",
            "robot or human",
            "temporarily unavailable",
            "page not found",
            "404",
            "err_name_not_resolved",
        ]

        return any(marker in text for marker in blocked_markers)

    # STEP 8: Confirm page looks like a real product page
    def is_probable_product_page(self, page) -> bool:
        text = self.page_text(page).lower()

        positive_signals = [
            "noxzema",
            "ingredients",
            "description",
            "$",
            "add to cart",
            "brand",
            "12 oz",
        ]

        negative_signals = [
            "sorry for the wait",
            "we couldn’t find this page",
            "we couldn't find this page",
            "this site can’t be reached",
            "this site can't be reached",
            "having trouble finding that site",
            "captcha",
            "verify",
        ]

        positive_count = sum(1 for s in positive_signals if s in text)
        negative_count = sum(1 for s in negative_signals if s in text)

        return positive_count >= 2 and negative_count == 0

    # STEP 9: Wait so user can manually resolve a challenge if page allows it
    def wait_for_manual_resolution(self, page, seconds: int = 60) -> None:
        print("\n[INFO] Block/challenge page detected.")
        print("[INFO] Please solve it manually in the opened browser if possible.")
        print(f"[INFO] Waiting up to {seconds} seconds...\n")

        start = time.time()
        while time.time() - start < seconds:
            if not self.is_blocked(page):
                print("[INFO] Page looks usable now.")
                return
            page.wait_for_timeout(2000)

        print("[WARN] Still blocked/unavailable after waiting.")

    # STEP 10: Extract structured product data from JSON-LD if available
    def parse_json_ld(self, page) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        try:
            scripts = page.locator('script[type="application/ld+json"]')
            count = scripts.count()

            for i in range(count):
                raw = scripts.nth(i).text_content()
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
                    if "product" not in item_type:
                        continue

                    result["product_name"] = result.get("product_name") or item.get("name")

                    brand = item.get("brand")
                    if isinstance(brand, dict):
                        result["brand"] = result.get("brand") or brand.get("name")
                    elif isinstance(brand, str):
                        result["brand"] = result.get("brand") or brand

                    result["description"] = result.get("description") or item.get("description")

                    image = item.get("image")
                    if isinstance(image, list) and image:
                        result["image"] = result.get("image") or image[0]
                    elif isinstance(image, str):
                        result["image"] = result.get("image") or image

                    offers = item.get("offers")
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    if isinstance(offers, dict):
                        result["price"] = result.get("price") or str(offers.get("price") or "")

            return result
        except Exception:
            return result

    # STEP 11: Extract size/volume from text
    def extract_size(self, *values: Optional[str]) -> Optional[str]:
        pattern = re.compile(r"\b\d+(?:\.\d+)?\s?(?:oz|fl oz|ml|l|g|kg|lb|ct)\b", re.I)

        for value in values:
            if not value:
                continue
            match = pattern.search(value)
            if match:
                return self.clean_text(match.group(0))

        return None

    # STEP 12: Reject logos, icons, SVGs, base64 placeholders, etc.
    def is_valid_image(self, url: Optional[str]) -> bool:
        if not url:
            return False

        lower = url.lower()
        bad_patterns = [
            "spark-icon",
            "logo",
            "icon",
            "sprite",
            "data:image/",
            ".svg",
        ]
        return not any(p in lower for p in bad_patterns)

    # STEP 13: Create a null-safe record when page is invalid
    def build_empty_record(self, url: str) -> Dict[str, Any]:
        return {
            "source": "food_city",
            "url": url,
            "product_name": None,
            "brand": None,
            "size_volume": None,
            "price": None,
            "description": None,
            "ingredients": None,
            "image": None,
            "blocked_or_unavailable": True,
        }

    # STEP 14: Main scraping flow
    def scrape(self, url: str) -> None:
        Path(STATE_DIR).mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=STATE_DIR,
                headless=self.headless,
                viewport={"width": 1400, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )

            page = context.new_page()

            try:
                print(f"[INFO] Opening {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(5000)

            except PlaywrightTimeoutError:
                print("[WARN] Initial page load timed out.")
                self.data.append(self.build_empty_record(url))
                context.close()
                return

            except Exception as e:
                print(f"[ERROR] Failed to open page: {e}")
                self.data.append(self.build_empty_record(url))
                context.close()
                return

            # Save page snapshot for debugging
            self.save_debug_files(page, "food_city_debug")

            # If blocked, optionally wait for manual resolution
            if self.is_blocked(page):
                self.wait_for_manual_resolution(page, seconds=60)
                self.save_debug_files(page, "food_city_debug_after_wait")

            # If still not a real PDP, stop and save null record
            if self.is_blocked(page) or not self.is_probable_product_page(page):
                self.data.append(self.build_empty_record(url))
                context.close()
                return

            json_ld = self.parse_json_ld(page)
            full_text = self.page_text(page)

            # STEP 15: Extract fields with fallbacks
            product_name = (
                json_ld.get("product_name")
                or self.safe_text(page, "h1")
                or self.safe_attr(page, 'meta[property="og:title"]', "content")
                or self.safe_text(page, '[data-testid*="product-name"]')
            )

            brand = (
                json_ld.get("brand")
                or self.safe_text(page, 'text=/brand/i')
            )

            price = (
                json_ld.get("price")
                or self.safe_text(page, 'text=/\\$\\s*\\d+(?:\\.\\d{2})?/')
                or self.safe_text(page, '[class*="price"]')
            )

            description = (
                json_ld.get("description")
                or self.safe_attr(page, 'meta[name="description"]', "content")
                or self.safe_text(page, 'text=/This cleansing cream/i')
            )

            ingredients = (
                self.safe_text(page, 'text=/ingredients/i')
                or self.safe_text(page, '[class*="ingredient"]')
            )

            image = (
                json_ld.get("image")
                or self.safe_attr(page, 'meta[property="og:image"]', "content")
            )

            if not self.is_valid_image(image):
                image = None

            size = self.extract_size(product_name, description, full_text)

            # STEP 16: Build final valid record
            record = {
                "source": "food_city",
                "url": url,
                "product_name": self.clean_text(product_name),
                "brand": self.clean_text(brand),
                "size_volume": self.clean_text(size),
                "price": self.clean_text(price),
                "description": self.clean_text(description),
                "ingredients": self.clean_text(ingredients),
                "image": self.clean_text(image),
                "blocked_or_unavailable": False,
            }

            self.data.append(record)
            context.close()

    # STEP 17: Export to JSON and CSV
    def export(self) -> None:
        Path("output").mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        pd.DataFrame(self.data).to_csv(OUTPUT_CSV, index=False)

        print(f"[INFO] Saved JSON -> {OUTPUT_JSON}")
        print(f"[INFO] Saved CSV  -> {OUTPUT_CSV}")


def main():
    scraper = FoodCityScraper(headless=False)
    scraper.scrape(URL)
    scraper.export()


if __name__ == "__main__":
    main()
    