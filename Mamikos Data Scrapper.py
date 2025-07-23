from bs4 import BeautifulSoup
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import random
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import csv # Import the csv module
import pandas as pd # Import pandas for CSV saving
from pathlib import Path

# --- BeautifulSoup based scraping function (kept separate for clarity) ---
def scrape_mamikos_details_from_html(html_content):
    """
    Scrapes specific details (owner name, room size, electricity inclusion,
    price before discount, all facilities, room availability, deposit amount)
    from a Mamikos product page HTML content using BeautifulSoup.

    Args:
        html_content (str): The HTML content of the Mamikos product page.

    Returns:
        dict: A dictionary containing the extracted details.
              Keys: "owner_name", "room_size", "is_electricity_included",
                    "price_before_discount_bs", "all_facilities_bs",
                    "room_availability_bs", "deposit_amount_bs".
              Values will be "N/A" or empty list if information is not found.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    owner_name = "N/A"
    room_size = "N/A"
    is_electricity_included = "N/A"
    price_before_discount_bs = "N/A"
    all_facilities_bs = []
    room_availability_bs = "N/A" # New field
    deposit_amount_bs = "N/A"    # New field

    print("  Attempting to extract specific details with BeautifulSoup...")

    # --- 1. Extract Owner Name ---
    owner_element = soup.find('div', class_='detail-kost-owner-section__owner-title')
    if owner_element:
        owner_text = owner_element.get_text(strip=True)
        if "Kos disewakan oleh" in owner_text:
            owner_name = owner_text.replace("Kos disewakan oleh", "").strip()
        else:
            owner_name = owner_text.strip()
        print(f"    - Owner Name (BS): '{owner_name}'")
    else:
        print("    - Owner Name (BS): Element not found.")


    # --- 2. Extract Room Size ---
    room_spec_section_title = soup.find('p', class_='detail-kost-facility-category__title', string=re.compile(r'Spesifikasi tipe kamar', re.IGNORECASE))
    if room_spec_section_title:
        room_spec_container = room_spec_section_title.find_parent('div', class_='detail-kost-facility-category')
        if room_spec_container:
            room_size_elements = room_spec_container.find_all('p', class_=re.compile(r'detail-kost-facility-item__label|bg-c-text--body-2'))
            for element in room_size_elements:
                text = element.get_text(strip=True)
                if re.search(r'\d+(\.\d+)?\s*x\s*\d+(\.\d+)?\s*meter', text):
                    room_size = text
                    print(f"    - Room Size (BS): '{room_size}'")
                    break 
            if room_size == "N/A":
                print("    - Room Size (BS): Pattern not found within elements.")
        else:
            print("    - Room Size (BS): Parent container not found.")
    else:
        print("    - Room Size (BS): 'Spesifikasi tipe kamar' title not found.")


    # --- 3. Determine if Electricity is Included ---
    electricity_icon_excluded = soup.find('img', alt='Tidak termasuk listrik')
    if electricity_icon_excluded:
        is_electricity_included = "Tidak termasuk listrik"
        print(f"    - Electricity (BS): '{is_electricity_included}' (via icon)")
    else:
        all_p_tags = soup.find_all('p', string=re.compile(r'listrik', re.IGNORECASE))
        found_electricity_text = False
        for p_tag in all_p_tags:
            text = p_tag.get_text(strip=True)
            if "Tidak termasuk listrik" in text:
                is_electricity_included = "Tidak termasuk listrik"
                found_electricity_text = True
                print(f"    - Electricity (BS): '{is_electricity_included}' (via explicit text)")
                break
            elif "listrik" in text: # If "listrik" is mentioned but not explicitly excluded
                is_electricity_included = "Termasuk listrik (implied)"
                found_electricity_text = True
                print(f"    - Electricity (BS): '{is_electricity_included}' (via implied text)")
                # Don't break immediately, in case a "Tidak termasuk" appears later
        
        if not found_electricity_text:
            description_element = soup.find('div', id='kost-owner-story-content')
            if description_element and "Token Mandiri" in description_element.get_text():
                is_electricity_included = "Token Mandiri (electricity separate/token-based)"
                print(f"    - Electricity (BS): '{is_electricity_included}' (via description)")
            else:
                if is_electricity_included == "N/A": # Only if still N/A after checking implied texts
                    print("    - Electricity (BS): No specific information or exclusion found.")

    # --- 4. Extract Price Before Discount (Original Price) ---
    # Prioritize specific class names for strikethrough prices
    price_before_discount_element = soup.find('span', class_='rc-price__additional-discount-price bg-c-text bg-c-text--body-2 bg-c-text--strikethrough')
    if not price_before_discount_element:
        price_before_discount_element = soup.find('span', class_='bg-c-text bg-c-text--label-4 bg-c-text--strikethrough')
    
    if price_before_discount_element:
        price_before_discount_bs = price_before_discount_element.get_text(strip=True)
        print(f"    - Price Before Discount (BS): '{price_before_discount_bs}'")
    else:
        print("    - Price Before Discount (BS): Element not found.")


    # --- 5. Extract ALL Facilities from all relevant sections ---
    # Find all main containers that typically hold facility categories
    # These often have the class 'detail-kost-facility-category'
    facility_category_wrappers = soup.find_all('div', class_='detail-kost-facility-category')
    
    if facility_category_wrappers:
        for wrapper in facility_category_wrappers:
            # Find all individual facility items within this specific wrapper
            # The class 'detail-kost-facility-item__label' is the most consistent for the facility text itself
            facility_items_in_section = wrapper.find_all('p', class_='detail-kost-facility-item__label')
            for item in facility_items_in_section:
                text = item.get_text(strip=True)
                if text and text not in all_facilities_bs: # Avoid duplicates
                    all_facilities_bs.append(text)
        
        if all_facilities_bs:
            print(f"    - All Facilities (BS): Found {len(all_facilities_bs)} items.")
        else:
            print("    - All Facilities (BS): No specific facility labels found across categories.")
    else:
        print("    - All Facilities (BS): No main facility category wrappers found.")

    # --- 6. Extract Room Availability ---
    room_availability_element = soup.find('p', class_='detail-kost-overview__availability-text bg-c-text bg-c-text--body-2')
    if room_availability_element:
        room_availability_bs = room_availability_element.get_text(strip=True)
        print(f"    - Room Availability (BS): '{room_availability_bs}'")
    else:
        print("    - Room Availability (BS): Element not found.")

    # --- 7. Extract Deposit Amount ---
    deposit_amount_element = soup.find('p', class_='detail-kost-rule-item__pricing-amount bg-c-text bg-c-text--body-1')
    if deposit_amount_element:
        deposit_amount_bs = deposit_amount_element.get_text(strip=True)
        print(f"    - Deposit Amount (BS): '{deposit_amount_bs}'")
    else:
        print("    - Deposit Amount (BS): Element not found.")


    return {
        "owner_name": owner_name,
        "room_size": room_size,
        "is_electricity_included": is_electricity_included,
        "price_before_discount_bs": price_before_discount_bs,
        "all_facilities_bs": all_facilities_bs,
        "room_availability_bs": room_availability_bs,
        "deposit_amount_bs": deposit_amount_bs
    }

class ImprovedMamikosScraper:
    def __init__(self):
        """Initialize Chrome driver with better anti-detection measures"""
        chrome_options = Options()
        
        # --- Anti-detection setup ---
        # Disable automation detection features
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # General stealth options
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox") # Bypass OS security model (needed in some environments)
        chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems (often paired with --no-sandbox)
        chrome_options.add_argument("--disable-notifications") # Suppress notification pop-ups
        chrome_options.add_argument("--log-level=3") # Suppress verbose logs from Chrome
        chrome_options.add_argument("--disable-popup-blocking") # Disable pop-up blocker
        chrome_options.add_argument("--disable-setuid-sandbox") # Another sandbox related option for stealth
        chrome_options.add_argument("--allow-running-insecure-content") # Allow mixed content
        chrome_options.add_argument("--disable-webgl") # Disable WebGL for fingerprinting mitigation
        chrome_options.add_argument("--disable-software-rasterizer") # Disable software rasterizer for rendering consistency
        chrome_options.add_argument("--no-default-browser-check") # Prevent "make default browser" prompts
        chrome_options.add_argument("--ignore-certificate-errors") # Ignore certificate errors
        chrome_options.add_argument("--disable-sync") # Disable sync services
        chrome_options.add_argument("--mute-audio") # Mute audio

        # Headless mode for background execution
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu") 
        
        # Set a consistent window size for headless (important for responsive sites)
        chrome_options.add_argument("--window-size=1920,1080") 

        # --- User-Agent Rotation ---
        # A list of common User-Agent strings to rotate through
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; CrOS x86_64 15183.78.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.5304.110 Safari/537.36" # Example Chrome OS
        ]
        selected_user_agent = random.choice(user_agents)
        chrome_options.add_argument(f"user-agent={selected_user_agent}")
        print(f"  Using User-Agent: {selected_user_agent}")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Execute script to hide webdriver property (important anti-detection technique)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.scraped_data = []
        
    def human_like_delay(self, min_seconds=1, max_seconds=3):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        
    def scroll_slowly(self, element):
        """Scroll to element slowly to mimic human behavior"""
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        self.human_like_delay(1, 3)
        
    def wait_for_page_load(self, timeout=20):
        """Wait for the product page to fully load"""
        print("⏳ Waiting for product page to load...")
        
        load_indicators = [
            "p.detail-title__room-name", 
            ".detail-title__room-name",
            "h1", "h2", 
            "[class*='detail-title']",
            "main", ".container",
            ".detail-kost-owner-section__owner-title" # Added owner title as a robust indicator
        ]
        
        for indicator in load_indicators:
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, indicator))
                )
                print(f"✓ Page loaded (detected: {indicator})")
                return True
            except TimeoutException:
                continue
        
        print("⚠️ Could not confirm page load, proceeding anyway...")
        return False
        
    def wait_for_any_element(self, selectors, timeout=10):
        """Wait for any of the given selectors to be present"""
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                return element, selector
            except TimeoutException:
                continue
        return None, None
        
    def extract_text_with_priority(self, selectors, field_name):
        """
        Extract text using priority-based selector matching
        Put the working selectors from product 2 first
        """
        for i, selector in enumerate(selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    text_methods = [
                        lambda e: e.text.strip(),
                        lambda e: e.get_attribute('textContent').strip() if e.get_attribute('textContent') else '',
                        lambda e: e.get_attribute('innerText').strip() if e.get_attribute('innerText') else '',
                        lambda e: e.get_attribute('value').strip() if e.get_attribute('value') else ''
                    ]
                    
                    for method in text_methods:
                        try:
                            text = method(element)
                            if text and len(text.strip()) > 0:
                                if self.validate_extracted_text(text, field_name):
                                    print(f"✓ {field_name}: '{text}' (selector #{i+1}: {selector})")
                                    return text
                        except:
                            continue
                            
            except Exception as e:
                continue
        
        print(f"❌ {field_name}: Not found with any selector")
        return "Not found"
    
    def validate_extracted_text(self, text, field_name):
        """Validate extracted text makes sense for the field"""
        text_lower = text.lower()
        
        skip_patterns = ['selengkapnya', 'chat', 'tanya pemilik', 'ajukan sewa', 'estimasi', 'promo', 'kuota terbatas', 'icon chevron right'] # Added 'promo' and related
        if any(pattern in text_lower for pattern in skip_patterns):
            if field_name not in ['Owner Name']: # Owner name can sometimes contain valid terms from skip_patterns
                return False
        
        if field_name == "Price":
            return 'rp' in text_lower and any(char.isdigit() for char in text)
        elif field_name == "Rating":
            return any(char.isdigit() for char in text) and len(text) < 10
        elif field_name == "Room Name":
            return len(text) > 5 and 'kos' in text_lower
        elif field_name == "Discount": # Revised validation for discount
            # A valid discount should contain numbers, a percentage, or specific discount keywords followed by numbers
            if re.search(r'\d+%?', text) or '%' in text: # Matches "10%", "20", "50"
                return True
            if re.search(r'diskon\s*\d+rb', text_lower): # Matches "diskon 100rb"
                return True
            # If it's just "flash", "promo", or other non-quantifiable text, it's not a discount.
            return False 
        
        return True
    
    def debug_page_elements(self):
        """Enhanced debugging to find available elements"""
        print(f"\n🔍 DEBUGGING PAGE: {self.driver.current_url}")
        print(f"Page title: {self.driver.title}")
        print(f"Page source length: {len(self.driver.page_source)}")
        print("-" * 60)
        
        working_selectors = [
            "p.detail-title__room-name",
            "span.rc-price__text.bg-c-text.bg-c-text--title-2", # Specific for price
            "p[data-v-d8a7c31a].detail-kost-overview__rating-text",
            "p[data-v-d8a7c31a].detail-kost-overview__rating-review",
            "p[data-v-d8a7c31a].detail-kost-overview__total-transaction-text",
            "span[data-v-d8a7c31a].detail-kost-overview__gender-box",
            "p[data-v-d8a7c31a].detail-kost-overview__area-text",
            "div.detail-kost-owner-section__owner-title", # Owner Name
            "p.detail-kost-facility-item__label", # Room Size and Electricity likely here
            "img[alt='Tidak termasuk listrik']", # Electricity excluded icon
            "span.rc-price__additional-discount-price.bg-c-text--strikethrough", # Price before promo (new)
            "span.bg-c-text.bg-c-text--label-4.bg-c-text--strikethrough", # Original price (new)
            "div.detail-kost-room-facilities p.detail-kost-facility-item__label", # Room facilities (main)
            "div.detail-kost-bathroom-facilities p.detail-kost-facility-item__label", # Bathroom facilities (new)
            "div.detail-kost-public-facilities p.detail-kost-facility-item__label", # Public facilities (new)
            "p.detail-kost-overview__availability-text", # Room availability (new)
            "p.detail-kost-rule-item__pricing-amount" # Deposit amount (new)
        ]
        
        print("🎯 Checking for key selectors on current page:")
        for selector in working_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✓ Found {len(elements)} element(s) with: {selector}")
                    for i, elem in enumerate(elements[:3]): # Show first 3 elements
                        try:
                            # For img tags, also print alt attribute as it's relevant
                            if elem.tag_name == 'img' and elem.get_attribute('alt'):
                                print(f"    {i+1}. Alt Text: '{elem.get_attribute('alt')}'")
                            else:
                                text = elem.text.strip()
                                print(f"    {i+1}. Text: '{text[:100]}{'...' if len(text) > 100 else ''}'")
                        except:
                            print(f"    {i+1}. (No readable text/attribute)")
                else:
                    print(f"❌ Not found: {selector}")
            except Exception as e:
                print(f"❌ Error with {selector}: {str(e)}")
        
        print("-" * 60)
    
    def extract_product_data(self):
        """Enhanced data extraction prioritizing working selectors"""
        print("\n🎯 EXTRACTING PRODUCT DATA")
        print("=" * 50)
        
        self.wait_for_page_load()
        self.human_like_delay(3, 5)
        
        self.debug_page_elements() # Debug to see elements available after load
        
        data = {
            'url': self.driver.current_url,
            'page_title': self.driver.title
        }
        
        print("\n📊 EXTRACTING FIELDS (from current page HTML):")
        print("-" * 30)

        # --- Aggressive Scrolling to load all content ---
        print("  Initiating aggressive scrolling to load all dynamic content...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        while scroll_attempts < 5: # Try up to 5 scrolls, adjust as needed
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.human_like_delay(2, 3) # Give time for content to load
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("  Reached end of scrollable page or no new content loaded.")
                break
            last_height = new_height
            scroll_attempts += 1
        print(f"  Finished scrolling after {scroll_attempts} attempts.")
        self.human_like_delay(1) # Final small delay

        # --- Specific Wait for Deposit Element before capturing page source ---
        # This explicitly waits for the deposit element to be present in the DOM
        print("  Waiting specifically for deposit amount element to be present...")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'p.detail-kost-rule-item__pricing-amount.bg-c-text.bg-c-text--body-1'))
            )
            print("  Deposit amount element found via explicit wait.")
        except TimeoutException:
            print("  Deposit amount element NOT found via explicit wait. Proceeding without it.")
        
        # Get the full HTML content of the page after Selenium has loaded it and scrolled
        html_content_after_load = self.driver.page_source
        
        # Use the BeautifulSoup function to extract the specific details
        specific_details = scrape_mamikos_details_from_html(html_content_after_load)
        
        # Merge the specific details into the main data dictionary
        data.update(specific_details)
        print("  Specific details extracted via BeautifulSoup merged into data.")

        # Existing extractions for other fields (using Selenium directly)
        room_name_selectors = [
            "p.detail-title__room-name",
            "p[class*='detail-title__room-name']",
            ".detail-title__room-name",
            "h1", "h2", "h3",
            "[class*='title']", "[class*='name']",
            "main h1", "main h2"
        ]
        data['room_name'] = self.extract_text_with_priority(room_name_selectors, "Room Name")
        
        price_selectors = [
            "p[data-v-160ecdd7].bg-c-text.bg-c-text--body-1",
            "span.rc-price__text.bg-c-text.bg-c-text--title-2", # More specific price selector
            "p[class*='bg-c-text'][class*='body-1']",
            ".bg-c-text.bg-c-text--body-1",
            ".bg-c-text--body-1",
            "[class*='price']", "[class*='harga']",
            "*:contains('Rp')", "span:contains('Rp')", "p:contains('Rp')"
        ]
        data['price'] = self.extract_text_with_priority(price_selectors, "Price")
        
        rating_selectors = [
            "p[data-v-d8a7c31a].detail-kost-overview__rating-text",
            "p[class*='detail-kost-overview__rating-text']",
            ".detail-kost-overview__rating-text",
            "[class*='rating-text']",
            "[class*='rating']", "[class*='score']",
            "*:contains('★')", "span:contains('★')"
        ]
        data['rating'] = self.extract_text_with_priority(rating_selectors, "Rating")
        
        rating_count_selectors = [
            "p[data-v-d8a7c31a].detail-kost-overview__rating-review",
            "p[class*='detail-kost-overview__rating-review']",
            ".detail-kost-overview__rating-review",
            "[class*='rating-review']",
            "*:contains('ulasan')", "*:contains('review')"
        ]
        data['rating_count'] = self.extract_text_with_priority(rating_count_selectors, "Rating Count")
        
        transaction_selectors = [
            "p[data-v-d8a7c31a].detail-kost-overview__total-transaction-text",
            "p[class*='detail-kost-overview__total-transaction-text']",
            ".detail-kost-overview__total-transaction-text",
            "[class*='transaction-text']",
            "*:contains('transaksi')", "*:contains('berhasil')"
        ]
        data['transaction_count'] = self.extract_text_with_priority(transaction_selectors, "Transaction Count")
        
        tipe_kos_selectors = [
            "span[data-v-d8a7c31a].detail-kost-overview__gender-box",
            "span[class*='detail-kost-overview__gender-box']",
            ".detail-kost-overview__gender-box",
            "[class*='gender-box']",
            "*:contains('Putra')", "*:contains('Putri')", "*:contains('Campur')"
        ]
        data['tipe_kos'] = self.extract_text_with_priority(tipe_kos_selectors, "Tipe Kos")
        
        location_selectors = [
            "p[data-v-d8a7c31a].detail-kost-overview__area-text",
            "p[class*='detail-kost-overview__area-text']",
            ".detail-kost-overview__area-text",
            "[class*='area-text']",
            "[class*='location']", "[class*='area']", "[class*='lokasi']"
        ]
        data['location'] = self.extract_text_with_priority(location_selectors, "Location")
        
        discount_selectors = [
            "span[data-v-160ecdd7].bg-c-text.bg-c-text--label-3",
            "span[class*='bg-c-text'][class*='label-3']",
            ".bg-c-text--label-3",
            "[class*='discount']", "[class*='diskon']",
            "*:contains('%')", "*:contains('diskon')"
        ]
        data['discount_amount'] = self.extract_text_with_priority(discount_selectors, "Discount")
        
        print(f"\n✅ Data extraction completed for: {data.get('room_name', 'Unknown')}")
        return data
    
    def scrape_products(self, csv_file_path, region_name="Unknown Region", max_products=None): # Added region_name parameter
        """Enhanced scraping with better navigation handling for URLs from CSV"""
        urls_from_csv = []
        try:
            with open(csv_file_path, mode='r', newline='', encoding='utf-8') as file:
                csv_reader = csv.reader(file)
                next(csv_reader, None) # Skip the header row
                for row in csv_reader:
                    if row:
                        urls_from_csv.append(row[0].strip())
            print(f"\nSuccessfully loaded {len(urls_from_csv)} URLs from '{csv_file_path}'.")
        except FileNotFoundError:
            print(f"\nError: CSV file '{csv_file_path}' not found. Please check the path.")
            return False
        except Exception as e:
            print(f"\nAn error occurred while reading the CSV file: {e}")
            return False

        if not urls_from_csv:
            print("\nNo URLs to process from CSV. Exiting.")
            return False
            
        urls_to_scrape = urls_from_csv
        if max_products is not None and max_products < len(urls_to_scrape): # Check for None explicitly
            urls_to_scrape = urls_to_scrape[:max_products]
            print(f"Scraping the first {max_products} URLs as requested.")
        else: # Add this else block to confirm all URLs are being processed if no limit
            print(f"Scraping all {len(urls_to_scrape)} URLs from the CSV.")


        for i, url in enumerate(urls_to_scrape):
            print(f"\n{'='*60}")
            print(f"PROCESSING PRODUCT {i+1} OF {len(urls_to_scrape)}: {url}")
            print(f"{'='*60}")
            
            try:
                self.driver.get(url)
                self.human_like_delay(3, 5) # Initial delay for page load
                
                # Extract data using the combined method
                product_data = self.extract_product_data()
                product_data['product_number'] = i + 1
                product_data['region'] = region_name # Add the region to the scraped data
                self.scraped_data.append(product_data)
                
            except WebDriverException as e: # Catch WebDriver-specific errors (e.g., connection issues, crashes)
                print(f"❌ WebDriver Error processing URL {url}: {str(e)}")
                print("  Attempting to restart WebDriver for the next URL...")
                self.close() # Close current driver
                self.__init__() # Re-initialize the driver
                continue # Continue to the next URL
            except Exception as e:
                print(f"❌ General Error processing URL {url}: {str(e)}")
                continue
            
        return len(self.scraped_data) > 0
            
    def print_results(self):
        """Print scraped results in a formatted way"""
        print(f"\n{'='*60}")
        print(f"SCRAPING RESULTS - {len(self.scraped_data)} PRODUCTS")
        print(f"{'='*60}")
        
        for i, data in enumerate(self.scraped_data):
            print(f"\n--- PRODUCT {i+1} ---")
            
            # Define a preferred order for key fields, including the specific ones
            ordered_fields = [
                'product_number', 'room_name', 'price', 'owner_name',
                'room_size', 'room_availability_bs', 'deposit_amount_bs', 
                'is_electricity_included', 'price_before_discount_bs',
                'discount_amount', 
                'all_facilities_bs', 
                'rating', 'rating_count', 'transaction_count', 'tipe_kos',
                'location', 'region', 'url', 'page_title' # Added 'region' to ordered fields
            ]
            
            # Print fields in preferred order
            for field in ordered_fields:
                if field in data:
                    value = data[field]
                    if isinstance(value, list):
                        if value and value != ["Not found"]:
                            print(f"  {field.replace('_', ' ').capitalize()}: {', '.join(map(str, value[:5]))}{'...' if len(value) > 5 else ''}")
                        else:
                            print(f"  {field.replace('_', ' ').capitalize()}: Not found")
                    else:
                        display_value = str(value)
                        if len(display_value) > 100: # Truncate long strings for display
                            display_value = f"{display_value[:100]}..."
                        print(f"  {field.replace('_', ' ').capitalize()}: {display_value}")
                else:
                    print(f"  {field.replace('_', ' ').capitalize()}: Not Available") # Indicate if a field is genuinely missing from data

            print("-" * 40)
    
    def save_data_to_json(self, filename="mamikos_data_bekasi.json"):
        """Save scraped data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
            print(f"✓ Data saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving data to JSON: {str(e)}")

    def save_data_to_csv(self, filename="mamikos_data_jakarta_selatan.csv"):
        """Save scraped data to CSV file using pandas."""
        if not self.scraped_data:
            print("No data to save to CSV.")
            return

        try:
            # Flatten lists into strings for CSV compatibility
            df_data = []
            for item in self.scraped_data:
                row = item.copy()
                for key, value in row.items():
                    if isinstance(value, list):
                        row[key] = "; ".join(map(str, value)) # Join list items with a semicolon
                df_data.append(row)

            df = pd.DataFrame(df_data)
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"✓ Data saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving data to CSV: {str(e)}")
    
    def close(self):
        """Close the browser"""
        try:
            self.driver.quit()
            print("✓ Browser closed")
        except:
            pass

# Test the improved functionality
if __name__ == "__main__":
    # Define the path to your CSV file
    user_input = input("Enter the CSV file path: ").strip().strip('"')
    csv_file_path = Path(user_input)
    region = input("Input Region Name: ")
    
    scraper = ImprovedMamikosScraper()
    
    try:
        print("🚀 Starting Improved Mamikos Scraper...")
        print("✨ Integrating specific detail extraction via BeautifulSoup on loaded page source.")
        print("✨ Enhanced anti-detection and error handling for long runs.")
        print("-" * 60)
        
        # Scrape products directly from the CSV URLs
        # Pass the desired region name here
        success = scraper.scrape_products(csv_file_path, region_name=region) 
        
        if success:
            print("\n✅ SCRAPING COMPLETED!")
            scraper.print_results()
            scraper.save_data_to_json()
            scraper.save_data_to_csv() # Save to CSV
        else:
            print("\n❌ SCRAPING FAILED or no URLs processed!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Scraping failed with error: {str(e)}")
    finally:
        scraper.close()
