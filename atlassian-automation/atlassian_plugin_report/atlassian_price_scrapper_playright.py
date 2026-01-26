#!/usr/bin/env python3
"""
Atlassian Marketplace Pricing Scraper - CSV Batch Processor (Linux Headless)
Reads plugin_price_scrapping.csv, scrapes pricing for each row, and adds two new columns.
"""

from playwright.sync_api import sync_playwright
import pandas as pd
import re
from datetime import datetime
from urllib.parse import urlparse
import os

# ===== CONFIGURATION =====
# Update these paths for your Linux VM
INPUT_CSV = "/export/scripts/ram/plugin_price_scrapping.csv"
OUTPUT_CSV = "/export/scripts/ram/plugin_price_scrapping_with_pricing.csv"
DEBUG = False
SLOW_MO = 500
HEADLESS = True  # Headless mode for Linux VM (no GUI)
# =========================

def extract_plugin_id_from_url(url: str) -> str:
    """Extract plugin ID from Marketplace URL."""
    if pd.isna(url) or not url:
        return None
    # URL format: https://marketplace.atlassian.com/plugins/com.onresolve.jira.groovy.groovyrunner
    parts = url.strip().split('/plugins/')
    if len(parts) == 2:
        return parts[1].split('?')[0].split('#')[0].strip()
    return None

def extract_usd_number(price_str: str) -> str:
    """Extract just the USD number from price string like 'USD 36,329' -> '36329'."""
    if not price_str or pd.isna(price_str):
        return ""
    
    # Remove currency symbols and text
    price_clean = re.sub(r'[^\d,.]', '', str(price_str))
    # Remove commas
    price_clean = price_clean.replace(',', '')
    # Extract number
    match = re.search(r'(\d+(?:\.\d+)?)', price_clean)
    if match:
        # Return as integer string (no decimals for USD)
        return str(int(float(match.group(1))))
    return ""

def normalize_tier(tier_str: str) -> str:
    """Normalize tier string to match marketplace format."""
    if pd.isna(tier_str) or not tier_str or tier_str.strip().lower() in ['unknown tier', 'n/a']:
        return None
    
    # Extract just the number
    match = re.search(r'(\d+)', str(tier_str))
    if match:
        return match.group(1)
    return None

def scrape_plugin_playwright(plugin_id: str, page, target_tier: str) -> dict:
    """Scrape pricing for a single plugin."""
    result = {
        'price': None,
        'status': 'failed',
        'error': None
    }
    
    try:
        url = f"https://marketplace.atlassian.com/plugins/{plugin_id}"
        
        page.goto(url, wait_until='networkidle', timeout=60000)
        page.wait_for_timeout(2000)
        
        # Step 1: Click View dropdown
        try:
            view_button = page.locator("button:has-text('View for')").first
            view_button.wait_for(state='visible', timeout=10000)
            view_button.click()
            page.wait_for_timeout(1500)
        except Exception as e:
            result['error'] = f'View dropdown: {str(e)[:50]}'
            return result
        
        # Step 2: Click Data Center
        try:
            page.wait_for_selector("//*[contains(text(), 'Hosting Types')]", timeout=5000)
            page.wait_for_timeout(500)
            
            dc_selectors = [
                "//*[contains(text(), 'Hosting Types')]/following-sibling::*//*[contains(text(), 'Data Center')]",
                "//*[contains(text(), 'Hosting Types')]/..//*[contains(text(), 'Data Center')]",
                "//ul//*[contains(text(), 'Data Center')]",
                "button:has-text('Data Center')",
                "a:has-text('Data Center')",
                "//*[contains(text(), 'Data Center')]",
            ]
            
            dc_clicked = False
            for selector in dc_selectors:
                try:
                    if selector.startswith("//"):
                        element = page.locator(f"xpath={selector}").first
                    else:
                        element = page.locator(selector).first
                    
                    element.wait_for(state='visible', timeout=3000)
                    element.click(timeout=5000)
                    page.wait_for_load_state('networkidle', timeout=30000)
                    page.wait_for_timeout(2000)
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
        
        # Step 3: Navigate to Pricing tab via URL
        try:
            current_url = page.url
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
                
                page.goto(new_url, wait_until='networkidle', timeout=30000)
                page.wait_for_timeout(2000)
            else:
                result['error'] = 'Could not determine URL structure'
                return result
        except Exception as e:
            result['error'] = f'Pricing tab: {str(e)[:50]}'
            return result
        
        # Step 4: Check main table first
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        
        try:
            row = page.locator(f"tr:has-text('Up to {target_tier} users')").first
            if row.count() > 0:
                cells = row.locator("td")
                if cells.count() >= 2:
                    price = cells.nth(1).text_content().strip()
                    result['price'] = price
                    result['status'] = 'success'
                    return result
        except:
            pass
        
        # Step 5: Click Explore pricing link
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        
        explore_selectors = [
            "a:has-text('Explore pricing for different user tiers')",
            "//a[contains(text(), 'Explore pricing for different user tiers')]",
            "a:has-text('Explore pricing')",
            "//a[contains(text(), 'Explore pricing')]",
            "//a[contains(text(), 'different user tiers')]",
            "//*[contains(text(), 'Explore pricing for different user tiers')]",
        ]
        
        explore_clicked = False
        for selector in explore_selectors:
            try:
                if selector.startswith("//"):
                    element = page.locator(f"xpath={selector}").first
                else:
                    element = page.locator(selector).first
                
                element.wait_for(state='visible', timeout=5000)
                element.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                element.click(timeout=10000)
                page.wait_for_timeout(2000)
                
                # Wait for modal
                try:
                    page.wait_for_selector("//h2[contains(text(), 'Data Center Pricing')]", timeout=15000)
                    explore_clicked = True
                    break
                except:
                    try:
                        page.wait_for_selector("div[role='dialog'], div[class*='modal']", timeout=5000)
                        explore_clicked = True
                        break
                    except:
                        continue
            except:
                continue
        
        if not explore_clicked:
            result['error'] = 'Could not find Explore pricing link'
            return result
        
        # Step 6: Find target tier in modal
        try:
            page.wait_for_timeout(1500)
            
            modal_selectors = [
                "//div[contains(@class, 'modal')]",
                "//div[contains(@role, 'dialog')]",
                "//div[contains(@class, 'dialog')]",
            ]
            
            modal_found = False
            for selector in modal_selectors:
                try:
                    modal = page.locator(f"xpath={selector}").first
                    try:
                        count = modal.count()
                        if count > 0:
                            modal.evaluate("element => element.scrollTop = 0")
                            page.wait_for_timeout(1000)
                            modal_found = True
                            break
                    except:
                        try:
                            modal.wait_for(state='visible', timeout=2000)
                            modal.evaluate("element => element.scrollTop = 0")
                            page.wait_for_timeout(1000)
                            modal_found = True
                            break
                        except:
                            continue
                except:
                    continue
            
            # Search for target tier
            row_selectors = [
                f"//div[contains(@class, 'modal')]//tr[contains(., 'Up to {target_tier} users')]",
                f"//div[contains(@role, 'dialog')]//tr[contains(., 'Up to {target_tier} users')]",
                f"//tr[contains(., 'Up to {target_tier} users')]",
            ]
            
            for selector in row_selectors:
                try:
                    row = page.locator(f"xpath={selector}").first
                    count = row.count()
                    if count > 0:
                        row.scroll_into_view_if_needed()
                        page.wait_for_timeout(300)
                        cells = row.locator("td")
                        if cells.count() >= 2:
                            price = cells.nth(1).text_content().strip()
                            result['price'] = price
                            result['status'] = 'success'
                            return result
                except:
                    continue
            
            # Fallback: search all rows
            try:
                all_rows = page.locator("//div[contains(@class, 'modal')]//tr, //div[contains(@role, 'dialog')]//tr").all()
                for r in all_rows:
                    try:
                        text = r.text_content()
                        if target_tier in text and 'users' in text:
                            r.scroll_into_view_if_needed()
                            page.wait_for_timeout(300)
                            cells = r.locator("td")
                            if cells.count() >= 2:
                                price = cells.nth(1).text_content().strip()
                                result['price'] = price
                                result['status'] = 'success'
                                return result
                    except:
                        continue
            except Exception as e:
                if DEBUG:
                    print(f"  [DEBUG] Fallback search error: {str(e)}")
            
            result['error'] = f'Could not find "Up to {target_tier} users" in modal'
        except Exception as e:
            result['error'] = f'Modal extraction: {str(e)[:80]}'
        
    except Exception as e:
        result['error'] = str(e)[:100]
    
    return result

def main():
    print("=" * 70)
    print("Atlassian Marketplace Pricing Scraper - CSV Batch Processor (Linux Headless)")
    print("=" * 70)
    
    # Read CSV
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: Input file not found: {INPUT_CSV}")
        return
    
    print(f"Reading: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"Found {len(df)} rows to process")
    print(f"Running in HEADLESS mode (no GUI)")
    print()
    
    # Initialize new columns
    df['Listing Price (USD)'] = ""
    df['Price Check Date/Time'] = ""
    
    # Get current timestamp
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Launch browser once
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for idx, row in df.iterrows():
            # Extract plugin ID
            plugin_id = None
            if 'App Key' in df.columns and pd.notna(row.get('App Key')):
                plugin_id = str(row['App Key']).strip()
            elif 'Marketplace URL' in df.columns and pd.notna(row.get('Marketplace URL')):
                plugin_id = extract_plugin_id_from_url(row['Marketplace URL'])
            
            if not plugin_id:
                print(f"[{idx+1}/{len(df)}] SKIP: No plugin ID found for row {idx+1}")
                df.at[idx, 'Price Check Date/Time'] = current_timestamp
                skipped_count += 1
                continue
            
            # Extract user tier
            tier = None
            if 'License Tier' in df.columns and pd.notna(row.get('License Tier')):
                tier = normalize_tier(row['License Tier'])
            
            if not tier:
                print(f"[{idx+1}/{len(df)}] SKIP: {plugin_id} - No valid tier (got: {row.get('License Tier', 'N/A')})")
                df.at[idx, 'Price Check Date/Time'] = current_timestamp
                skipped_count += 1
                continue
            
            # Scrape pricing
            app_name = row.get('App Name', 'Unknown')
            print(f"[{idx+1}/{len(df)}] Processing: {app_name} (Tier: {tier})")
            
            result = scrape_plugin_playwright(plugin_id, page, tier)
            
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
            
            # Small delay between requests
            page.wait_for_timeout(1000)
        
        browser.close()
    
    # Save results
    print()
    print("=" * 70)
    print("Saving results...")
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to: {OUTPUT_CSV}")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total rows: {len(df)}")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Success rate: {success_count/(len(df)-skipped_count)*100:.1f}%" if (len(df)-skipped_count) > 0 else "N/A")
    print()

if __name__ == "__main__":
    main()
