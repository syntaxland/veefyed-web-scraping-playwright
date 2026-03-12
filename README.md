
# Veefyed Product Scraper with Playwright

This project contains 3 separate Playwright scrapers for extracting product details from:

- Food City
- Target
- Walmart

Each scraper collects:

- product name
- brand
- size/volume
- price
- description
- ingredients
- image

The data is exported to both JSON and CSV inside the `output/` folder.

---

## Project Structure

```bash
project/
├── food_city_main.py
├── target_main.py
├── walmart_main.py
├── requirements.txt
├── output/
├── state/
└── README.md
````

---

## Output Files

After running the scripts, the following files will be created:

```bash
output/food_city.json
output/food_city.csv
output/target_city.json
output/target_city.csv
output/walmart_city.json
output/walmart_city.csv
```

The `state/` folder stores persistent browser session data such as cookies and local storage.

---

## What the Scrapers Do

Each script follows this flow:

1. Open the product page with Playwright.
2. Use a persistent browser session so cookies are reused.
3. Detect if the site shows a block page, wait page, captcha, or unavailable page.
4. Allow manual resolution if needed while the browser is open.
5. Extract product data using fallback logic:

   * JSON-LD structured data
   * meta tags
   * visible page selectors
   * regex from page text
6. Save the result to JSON and CSV.

---

## Requirements

* Python 3.10+
* Playwright
* playwright-stealth
* beautifulsoup4
* pandas
* python-dotenv

---

## Installation

### 1. Create virtual environment

```bash
python -m venv .venv
```

### 2. Activate virtual environment

#### Linux / macOS

```bash
source .venv/bin/activate
```

#### Windows

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
playwright install
```

---

## requirements.txt

Create a `requirements.txt` file like this:

```txt
playwright
pandas
python-dotenv
```

---

## How to Run

Run each scraper separately.

### Food City

```bash
python food_city_main.py
```

### Target

```bash
python target_main.py
```

### Walmart

```bash
python walmart_main.py 
```

### Logs

(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ python food_city_main.py
[INFO] Opening https://foodcityships.com/p/3085/Noxzema-Deep-Original-Classic-Clean-Cleansing-Cream--12-oz
[ERROR] Failed to open page: Page.goto: net::ERR_NAME_NOT_RESOLVED at https://foodcityships.com/p/3085/Noxzema-Deep-Original-Classic-Clean-Cleansing-Cream--12-oz
Call log:
  - navigating to "https://foodcityships.com/p/3085/Noxzema-Deep-Original-Classic-Clean-Cleansing-Cream--12-oz", waiting until "domcontentloaded"

[INFO] Saved JSON -> output/food_city.json
[INFO] Saved CSV  -> output/food_city.csv
(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ python target_main.py
[INFO] Opening https://www.target.com/p/noxzema-classic-clean-original-deep-cleansing-cream-12oz/-/A-11000080

[INFO] Target challenge/wait page detected.
[INFO] Please solve it manually in the opened browser.
[INFO] Waiting up to 90 seconds...

[WARN] Target still appears blocked.
[INFO] Saved JSON -> output/target_city.json
[INFO] Saved CSV  -> output/target_city.csv
(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ python walmart_main.py 
[INFO] Opening https://www.walmart.com/ip/Noxzema-Classic-Clean-Original-Deep-Cleansing-Cream-12-oz/10294073

[INFO] Walmart error/challenge detected.
[INFO] Solve manually in the opened browser if needed.
[INFO] Waiting up to 90 seconds...

[WARN] Walmart still looks blocked/unavailable.
[INFO] Saved JSON -> output/walmart_city.json
[INFO] Saved CSV  -> output/walmart_city.csv
(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ 



**Tried:**
https://www.walmart.com/cp/the-wellness-hub/5523094?povid=OMNISRV_D_i_GLOBAL_Nav_ServicesNav_HW_4097505_SuperDepartment_ClinicalServices_WellnessHub

```bash
python walmart_wellness.py
```

### Log

(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ python walmart_wellness.py
[INFO] Opening https://www.walmart.com/cp/the-wellness-hub/5523094?povid=OMNISRV_D_i_GLOBAL_Nav_ServicesNav_HW_4097505_SuperDepartment_ClinicalServices_WellnessHub

[INFO] Walmart challenge/error page detected.
[INFO] Solve manually in the opened browser if needed.
[INFO] Waiting up to 90 seconds...

[INFO] Walmart page looks usable now.
[DEBUG] networkidle wait skipped/timeout
[DEBUG] No ready selector matched, continuing anyway
[DEBUG] listing positive_count=1, negative_count=0
[DEBUG] page text preview: robot or human?

activate and hold the button to confirm that you’re human. thank you!

terms of use privacy policy do not sell my personal information request my personal information

©2026 walmart stores, inc.
[DEBUG] blocked=True, probable_listing=True
[WARN] Page still looks blocked. Saving empty fallback record.
[INFO] Saved JSON -> output/walmart_wellness.json
[INFO] Saved CSV  -> output/walmart_wellness.csv
(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ 


### Using beautifulsoup4

```bash
python walmart_next_data.py
```

### Live URL:
"https://www.walmart.com/ip/Noxzema-Original-Facial-Cleanser-Cream-Daily-Deep-Face-Cleansing-for-All-Skin-Types-12-oz/14122693"

### Logs

(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ python walmart_next_data.py
[INFO] HTTP status -> 200
[INFO] Debug HTML  -> output/debug/walmart_next_data.html
[WARN] Walmart returned a bot/challenge page, not a product page.


### Tried Jumia Noxzema Product Detail (SUCCESSFUL)

```bash
python jumia_noxzema_data.py
```

### Logs

(.venv) jb@jb-U46E:~/Documents/dev/others/veefyed-web-scraping-playwright$ python jumia_noxzema_data.py
[INFO] HTTP status -> 200
[INFO] Debug HTML  -> output/debug/walmart_next_data.html
[INFO] Saved JSON -> output/walmart_next_data.json
[INFO] Saved CSV  -> output/walmart_next_data.csv
[INFO] Product    -> Noxzema Moisturizing Cleansing Cream Wt Eucalyptus Extract 340g | Jumia Nigeria
[INFO] Price      -> $35000.00
[INFO] Blocked    -> False


---

## How the Extraction Works

The scraper tries multiple methods so it does not fail if one selector changes.

### 1. JSON-LD

Many ecommerce pages include structured product data inside:

```html
<script type="application/ld+json">
```

This is the first and most reliable source for:

* product name
* brand
* description
* image
* price

### 2. Meta Tags

If JSON-LD is missing, the scraper checks:

* `og:title`
* `og:image`
* `meta[name="description"]`

### 3. Page Selectors

If structured data is missing, it looks for visible HTML elements like:

* `h1`
* price blocks
* ingredients section
* description section

### 4. Regex Fallback

If needed, it searches the full page text using regex for:

* size/volume
* ingredients

---

## Anti-Bot / Captcha / Site Unavailable Handling

Some of these sites may show:

* captcha
* “Sorry for the wait”
* “We couldn’t find this page”
* server unavailable page
* access denied

The scraper handles this by:

1. launching in visible mode (`headless=False`)
2. using a persistent browser profile
3. checking page text for known block messages
4. waiting for manual resolution if needed

### Important

This project does **not** attempt to break or bypass security systems.
The intended workflow is:

* open browser normally
* solve any visible challenge manually if allowed
* let session cookies persist
* continue scraping after the page becomes available

---

## Why Persistent Sessions Are Used

Each site uses:

```python
launch_persistent_context(...)
```

instead of a fresh browser session.

This helps because:

* cookies are preserved
* local storage is preserved
* solved challenges may remain valid for later runs
* scraping becomes more stable across retries

---

## Data Fields

Each output record contains:

* `source`
* `url`
* `product_name`
* `brand`
* `size_volume`
* `price`
* `description`
* `ingredients`
* `image`
* `blocked_or_unavailable`

Example:

```json
[
  {
    "source": "target",
    "url": "https://www.target.com/...",
    "product_name": "Noxzema Classic Clean Original Deep Cleansing Cream 12oz",
    "brand": "Noxzema",
    "size_volume": "12 oz",
    "price": "$4.99",
    "description": "Deep cleansing cream...",
    "ingredients": "Water, soybean oil, ...",
    "image": "https://...",
    "blocked_or_unavailable": false
  }
]
```

---

## Error Handling

The code is designed to fail gracefully.

### Included reliability measures:

* safe text extraction
* safe attribute extraction
* timeout handling
* block-page detection
* fallback selectors
* partial record saving even if some fields are missing

This means the scraper can still produce output even when:

* some selectors are missing
* some fields are unavailable
* the page loads partially
* the site temporarily blocks access

---

## Notes Per Site

### Food City

This site may fail to load or show connection issues depending on environment or region.

### Target

This site may show a wait/throttle page such as:

* “Sorry for the wait”
* “It’s a little busier than we expected”

### Walmart

This site may sometimes return:

* “We couldn’t find this page”
  even when the product exists in another live listing or region-specific route.

Because of that, the scraper checks whether the loaded page is actually a valid product page before extracting.

---

## Development Tips

While testing:

* keep `headless=False`
* run one script at a time
* inspect the loaded page manually if extraction fails
* verify selectors with browser DevTools
* check whether the page is a product page or a block/error page

When stable, you can try switching to:

```python
headless=True
```

but visible mode is safer for these sites.

---

## Possible Improvements

Future upgrades could include:

* shared `base_scraper.py`
* retry with exponential backoff
* screenshot on failure
* save raw HTML on failure
* logging to file
* selector configuration per site
* proxy support via `.env`

---

## Disclaimer

Use this scraper responsibly and only where you have the right to access and collect the data.
Retail sites may rate-limit, challenge, or block automated traffic, so stability can vary by IP, region, and session state.

---

## Author

Built with Python, Playwright, and pandas.

```

