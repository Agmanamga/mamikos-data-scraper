# Mamikos Web Scraping Tools for Jabodetabek Kos Analysis

This repository contains Python scripts used for collecting data from [Mamikos.com](https://mamikos.com), a leading Indonesian kos (boarding house) rental platform. These tools were developed as part of the **"Studi Data Kos Jabodetabek"** project, which aims to uncover the factors influencing kos prices and facility preferences across the Jabodetabek region (Jakarta, Bogor, Depok, Tangerang, Bekasi).

---

## Project Overview

The "Studi Data Kos Jabodetabek" project focuses on analyzing kos rental data to uncover pricing patterns, facility impacts, and market dynamics in the greater Jakarta area. The data collection process was handled using the scraping scripts in this repository.

### Key Objectives:

- Identify features that influence kos prices in Jabodetabek.
- Analyze price trends and distribution based on location and facilities.
- Provide practical, data-driven insights for kos seekers and owners.

---

## 🛠️ Tools Overview

There are two main Python scripts used for scraping:

### 1. `Mamikos Link Scrapper.py`

This script automates Mamikos search pages to collect URLs of individual kos listings.

#### Key Features:

- Navigates to a custom Mamikos search URL.
- Clicks the "Lihat lebih banyak lagi" button up to 15 times (configurable).
- Simulates Ctrl+Click to validate and collect unique product URLs.
- Saves all URLs into a CSV file.

### 2. `Mamikos Data Scrapper.py`

This script visits each kos URL (from the previous step) to extract detailed listing information.

#### Key Features:

- Reads URLs from the CSV.
- Aggressively scrolls each product page to load dynamic content.
- Uses Selenium for interactions & BeautifulSoup for parsing HTML.
- Extracts comprehensive data such as:
  - Price, room size, discounts, amenities, ratings, and transaction counts
  - Room availability, electricity inclusion, location, and more
- Saves final output in both JSON and CSV formats.

---

## Setup & Usage Instructions

###  Prerequisites:

- Python 3.x
- Google Chrome
- ChromeDriver (matching your Chrome version)
- Required libraries:
  ```bash
  pip install selenium beautifulsoup4 pandas
  ```

### 🔎 How to Use `Mamikos Link Scrapper.py`:

1. Optionally change the output filename in `scraper.save_links_to_csv()`.
2. Run the script:
   ```bash
   python "Mamikos Link Scrapper.py"
   ```
3. Input Search link that inteded to be scraped on the input after the script running on the first time
4. Wait for the link scrapping process finished extracting the data
5. if there's popup on the browser, click it manually. If not, the process cannot be done.
6. Output: A CSV file containing all collected kos URLs.

### 🔍 How to Use `Mamikos Data Scrapper.py`:

1. Update filenames in `save_data_to_json()` and `save_data_to_csv()`.
3. Optional: Limit scraping by adding `max_products=50` for testing.
4. Run the script:
   ```bash
   python "Mamikos Data Scrapper.py"
   ```
5. Copy the file pach from link scrapper and paste it on the input after the script running
6. Iput the region name
7. Output: A detailed CSV and JSON file with all extracted data.

---

## 🔒 Anti-Detection Techniques

- Uses user-agent spoofing and disables WebDriver flags.
- Incorporates human-like delays to simulate user behavior.
- Breaks scraping into modular stages for better error handling and flexibility.

---

## 📊 Data Collected

The final dataset includes (but is not limited to):

- `url`, `room_name`, `price`, `room_size`, `location`
- `rating`, `rating_count`, `transaction_count`
- `all_facilities_bs`, `is_electricity_included`, `discount_amount`, `deposit_amount_bs`
- `tipe_kos`, `owner_name`, `product_number`, `region`

---

##  Project Workflow

1. **Data Collection:** Scraping URLs and product data for multiple Jabodetabek regions.
2. **Data Cleaning:** Removing symbols, formatting inconsistencies, and missing values.
3. **Exploration:** Identifying price trends and distribution by region and facility.
4. **Visualization & Modeling:** Using Python, Power BI, and XGBoost to build insights and predictions.

---

## Notes

- Site structure may change; inspect the Mamikos site if errors occur.
- Pop-ups, lazy loading, and dynamic Vue.js components can affect scraping.
- This repo focuses on raw extraction; data cleaning and modeling are handled separately.

---

## Contributing & Feedback

Have ideas, improvements, or similar experiences scraping Indonesian property sites? Feel free to fork, contribute, or open an issue. PRs are welcome!

---

## About the Author

This project was developed by **Dendy Kurniari Agman**, a data analytics enthusiast transitioning from education and multimedia into the data world. 

Dendy created this project as part of his data portfolio to demonstrate practical skills in web scraping, data exploration, and predictive modeling using real-world data from Indonesia’s housing market.

- 📍 Based in West Kalimantan
- 📧 Email: dendy.kurniary@gmail.com
- 🔗 Portfolio: [dendykurniari.notion.site](https://dendykurniari.notion.site/Personal-Portfolio-188c046abbad80c3bbcbe9195feb21c0)
- 💼 LinkedIn: [linkedin.com/in/dendy-kurniari-agman-a2b38616a](https://linkedin.com/in/dendy-kurniari-agman-a2b38616a)

Feel free to connect or reach out if you’d like to collaborate, ask questions, or explore similar data-driven projects!
---

## License

This repository is for educational and personal use only. Respect Mamikos.com's terms of service.

