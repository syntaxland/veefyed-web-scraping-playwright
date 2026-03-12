# walmart_wellness.py

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# STEP 1: Set landing page URL and output paths
URL = "https://www.walmart.com/cp/the-wellness-hub/5523094?povid=OMNISRV_D_i_GLOBAL_Nav_ServicesNav_HW_4097505_SuperDepartment_ClinicalServices_WellnessHub"
OUTPUT_JSON = "output/walmart_wellness.json"
OUTPUT_CSV = "output/walmart_wellness.csv"
STATE_DIR = "state/walmart_wellness_profile"


class WalmartWellnessScraper:
    def __init__(self, headless: bool = False):
        # Keep browser visible while testing
        self.headless = headless

        # Store all scraped product card records
        self.data: List[Dict[str, Any]] = []

    # STEP 2: Clean text values
    def clean_text(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return re.sub(r"\s+", " ", value).strip() or None

    # STEP 3: Safe text extraction from a locator
    def safe_locator_text(self, locator, timeout: int = 3000) -> Optional[str]:
        try:
            locator.first.wait_for(state="visible", timeout=timeout)
            return self.clean_text(locator.first.text_content())
        except Exception:
            return None

    # STEP 4: Safe attribute extraction from a locator
    def safe_locator_attr(self, locator, attr: str, timeout: int = 3000) -> Optional[str]:
        try:
            locator.first.wait_for(state="attached", timeout=timeout)
            value = locator.first.get_attribute(attr)
            return self.clean_text(value)
        except Exception:
            return None

    # STEP 5: Safe text extraction directly from page
    def safe_text(self, page, selector: str, timeout: int = 3000) -> Optional[str]:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="visible", timeout=timeout)
            return self.clean_text(locator.text_content())
        except Exception:
            return None

    # STEP 6: Safe attribute extraction directly from page
    def safe_attr(self, page, selector: str, attr: str, timeout: int = 3000) -> Optional[str]:
        try:
            locator = page.locator(selector).first
            locator.wait_for(state="attached", timeout=timeout)
            value = locator.get_attribute(attr)
            return self.clean_text(value)
        except Exception:
            return None

    # STEP 7: Read full page text for validation
    def page_text(self, page) -> str:
        try:
            return page.locator("body").inner_text(timeout=4000)
        except Exception:
            return ""

    # STEP 8: Save debug screenshot and HTML
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

    # STEP 9: Detect block / error pages
    def is_blocked(self, page) -> bool:
        text = self.page_text(page).lower()

        blocked_markers = [
            "sorry for the wait",
            "busier than we expected",
            "thanks for your patience",
            "we couldn’t find this page",
            "we couldn't find this page",
            "access denied",
            "captcha",
            "verify you are human",
            "robot or human",
            "temporarily unavailable",
            "page not found",
            "404",
        ]

        return any(marker in text for marker in blocked_markers)

    # STEP 10: Validate this looks like a real Walmart listing page
    def is_probable_listing_page(self, page) -> bool:
        text = self.page_text(page).lower()

        positive_signals = [
            "wellness",
            "add",
            "$",
            "pickup",
            "delivery",
            "shop",
            "walmart",
        ]

        negative_signals = [
            "sorry for the wait",
            "we couldn’t find this page",
            "we couldn't find this page",
            "captcha",
            "verify",
            "access denied",
        ]

        positive_count = sum(1 for s in positive_signals if s in text)
        negative_count = sum(1 for s in negative_signals if s in text)

        print(f"[DEBUG] listing positive_count={positive_count}, negative_count={negative_count}")
        print(f"[DEBUG] page text preview: {text[:500]}")

        return positive_count >= 1 and negative_count == 0

    # STEP 11: Wait if Walmart challenge page appears
    def wait_for_manual_resolution(self, page, seconds: int = 90) -> None:
        print("\n[INFO] Walmart challenge/error page detected.")
        print("[INFO] Solve manually in the opened browser if needed.")
        print(f"[INFO] Waiting up to {seconds} seconds...\n")

        start = time.time()
        while time.time() - start < seconds:
            if not self.is_blocked(page):
                print("[INFO] Walmart page looks usable now.")
                return
            page.wait_for_timeout(2000)

        print("[WARN] Walmart still looks blocked/unavailable.")

    # STEP 12: Reject logo/icon images
    def is_valid_image(self, url: Optional[str]) -> bool:
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

    # STEP 13: Normalize relative URLs
    def normalize_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None

        url = url.strip()

        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return f"https://www.walmart.com{url}"

        return url

    # STEP 14: Extract a price-looking value from card text if selectors fail
    def extract_price_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None

        match = re.search(r"\$\s*\d+(?:\.\d{1,2})?", text)
        if match:
            return self.clean_text(match.group(0))

        return None

    # STEP 15: Extract price-unit like $0.57/oz or 46.0 c/ea
    def extract_price_unit_from_text(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None

        match = re.search(
            r"(?:\$\s*\d+(?:\.\d{1,2})?\s*/\s*[a-z]+|\d+(?:\.\d+)?\s*[a-z]+/[a-z]+)",
            text,
            re.I
        )
        if match:
            return self.clean_text(match.group(0))

        return None

    # STEP 16: Return empty record if page is invalid
    def build_empty_record(self, url: str) -> Dict[str, Any]:
        return {
            "source": "walmart_wellness",
            "source_page": url,
            "page_title": None,
            "product_name": None,
            "price": None,
            "price_unit": None,
            "product_url": None,
            "image": None,
            "badge": None,
            "blocked_or_unavailable": True,
        }

    # STEP 17: Wait until page is more ready
    def wait_for_page_ready(self, page) -> None:
        page.wait_for_timeout(5000)

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            print("[DEBUG] networkidle wait skipped/timeout")

        possible_ready_selectors = [
            'a[href*="/ip/"]',
            'img',
            'button:has-text("Add")',
            'text=/Shop now/i',
        ]

        for selector in possible_ready_selectors:
            try:
                page.locator(selector).first.wait_for(state="visible", timeout=5000)
                print(f"[DEBUG] Ready selector found: {selector}")
                return
            except Exception:
                continue

        print("[DEBUG] No ready selector matched, continuing anyway")

    # STEP 18: Scroll page to trigger lazy-loaded content
    def scroll_page(self, page, rounds: int = 4, pause_ms: int = 2000) -> None:
        for idx in range(rounds):
            try:
                page.mouse.wheel(0, 2500)
                page.wait_for_timeout(pause_ms)
                print(f"[DEBUG] Scrolled page round {idx + 1}/{rounds}")
            except Exception:
                break

    # STEP 19: Find best card locator
    def find_best_cards_locator(self, page):
        card_selectors = [
            'a[href*="/ip/"]',
            '[data-testid="product-tile"]',
            '[data-testid="item-stack"]',
            'div[data-item-id]',
        ]

        best_locator = None
        best_count = 0
        best_selector = None

        for selector in card_selectors:
            try:
                locator = page.locator(selector)
                count = locator.count()
                print(f"[DEBUG] Selector {selector} -> count={count}")
                if count > best_count:
                    best_locator = locator
                    best_count = count
                    best_selector = selector
            except Exception:
                continue

        print(f"[DEBUG] Best selector: {best_selector}, count={best_count}")
        return best_locator, best_count, best_selector

    # STEP 20: Main scraping flow
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
                page.wait_for_timeout(8000)
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

            self.save_debug_files(page, "walmart_wellness_debug")

            if self.is_blocked(page):
                self.wait_for_manual_resolution(page, seconds=90)
                self.save_debug_files(page, "walmart_wellness_debug_after_wait")

            self.wait_for_page_ready(page)

            blocked = self.is_blocked(page)
            probable = self.is_probable_listing_page(page)

            print(f"[DEBUG] blocked={blocked}, probable_listing={probable}")

            if blocked:
                print("[WARN] Page still looks blocked. Saving empty fallback record.")
                self.data.append(self.build_empty_record(url))
                context.close()
                return

            if not probable:
                print("[WARN] Page validation uncertain. Will still attempt card extraction.")

            # STEP 21: Save another debug snapshot after waits
            self.save_debug_files(page, "walmart_wellness_debug_ready")

            # STEP 22: Read page title for context
            page_title = (
                self.safe_text(page, "h1")
                or self.safe_attr(page, 'meta[property="og:title"]', "content")
                or self.safe_attr(page, "title", "text")
            )

            print(f"[DEBUG] page_title={page_title}")

            # STEP 23: Try finding cards before scrolling
            cards, card_count, best_selector = self.find_best_cards_locator(page)

            # STEP 24: If none found, scroll and retry
            if not cards or card_count == 0:
                print("[DEBUG] No cards found initially. Scrolling page and retrying...")
                self.scroll_page(page, rounds=4, pause_ms=2000)
                self.save_debug_files(page, "walmart_wellness_debug_after_scroll")
                cards, card_count, best_selector = self.find_best_cards_locator(page)

            if not cards or card_count == 0:
                print("[WARN] No product cards found after retry.")
                self.data.append(self.build_empty_record(url))
                context.close()
                return

            print(f"[INFO] Found {card_count} candidate cards using selector: {best_selector}")

            # STEP 25: Limit during testing
            max_cards = min(card_count, 20)

            for i in range(max_cards):
                card = cards.nth(i)

                try:
                    card_text = self.clean_text(card.text_content()) or ""

                    # If best selector is anchor links, card itself may be the product link
                    direct_href = None
                    try:
                        direct_href = card.get_attribute("href")
                    except Exception:
                        direct_href = None

                    # Card title
                    product_name = (
                        self.safe_locator_text(card.locator('[data-automation-id="product-title"]'))
                        or self.safe_locator_text(card.locator("span"))
                        or self.safe_locator_text(card.locator("a"))
                        or self.clean_text(card_text[:150])
                    )

                    # Product link
                    product_url = direct_href or self.safe_locator_attr(card.locator("a"), "href")
                    product_url = self.normalize_url(product_url)

                    # Card image
                    image = (
                        self.safe_locator_attr(card.locator("img"), "src")
                        or self.safe_locator_attr(card.locator("img"), "data-src")
                    )
                    image = self.normalize_url(image)
                    if not self.is_valid_image(image):
                        image = None

                    # Price
                    price = (
                        self.safe_locator_text(card.locator('[itemprop="price"]'))
                        or self.safe_locator_text(card.locator('[class*="price"]'))
                        or self.extract_price_from_text(card_text)
                    )

                    # Price unit
                    price_unit = self.extract_price_unit_from_text(card_text)

                    # Badge / promo
                    badge = (
                        self.safe_locator_text(card.locator('text=/now/i'))
                        or self.safe_locator_text(card.locator('text=/rollback/i'))
                        or self.safe_locator_text(card.locator('text=/shop now/i'))
                    )

                    # Skip obviously bad rows
                    if not product_name and not product_url and not price:
                        print(f"[DEBUG] Skipping bad card {i + 1}")
                        continue

                    record = {
                        "source": "walmart_wellness",
                        "source_page": url,
                        "page_title": self.clean_text(page_title),
                        "product_name": self.clean_text(product_name),
                        "price": self.clean_text(price),
                        "price_unit": self.clean_text(price_unit),
                        "product_url": self.clean_text(product_url),
                        "image": self.clean_text(image),
                        "badge": self.clean_text(badge),
                        "blocked_or_unavailable": False,
                    }

                    self.data.append(record)
                    print(f"[DEBUG] Parsed card {i + 1}: {record['product_name']} | {record['price']}")

                except Exception as e:
                    print(f"[WARN] Error parsing card {i + 1}: {e}")

            # STEP 26: If still nothing parsed, save fallback row
            if not self.data:
                print("[WARN] Card loop ran but no usable records were extracted.")
                self.data.append(self.build_empty_record(url))

            context.close()

    # STEP 27: Export results
    def export(self) -> None:
        Path("output").mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        pd.DataFrame(self.data).to_csv(OUTPUT_CSV, index=False)

        print(f"[INFO] Saved JSON -> {OUTPUT_JSON}")
        print(f"[INFO] Saved CSV  -> {OUTPUT_CSV}")


def main():
    scraper = WalmartWellnessScraper(headless=False)
    scraper.scrape(URL)
    scraper.export()


if __name__ == "__main__":
    main()