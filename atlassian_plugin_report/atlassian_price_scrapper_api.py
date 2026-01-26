#!/usr/bin/env python3
"""
Atlassian Marketplace Pricing API
REST API endpoint for on-demand pricing lookups
Thread-safe version - creates new browser per request
"""

from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import re
from datetime import datetime
import os
import threading

app = Flask(__name__)

# Lock for serializing browser creation (alternative approach)
_browser_lock = threading.Lock()

def extract_usd_number(price_str: str) -> str:
    """Extract just the USD number from price string."""
    if not price_str or price_str == "":
        return ""
    price_clean = re.sub(r'[^\d,.]', '', str(price_str))
    price_clean = price_clean.replace(',', '')
    match = re.search(r'(\d+(?:\.\d+)?)', price_clean)
    if match:
        return str(int(float(match.group(1))))
    return ""

def normalize_tier(tier_str: str) -> str:
    """Normalize tier string."""
    if not tier_str:
        return None
    match = re.search(r'(\d+)', str(tier_str))
    if match:
        return match.group(1)
    return None

def scrape_plugin_price(plugin_id: str, target_tier: str) -> dict:
    """Scrape pricing for a single plugin - creates new browser per request (thread-safe)."""
    result = {
        'plugin_id': plugin_id,
        'user_tier': target_tier,
        'price_usd': None,
        'price_raw': None,
        'status': 'failed',
        'error': None,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    playwright = None
    browser = None
    context = None
    
    try:
        # Create a NEW browser instance for each request (thread-safe)
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
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
            if context:
                context.close()
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
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
                if context:
                    context.close()
                if browser:
                    browser.close()
                if playwright:
                    playwright.stop()
                return result
        except Exception as e:
            result['error'] = f'Data Center: {str(e)[:50]}'
            if context:
                context.close()
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            return result
        
        # Step 3: Navigate to Pricing tab
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
                if context:
                    context.close()
                if browser:
                    browser.close()
                if playwright:
                    playwright.stop()
                return result
        except Exception as e:
            result['error'] = f'Pricing tab: {str(e)[:50]}'
            if context:
                context.close()
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
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
                    result['price_raw'] = price
                    result['price_usd'] = extract_usd_number(price)
                    result['status'] = 'success'
                    if context:
                        context.close()
                    if browser:
                        browser.close()
                    if playwright:
                        playwright.stop()
                    return result
        except:
            pass
        
        # Step 5: Click Explore pricing link - ENHANCED
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)
        
        explore_selectors = [
            "a:has-text('Explore pricing for different user tiers')",
            "//a[contains(text(), 'Explore pricing for different user tiers')]",
            "//a[contains(., 'Explore pricing for different user tiers')]",
            "a:has-text('Explore pricing')",
            "//a[contains(text(), 'Explore pricing')]",
            "//a[contains(., 'different user tiers')]",
            "//*[contains(text(), 'Explore pricing for different user tiers')]",
            "//*[contains(., 'Explore pricing for different user tiers')]",
        ]
        
        explore_clicked = False
        for selector in explore_selectors:
            try:
                if selector.startswith("//"):
                    element = page.locator(f"xpath={selector}").first
                else:
                    element = page.locator(selector).first
                
                element.wait_for(state='visible', timeout=8000)
                element.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                element.click(timeout=10000)
                page.wait_for_timeout(2000)
                
                # Wait for modal with multiple strategies
                try:
                    page.wait_for_selector("//h2[contains(text(), 'Data Center Pricing')]", timeout=15000)
                    explore_clicked = True
                    break
                except:
                    try:
                        page.wait_for_selector("//h2[contains(., 'Data Center Pricing')]", timeout=5000)
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
            # Last resort: try to find any link with "pricing" and "tier" keywords
            try:
                all_links = page.locator("a").all()
                for link in all_links:
                    try:
                        link_text = link.text_content()
                        if link_text and ('pricing' in link_text.lower() and ('tier' in link_text.lower() or 'user' in link_text.lower())):
                            link.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                            link.click()
                            page.wait_for_timeout(2000)
                            try:
                                page.wait_for_selector("div[role='dialog'], div[class*='modal']", timeout=5000)
                                explore_clicked = True
                                break
                            except:
                                continue
                    except:
                        continue
            except:
                pass
        
        if not explore_clicked:
            result['error'] = 'Could not find Explore pricing link'
            if context:
                context.close()
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            return result
        
        # Step 6: Find target tier in modal - ENHANCED
        try:
            page.wait_for_timeout(1500)
            
            # Scroll modal to top
            try:
                modal = page.locator("//div[contains(@class, 'modal')], //div[@role='dialog']").first
                modal.evaluate("element => element.scrollTop = 0")
                page.wait_for_timeout(1000)
            except:
                pass
            
            # Search for target tier with multiple patterns
            patterns = [
                f"Up to {target_tier} users",
                f"Up to {int(target_tier):,} users",  # With comma: "1,000"
                f"{target_tier} users",
                f"{int(target_tier):,} users",
            ]
            
            for pattern in patterns:
                row_selectors = [
                    f"//div[contains(@class, 'modal')]//tr[contains(., '{pattern}')]",
                    f"//div[@role='dialog']//tr[contains(., '{pattern}')]",
                    f"//tr[contains(., '{pattern}')]",
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
                                result['price_raw'] = price
                                result['price_usd'] = extract_usd_number(price)
                                result['status'] = 'success'
                                if context:
                                    context.close()
                                if browser:
                                    browser.close()
                                if playwright:
                                    playwright.stop()
                                return result
                    except:
                        continue
            
            # Fallback: search all rows
            try:
                all_rows = page.locator("//div[contains(@class, 'modal')]//tr, //div[@role='dialog']//tr").all()
                for r in all_rows:
                    try:
                        text = r.text_content()
                        if target_tier in text and 'users' in text:
                            r.scroll_into_view_if_needed()
                            page.wait_for_timeout(300)
                            cells = r.locator("td")
                            if cells.count() >= 2:
                                price = cells.nth(1).text_content().strip()
                                result['price_raw'] = price
                                result['price_usd'] = extract_usd_number(price)
                                result['status'] = 'success'
                                if context:
                                    context.close()
                                if browser:
                                    browser.close()
                                if playwright:
                                    playwright.stop()
                                return result
                    except:
                        continue
            except Exception as e:
                pass
            
            result['error'] = f'Could not find "Up to {target_tier} users" in modal'
        except Exception as e:
            result['error'] = f'Modal extraction: {str(e)[:80]}'
        
        # Cleanup
        if context:
            context.close()
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        
    except Exception as e:
        result['error'] = str(e)[:100]
        # Ensure cleanup on error
        try:
            if context:
                context.close()
        except:
            pass
        try:
            if browser:
                browser.close()
        except:
            pass
        try:
            if playwright:
                playwright.stop()
        except:
            pass
    
    return result

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'Atlassian Marketplace Pricing API',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/price', methods=['GET', 'POST'])
def get_price():
    """
    Get pricing for a plugin.
    
    GET /price?plugin_id=com.onresolve.jira.groovy.groovyrunner&tier=10000
    POST /price
    {
        "plugin_id": "com.onresolve.jira.groovy.groovyrunner",
        "tier": "10000"
    }
    """
    try:
        # Support both GET and POST
        if request.method == 'GET':
            plugin_id = request.args.get('plugin_id')
            tier = request.args.get('tier')
        else:
            data = request.get_json() or {}
            plugin_id = data.get('plugin_id')
            tier = data.get('tier')
        
        # Validate inputs
        if not plugin_id:
            return jsonify({
                'status': 'error',
                'error': 'plugin_id is required',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        if not tier:
            return jsonify({
                'status': 'error',
                'error': 'tier is required',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        # Normalize tier
        normalized_tier = normalize_tier(tier)
        if not normalized_tier:
            return jsonify({
                'status': 'error',
                'error': f'Invalid tier format: {tier}',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        # Scrape price (creates new browser per request - thread-safe)
        result = scrape_plugin_price(plugin_id, normalized_tier)
        
        # Format response
        response = {
            'plugin_id': result['plugin_id'],
            'user_tier': result['user_tier'],
            'price_usd': result['price_usd'],
            'price_raw': result['price_raw'],
            'status': result['status'],
            'timestamp': result['timestamp']
        }
        
        if result['error']:
            response['error'] = result['error']
            return jsonify(response), 500 if result['status'] == 'failed' else 200
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/price/batch', methods=['POST'])
def get_price_batch():
    """
    Get pricing for multiple plugins.
    
    POST /price/batch
    {
        "plugins": [
            {"plugin_id": "com.onresolve.jira.groovy.groovyrunner", "tier": "10000"},
            {"plugin_id": "com.valiantys.jira.plugins.SQLFeed", "tier": "5000"}
        ]
    }
    """
    try:
        data = request.get_json() or {}
        plugins = data.get('plugins', [])
        
        if not plugins or not isinstance(plugins, list):
            return jsonify({
                'status': 'error',
                'error': 'plugins array is required',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }), 400
        
        results = []
        for plugin_req in plugins:
            plugin_id = plugin_req.get('plugin_id')
            tier = plugin_req.get('tier')
            
            if not plugin_id or not tier:
                results.append({
                    'plugin_id': plugin_id or 'unknown',
                    'status': 'error',
                    'error': 'plugin_id and tier are required'
                })
                continue
            
            normalized_tier = normalize_tier(tier)
            if not normalized_tier:
                results.append({
                    'plugin_id': plugin_id,
                    'status': 'error',
                    'error': f'Invalid tier format: {tier}'
                })
                continue
            
            result = scrape_plugin_price(plugin_id, normalized_tier)
            results.append({
                'plugin_id': result['plugin_id'],
                'user_tier': result['user_tier'],
                'price_usd': result['price_usd'],
                'price_raw': result['price_raw'],
                'status': result['status'],
                'error': result.get('error'),
                'timestamp': result['timestamp']
            })
        
        return jsonify({
            'status': 'completed',
            'results': results,
            'total': len(results),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

if __name__ == '__main__':
    # Run on all interfaces, port 5000
    # threaded=True allows concurrent requests, each gets its own browser instance
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
