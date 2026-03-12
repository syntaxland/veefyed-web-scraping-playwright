# Product Scraper Python, Playwright and BeautifulSoup (Veefyed)

This repository contains a set of **Python Playwright-based scrapers** designed to extract product information from several ecommerce product pages.

The scraper attempts to collect the following fields:

* product name
* brand
* size / volume
* price
* description
* ingredients (when available)
* product image

The extracted data is exported to both **JSON and CSV** formats inside the `output/` directory.

---

# Target Sites

The original task required scraping product pages from the following retailers:

1. Food City
2. Walmart
3. Target

During testing, an additional **Jumia product page** was used to validate that the scraper pipeline works correctly on a site without strong anti-bot protection.

---

# Tested Product URLs

### Food City

[https://foodcityships.com/p/3085/Noxzema-Deep-Original-Classic-Clean-Cleansing-Cream--12-oz](https://foodcityships.com/p/3085/Noxzema-Deep-Original-Classic-Clean-Cleansing-Cream--12-oz)

### Walmart

[https://www.walmart.com/ip/Noxzema-Classic-Clean-Original-Deep-Cleansing-Cream-12-oz/10294073](https://www.walmart.com/ip/Noxzema-Classic-Clean-Original-Deep-Cleansing-Cream-12-oz/10294073)

Additional Walmart test:
[https://www.walmart.com/cp/the-wellness-hub/5523094](https://www.walmart.com/cp/the-wellness-hub/5523094)

### Target

[https://www.target.com/p/noxzema-classic-clean-original-deep-cleansing-cream-12oz/-/A-11000080](https://www.target.com/p/noxzema-classic-clean-original-deep-cleansing-cream-12oz/-/A-11000080)

### Validation Test (Jumia)

[https://www.jumia.com.ng/noxzema-moisturizing-cleansing-cream-wt-eucalyptus-extract-340g-418987238.html](https://www.jumia.com.ng/noxzema-moisturizing-cleansing-cream-wt-eucalyptus-extract-340g-418987238.html)

---

# Repository Structure

```
veefyed-web-scraping-playwright/
│
├── food_city_main.py
├── target_main.py
├── walmart_main.py
├── walmart_wellness.py
├── walmart_next_data.py
├── jumia_noxzema_data.py
│
├── requirements.txt
├── README.md
│
├── output/
│   ├── food_city.json
│   ├── food_city.csv
│   ├── target_city.json
│   ├── target_city.csv
│   ├── walmart_city.json
│   ├── walmart_city.csv
│   ├── jumia_noxzema_data.json
│   ├── jumia_noxzema_data.csv
│   └── debug/
│
└── state/
```

The **state/** directory stores persistent browser session data such as:

* cookies
* local storage
* session data

This helps maintain site sessions across runs.

---

# How the Scrapers Work

Each scraper follows a similar pipeline.

### 1. Launch Playwright Browser

The scraper opens the product page using Playwright with:

* a realistic browser user agent
* persistent browser session
* JavaScript enabled

```
launch_persistent_context(...)
```

This allows cookies and browser storage to persist across runs.

---

### 2. Detect Anti-Bot / Block Pages

The scraper checks page content for common blocking signals such as:

* captcha
* "robot or human"
* "sorry for the wait"
* "access denied"

If detected, the scraper:

* pauses
* allows manual resolution
* continues extraction if the page becomes available

---

### 3. Extract Product Data

Extraction uses multiple fallback strategies to improve reliability.

#### Method 1 – JSON-LD Structured Data

Many ecommerce pages embed product information inside:

```html
<script type="application/ld+json">
```

This is the most reliable source for:

* product name
* brand
* description
* image
* price

---

#### Method 2 – Meta Tags

If JSON-LD is unavailable, the scraper checks:

* `og:title`
* `og:image`
* `meta[name="description"]`

---

#### Method 3 – DOM Selectors

If structured data is missing, the scraper searches the page for visible elements such as:

* `h1`
* price containers
* description blocks
* ingredients sections

---

#### Method 4 – Regex Fallback

As a final fallback, the scraper scans the full page text for patterns such as:

* size / volume
* ingredients
* price

---

# Output Data

Each run produces JSON and CSV files containing extracted product records.

Example output:

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

# Installation

### 1. Create virtual environment

```
python -m venv .venv
```

### 2. Activate environment

Linux / macOS

```
source .venv/bin/activate
```

Windows

```
.venv\Scripts\activate
```

---

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

### 4. Install Playwright browsers

```
playwright install
```

---

# How to Run

Run each scraper individually.

### Food City

```
python food_city_main.py
```

### Target

```
python target_main.py
```

### Walmart

```
python walmart_main.py
```

### Walmart (alternative experiments)

```
python walmart_wellness.py
python walmart_next_data.py
```

### Jumia validation test

```
python jumia_noxzema_data.py
```

---

# Current Results

| Site      | Result  | Notes                                             |
| --------- | ------- | ------------------------------------------------- |
| Food City | Failed  | Domain resolution error (`ERR_NAME_NOT_RESOLVED`) |
| Target    | Blocked | Challenge / wait page detected                    |
| Walmart   | Blocked | Bot challenge page returned                       |
| Jumia     | Success | Product extracted successfully                    |

The successful Jumia test confirms that the **scraper architecture and extraction logic work correctly**.

The main limitation encountered is **anti-bot protection on some retailers** rather than extraction logic errors.

---

# Known Limitations

Some ecommerce sites deploy advanced bot protection systems that may block automated browsing.

Examples observed during testing:

Target:

* "Sorry for the wait"

Walmart:

* "Robot or human?"
* "Activate and hold the button to confirm that you’re human"

Because of these protections, the scraper may receive a challenge page instead of the real product page.

---

# Possible Improvements

Future improvements could include:

* proxy support
* rotating user agents
* retry with exponential backoff
* screenshot capture on failure
* improved selector configuration per site
* centralized base scraper class
* structured logging

---

# Development Tips

While testing:

* keep `headless=False`
* run scripts one at a time
* inspect loaded pages using browser DevTools
* verify whether the page is a real product page or a block page

---

# Disclaimer

This project is for **educational and technical demonstration purposes**.

Websites may restrict automated access, so scraping behavior can vary depending on:

* IP reputation
* region
* request frequency
* browser fingerprint

Always respect website terms of service.

---

# Author

Python • Playwright • BeautifulSoup

GitHub repository:

[https://github.com/syntaxland/veefyed-web-scraping-playwright](https://github.com/syntaxland/veefyed-web-scraping-playwright)

---
