from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import random
import csv # Import csv module for saving data
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

class ImprovedMamikosScraper:
    def __init__(self):
        """Initialize Chrome driver with better anti-detection measures"""
        chrome_options = Options()
        
        # Better anti-detection setup
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Add user agent to look more like a real browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Execute script to hide webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Set window size to common resolution
        self.driver.set_window_size(1920, 1080)
        
        # This will now store the URLs of successfully opened product pages
        self.opened_product_urls = []
        
    def human_like_delay(self, min_seconds=1, max_seconds=3):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
        
    def scroll_slowly(self, element):
        """Scroll to element slowly to mimic human behavior"""
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        self.human_like_delay(1, 3)
        
    def wait_for_page_load(self, timeout=20):
        """Wait for the initial search page or product page to fully load"""
        print("⏳ Waiting for page to load...")
        
        # Wait for any key indicator that the page has loaded
        load_indicators = [
            ".kost-rc", # For search page
            "p.detail-title__room-name", # For product detail page
            "body", # Fallback to body
            "main" # Fallback to main content area
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
        
    # Removed handle_popup method as per user request
    
    def scrape_products(self, search_url): 
        """
        Navigates to the search page, first clicks 'Load More' multiple times to load all content,
        then opens each unique product in a new tab, saves its URL, closes the tab, and repeats.
        Pop-up handling has been removed as per request.
        """
        print(f"🚀 Loading search page: {search_url}")
        self.driver.get(search_url)
        
        # Wait for the search page to load
        self.wait_for_page_load()
        self.human_like_delay(3, 5) # Additional human-like delay
        # Removed self.handle_popup() call here
        
        processed_urls_set = set(self.opened_product_urls) # Keep track of already processed URLs
        
        # --- Phase 1: Load all content via "Load More" button clicks ---
        print("\n--- Phase 1: Loading all content via 'Load More' clicks ---")
        pagination_clicks_done = 0
        MAX_PAGINATION_CLICKS = 15 # Attempt to click at least 13 times, setting a generous max
        scroll_attempts_without_new_content = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while pagination_clicks_done < MAX_PAGINATION_CLICKS:
            print(f"  Attempting pagination click {pagination_clicks_done + 1}...")

            # Try to find and click the "Load More" button
            pagination_button_selectors = [
                # Prioritize the specific selector from user's working code
                (By.CSS_SELECTOR, "a.list__content-load-link[data-v-4a297354][class*='list__content-load-link']"),
                (By.XPATH, "//a[contains(., 'Lihat lebih banyak lagi') and contains(@class, 'list__content-load-link')]"),
                (By.XPATH, "//button[contains(., 'Lihat lebih banyak lagi')]"), 
                (By.XPATH, "//span[contains(., 'Lihat lebih banyak lagi')]"), 
                (By.CSS_SELECTOR, "button.Button__solid"), # Common button class
                (By.CSS_SELECTOR, "div.sticky-bottom-button button"), # Button within a sticky footer
                (By.CSS_SELECTOR, "button[class*='load-more']"), # Generic load more button
                (By.CSS_SELECTOR, "[data-testid='load-more-button']"), # If they use data-testids
            ]
            
            load_more_button = None
            for selector_type, selector_value in pagination_button_selectors:
                try:
                    load_more_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"  ✓ 'Load More' button found with selector: {selector_value}")
                    break
                except TimeoutException:
                    continue
                except StaleElementReferenceException:
                    print("  StaleElementReferenceException on load more button, retrying selector...")
                    self.human_like_delay(0.5)
                    continue
                except Exception as e:
                    print(f"  Error finding 'Load More' button with selector {selector_value}: {e}")
                    continue
            
            if load_more_button:
                try:
                    self.scroll_slowly(load_more_button) # Scroll to button first
                    print("  Clicking 'Load More' button...")
                    self.driver.execute_script("arguments[0].click();", load_more_button) # Use JS click for robustness
                    self.human_like_delay(4, 6) # Give time for new content to load
                    pagination_clicks_done += 1
                    
                    # Check if new content actually loaded by comparing page height
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        scroll_attempts_without_new_content += 1
                        print(f"  ⚠️ 'Load More' clicked, but page height did not change. Attempts without new content: {scroll_attempts_without_new_content}")
                        if scroll_attempts_without_new_content >= 2: # Stop after 2 consecutive attempts with no new content
                            print("  Stopping pagination: Consecutive attempts to load more yielded no new content.")
                            break
                    else:
                        scroll_attempts_without_new_content = 0 # Reset counter if new content loaded
                    last_height = new_height # Update last_height for next iteration
                    
                except Exception as e:
                    print(f"  ❌ Error clicking 'Load More' button: {e}. Ending pagination.")
                    break # Break loop if button click fails
            else:
                print("  No more 'Load More' button found. Ending pagination phase.")
                break # Break loop if button not found

        print(f"\n--- Phase 1 Complete: Clicked 'Load More' {pagination_clicks_done} times. ---")
        self.human_like_delay(1, 2) # Reduced delay here
        
        # --- Phase 2: Process all loaded product cards ---
        print("\n--- Phase 2: Processing all loaded product cards ---")
        
        # Get all product card elements *after* loading all available content
        all_product_cards = self.driver.find_elements(By.CSS_SELECTOR, ".kost-rc")
        total_cards_found_for_processing = len(all_product_cards)
        print(f"Found {total_cards_found_for_processing} product cards to process.")

        if not all_product_cards:
            print("❌ No product cards found after loading all content!")
            return False

        processed_count_in_phase_2 = 0
        for i, card in enumerate(all_product_cards):
            try:
                # Find the clickable element within the current card
                # Re-finding element here to handle potential StaleElementReferenceException
                clickable_element = WebDriverWait(card, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".kost-rc__inner"))
                )
                
                # Get the URL before attempting to click, for checking against processed_urls_set
                card_url = clickable_element.get_attribute('href')

                if card_url in processed_urls_set:
                    # print(f"  Skipping already processed URL: {card_url}") # Optional: for verbose logging
                    continue # Skip if already processed

                print(f"\n--- Processing Product Card {i+1} (URL: {card_url}) ---")
                
                # Get original window handle before opening a new tab
                original_window = self.driver.current_window_handle
                
                print("  Attempting to open in new tab using Ctrl+Click...")
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).click(clickable_element).key_up(Keys.CONTROL).perform()
                
                # Use human-like delay, which is key to your successful tab opening logic
                self.human_like_delay(3, 5) 

                # Get all current window handles
                all_windows_after_click = self.driver.window_handles
                
                # Robust check for a new tab: if the number of handles has increased
                if len(all_windows_after_click) > len(set(self.driver.window_handles).difference({original_window})): 
                    # Find the new window handle (the one that isn't the original)
                    new_tab_handle = [w for w in all_windows_after_click if w != original_window][0]
                    self.driver.switch_to.window(new_tab_handle)
                    
                    current_product_page_url = self.driver.current_url
                    print(f"✓ Opened product page: {current_product_page_url}")
                    
                    # Add the URL of the opened product page to our list and set
                    self.opened_product_urls.append(current_product_page_url)
                    processed_urls_set.add(current_product_page_url)
                    processed_count_in_phase_2 += 1
                    
                    # Close the new tab and return to the original search page
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                    self.human_like_delay(1, 3) # Reduced delay here
                    # Removed self.handle_popup() call here
                    
                else:
                    print(f"❌ Failed to open product {i+1} in new tab. Only {len(all_windows_after_click)} window(s) detected.")
                    # If a new tab didn't open, ensure we are back on the original window
                    if self.driver.current_window_handle != original_window:
                         self.driver.switch_to.window(original_window) # Should already be on original, but for safety
                    self.human_like_delay(1) # Small delay before trying next card
                    # Removed self.handle_popup() call here
                
            except (NoSuchElementException, StaleElementReferenceException) as e:
                print(f"❌ Clickable element not found or became stale for card {i+1}: {e}. Skipping this card.")
                continue # Continue to the next card if the clickable element isn't found or becomes stale
            except Exception as e:
                print(f"❌ General error processing product {i+1}: {str(e)}")
                # Attempt to return to the original window if an error occurs mid-process in a new tab
                try:
                    current_windows = self.driver.window_handles
                    if self.driver.current_window_handle != original_window and len(current_windows) > 1:
                        self.driver.close() # Close the problematic tab
                        self.driver.switch_to.window(original_window)
                    elif len(current_windows) == 1 and self.driver.current_window_handle != original_window:
                         self.driver.switch_to.window(original_window) # Ensure we are on original if it's the only one left
                except:
                    pass # Ignore errors if driver is already quit or window is invalid
                continue # Continue to the next product card
        
        print(f"\n--- Phase 2 Complete: Processed {processed_count_in_phase_2} unique product URLs. ---")
        return len(self.opened_product_urls) > 0 # Return True if any URLs were successfully collected
            
    def print_results(self):
        """Prints the extracted product URLs in a formatted way."""
        print(f"\n{'='*60}")
        print(f"EXTRACTED PRODUCT URLs - {len(self.opened_product_urls)} URLs")
        print(f"{'='*60}")
        if self.opened_product_urls:
            for i, url in enumerate(self.opened_product_urls):
                print(f"URL {i+1}: {url}")
        else:
            print("No URLs to display.")
        print("-" * 40)
    
    def save_links_to_csv(self, filename="mamikos_url_jakarta_timur.csv"):
        """Saves the extracted product URLs to a CSV file."""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow(['Opened_Product_URL']) # Write header row
                for url in self.opened_product_urls:
                    csv_writer.writerow([url]) # Write each URL as a new row
            print(f"✓ Extracted URLs saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving URLs to CSV: {str(e)}")
    
    def close(self):
        """Close the browser"""
        try:
            self.driver.quit()
            print("✓ Browser closed")
        except:
            pass

# Test the improved functionality
if __name__ == "__main__":
    search_url = input("Put Mamikos Search URL here: ")
    
    scraper = ImprovedMamikosScraper()
    
    try:
        print("🚀 Starting Mamikos Product URL Collector...")
        print("This will open product pages, collect their URLs, and save them to a CSV file.")
        print("-" * 60)
        
        # Call the new product scraping method to open tabs and collect URLs for ALL products
        success = scraper.scrape_products(search_url) 
        
        if success:
            print("\n✅ URL COLLECTION COMPLETED!")
            scraper.print_results() # Print the URLs to console
            scraper.save_links_to_csv() # Save the URLs to a CSV file
        else:
            print("\n❌ URL COLLECTION FAILED!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Collection interrupted by user")
    except Exception as e:
        print(f"\n❌ Collection failed with error: {str(e)}")
    finally:
        scraper.close()
