#!/usr/bin/env python3
"""
Atlassian Marketplace Pricing Scraper - CSV Batch Processor (Selenium - Enhanced Modal Search)
Works with Python 3.6.8+
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import re
from datetime import datetime
import os
import time

# ===== CONFIGURATION =====
INPUT_CSV = "/export/scripts/ram/plugin_price_scrapping.csv"
OUTPUT_CSV = "/export/scripts/ram/plugin_price_scrapping_with_pricing.csv"
HEADLESS = True
DEBUG = False  # Set to True to see what's happening in modal
# =========================

def extract_plugin_id_from_url(url: str) -> str:
    """Extract plugin ID from Marketplace URL."""
    if pd.isna(url) or not url:
        return None
    parts = url.strip().split('/plugins/')
    if len(parts) == 2:
        return parts[1].split('?')[0].split('#')[0].strip()
    return None

def extract_usd_number(price_str: str) -> str:
    """Extract just the USD number from price string."""
    if not price_str or pd.isna(price_str):
        return ""
    price_clean = re.sub(r'[^\d,.]', '', str(price_str))
    price_clean = price_clean.replace(',', '')
    match = re.search(r'(\d+(?:\.\d+)?)', price_clean)
    if match:
        return str(int(float(match.group(1))))
    return ""

def normalize_tier(tier_str: str) -> str:
    """Normalize tier string to match marketplace format."""
    if pd.isna(tier_str) or not tier_str or tier_str.strip().lower() in ['unknown tier', 'n/a']:
        return None
    match = re.search(r'(\d+)', str(tier_str))
    if match:
        return match.group(1)
    return None

def find_tier_in_modal(driver, target_tier: str) -> dict:
    """Enhanced function to find tier in modal with multiple search strategies."""
    result = {'price': None, 'found': False}
    
    # Strategy 1: Direct XPath with exact match
    patterns = [
        f"Up to {target_tier} users",
        f"Up to {int(target_tier):,} users",  # With comma: "1,000"
        f"{target_tier} users",
        f"{int(target_tier):,} users",  # With comma: "1,000"
        f"Up to {target_tier}",
        f"{target_tier}",
    ]
    
    # Try each pattern
    for pattern in patterns:
        try:
            selectors = [
                f"//tr[contains(., '{pattern}')]",
                f"//div[contains(@class, 'modal')]//tr[contains(., '{pattern}')]",
                f"//div[@role='dialog']//tr[contains(., '{pattern}')]",
                f"//table//tr[contains(., '{pattern}')]",
            ]
            
            for selector in selectors:
                try:
                    row = driver.find_element_by_xpath(selector)
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                    time.sleep(0.3)
                    cells = row.find_elements_by_tag_name("td")
                    if len(cells) >= 2:
                        price = cells[1].text.strip()
                        result['price'] = price
                        result['found'] = True
                        if DEBUG:
                            print(f"    [DEBUG] Found using pattern '{pattern}' in selector '{selector}'")
                        return result
                except:
                    continue
        except:
            continue
    
    # Strategy 2: Find all rows and search by text content
    try:
        # Get all table rows in modal
        all_rows = driver.find_elements_by_xpath(
            "//div[contains(@class, 'modal')]//tr | "
            "//div[@role='dialog']//tr | "
            "//table//tr"
        )
        
        if DEBUG:
            print(f"    [DEBUG] Found {len(all_rows)} rows in modal")
        
        for row in all_rows:
            try:
                row_text = row.text
                if DEBUG and len(all_rows) < 20:  # Only print if not too many rows
                    print(f"    [DEBUG] Row text: {row_text[:100]}")
                
                # Check if tier number is in the row (with or without comma)
                tier_num = int(target_tier)
                tier_with_comma = f"{tier_num:,}"
                
                # Match if row contains the tier number and "user" keyword
                if (target_tier in row_text or tier_with_comma in row_text) and 'user' in row_text.lower():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                    time.sleep(0.5)
                    cells = row.find_elements_by_tag_name("td")
                    if len(cells) >= 2:
                        price = cells[1].text.strip()
                        if price and price != '':
                            result['price'] = price
                            result['found'] = True
                            if DEBUG:
                                print(f"    [DEBUG] Found price '{price}' in row: {row_text[:80]}")
                            return result
            except Exception as e:
                if DEBUG:
                    print(f"    [DEBUG] Error processing row: {str(e)[:50]}")
                continue
    except Exception as e:
        if DEBUG:
            print(f"    [DEBUG] Error in Strategy 2: {str(e)[:50]}")
    
    # Strategy 3: Search by table cell content
    try:
        # Find all cells that might contain the tier
        cells = driver.find_elements_by_xpath(
            "//div[contains(@class, 'modal')]//td | "
            "//div[@role='dialog']//td | "
            "//table//td"
        )
        
        for cell in cells:
            cell_text = cell.text.strip()
            tier_num = int(target_tier)
            tier_with_comma = f"{tier_num:,}"
            
            if (target_tier in cell_text or tier_with_comma in cell_text) and 'user' in cell_text.lower():
                # Found the tier cell, get the price from next cell or parent row
                try:
                    # Try to get parent row
                    row = cell.find_element_by_xpath("./ancestor::tr[1]")
                    row_cells = row.find_elements_by_tag_name("td")
                    if len(row_cells) >= 2:
                        # Find which cell has the tier
                        for idx, rc in enumerate(row_cells):
                            if target_tier in rc.text or tier_with_comma in rc.text:
                                # Price should be in next cell
                                if idx + 1 < len(row_cells):
                                    price = row_cells[idx + 1].text.strip()
                                    if price:
                                        result['price'] = price
                                        result['found'] = True
                                        if DEBUG:
                                            print(f"    [DEBUG] Found price '{price}' using cell search")
                                        return result
                except:
                    pass
    except Exception as e:
        if DEBUG:
            print(f"    [DEBUG] Error in Strategy 3: {str(e)[:50]}")
    
    return result

def scrape_plugin_selenium(plugin_id: str, driver, target_tier: str) -> dict:
    """Scrape pricing for a single plugin using Selenium."""
    result = {
        'price': None,
        'status': 'failed',
        'error': None
    }
    
    try:
        url = f"https://marketplace.atlassian.com/plugins/{plugin_id}"
        if DEBUG:
            print(f"    [DEBUG] Navigating to: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        
        # Step 1: Click View dropdown
        try:
            view_selectors = [
                (By.XPATH, "//button[contains(text(), 'View for')]"),
                (By.XPATH, "//button[contains(., 'View for')]"),
                (By.XPATH, "//*[@aria-label='View for']"),
            ]
            
            view_clicked = False
            for by, selector in view_selectors:
                try:
                    view_button = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", view_button)
                    time.sleep(0.5)
                    view_button.click()
                    time.sleep(2)
                    view_clicked = True
                    break
                except:
                    continue
            
            if not view_clicked:
                buttons = driver.find_elements_by_tag_name("button")
                for btn in buttons:
                    if 'view' in btn.text.lower():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.5)
                        btn.click()
                        time.sleep(2)
                        view_clicked = True
                        break
            
            if not view_clicked:
                result['error'] = 'View dropdown not found'
                return result
        except Exception as e:
            result['error'] = f'View dropdown error: {str(e)[:50]}'
            return result
        
        # Step 2: Click Data Center
        try:
            time.sleep(1)
            dc_selectors = [
                "//*[contains(text(), 'Hosting Types')]/following-sibling::*//*[contains(text(), 'Data Center')]",
                "//*[contains(text(), 'Hosting Types')]/..//*[contains(text(), 'Data Center')]",
                "//ul//*[contains(text(), 'Data Center')]",
                "//button[contains(text(), 'Data Center')]",
                "//a[contains(text(), 'Data Center')]",
            ]
            
            dc_clicked = False
            for selector in dc_selectors:
                try:
                    element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(0.5)
                    element.click()
                    time.sleep(3)
                    dc_clicked = True
                    break
                except:
                    continue
            
            if not dc_clicked:
                result['error'] = 'Could not find Data Center option'
                return result
        except Exception as e:
            result['error'] = f'Data Center: {str(e)[:50]}'
            return result
        
        # Step 3: Navigate to Pricing tab
        try:
            current_url = driver.current_url
            if '?tab=' in current_url or '&tab=' in current_url:
                if '?tab=' in current_url:
                    new_url = current_url.replace('?tab=overview', '?tab=pricing').replace('?tab=reviews', '?tab=pricing')
                else:
                    new_url = current_url.replace('&tab=overview', '&tab=pricing').replace('&tab=reviews', '&tab=pricing')
                
                if 'hosting=datacenter' not in new_url:
                    if '?' in new_url:
                        new_url += '&hosting=datacenter'
                    else:
                        new_url += '?hosting=datacenter'
                
                driver.get(new_url)
                time.sleep(3)
            else:
                result['error'] = 'Could not determine URL structure'
                return result
        except Exception as e:
            result['error'] = f'Pricing tab: {str(e)[:50]}'
            return result
        
        # Step 4: Check main table first
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        try:
            # Try multiple patterns for main table
            patterns = [
                f"Up to {target_tier} users",
                f"Up to {int(target_tier):,} users",
                f"{target_tier} users",
            ]
            for pattern in patterns:
                try:
                    row = driver.find_element_by_xpath(f"//tr[contains(., '{pattern}')]")
                    cells = row.find_elements_by_tag_name("td")
                    if len(cells) >= 2:
                        price = cells[1].text.strip()
                        result['price'] = price
                        result['status'] = 'success'
                        return result
                except:
                    continue
        except:
            pass
        
        # Step 5: Click Explore pricing link
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        explore_selectors = [
            "//a[contains(text(), 'Explore pricing for different user tiers')]",
            "//a[contains(., 'Explore pricing for different user tiers')]",
            "//a[contains(text(), 'Explore pricing')]",
        ]
        
        explore_clicked = False
        for selector in explore_selectors:
            try:
                element = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)
                element.click()
                time.sleep(2)
                
                # Wait for modal
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Data Center Pricing')] | //h2[contains(., 'Data Center Pricing')] | //div[@role='dialog'] | //div[contains(@class, 'modal')]"))
                    )
                    explore_clicked = True
                    break
                except:
                    continue
            except:
                continue
        
        if not explore_clicked:
            result['error'] = 'Could not find Explore pricing link'
            return result
        
        # Step 6: Find target tier in modal - ENHANCED
        try:
            time.sleep(2)  # Wait for modal to fully render
            
            # Scroll modal to top first
            try:
                modal = driver.find_element_by_xpath("//div[@role='dialog'] | //div[contains(@class, 'modal')]")
                driver.execute_script("arguments[0].scrollTop = 0;", modal)
                time.sleep(0.5)
            except:
                pass
            
            # Use enhanced search function
            search_result = find_tier_in_modal(driver, target_tier)
            
            if search_result['found']:
                result['price'] = search_result['price']
                result['status'] = 'success'
                return result
            else:
                result['error'] = f'Could not find "Up to {target_tier} users" in modal'
                if DEBUG:
                    # Take screenshot for debugging
                    try:
                        driver.save_screenshot(f"/tmp/modal_error_{plugin_id}_{target_tier}.png")
                        print(f"    [DEBUG] Screenshot saved to /tmp/modal_error_{plugin_id}_{target_tier}.png")
                    except:
                        pass
        except Exception as e:
            result['error'] = f'Modal extraction: {str(e)[:80]}'
        
    except Exception as e:
        result['error'] = str(e)[:100]
    
    return result

def main():
    print("=" * 70)
    print("Atlassian Marketplace Pricing Scraper - CSV Batch Processor (Selenium)")
    print("=" * 70)
    
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: Input file not found: {INPUT_CSV}")
        return
    
    print(f"Reading: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"Found {len(df)} rows to process")
    print(f"Running in HEADLESS mode: {HEADLESS}")
    print(f"Debug mode: {DEBUG}")
    print()
    
    df['Listing Price (USD)'] = ""
    df['Price Check Date/Time'] = ""
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for idx, row in df.iterrows():
            plugin_id = None
            if 'App Key' in df.columns and pd.notna(row.get('App Key')):
                plugin_id = str(row['App Key']).strip()
            elif 'Marketplace URL' in df.columns and pd.notna(row.get('Marketplace URL')):
                plugin_id = extract_plugin_id_from_url(row['Marketplace URL'])
            
            if not plugin_id:
                print(f"[{idx+1}/{len(df)}] SKIP: No plugin ID found")
                df.at[idx, 'Price Check Date/Time'] = current_timestamp
                skipped_count += 1
                continue
            
            tier = None
            if 'License Tier' in df.columns and pd.notna(row.get('License Tier')):
                tier = normalize_tier(row['License Tier'])
            
            if not tier:
                print(f"[{idx+1}/{len(df)}] SKIP: {plugin_id} - No valid tier")
                df.at[idx, 'Price Check Date/Time'] = current_timestamp
                skipped_count += 1
                continue
            
            app_name = row.get('App Name', 'Unknown')
            print(f"[{idx+1}/{len(df)}] Processing: {app_name} (Tier: {tier})")
            
            result = scrape_plugin_selenium(plugin_id, driver, tier)
            
            if result['status'] == 'success':
                price_str = result['price']
                price_number = extract_usd_number(price_str)
                df.at[idx, 'Listing Price (USD)'] = price_number
                df.at[idx, 'Price Check Date/Time'] = current_timestamp
                print(f"  ✓ Price: {price_str} (USD: {price_number})")
                success_count += 1
            else:
                df.at[idx, 'Listing Price (USD)'] = ""
                df.at[idx, 'Price Check Date/Time'] = current_timestamp
                print(f"  ✗ Failed: {result['error']}")
                failed_count += 1
            
            time.sleep(1)
        
        driver.quit()
    
    except Exception as e:
        print(f"ERROR setting up Chrome driver: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("=" * 70)
    print("Saving results...")
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to: {OUTPUT_CSV}")
    print()
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total rows: {len(df)}")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped: {skipped_count}")
    if (len(df) - skipped_count) > 0:
        print(f"Success rate: {success_count/(len(df)-skipped_count)*100:.1f}%")
    print()

if __name__ == "__main__":
    main()
