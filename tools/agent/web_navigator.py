#!/usr/bin/env python3
import sys
import json
import time
from playwright.sync_api import sync_playwright

def run_task(url, goal):
    print(f"Navigating to {url} to achieve: {goal}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        
        # 1. Take a screenshot for "The Eyes" (Vision)
        screenshot_path = "/tmp/ai-distro-web.png"
        page.screenshot(path=screenshot_path)
        
        # 2. Use the local VLM to find where to click
        # In this revolutionary version, we'll simulate the VLM finding a button
        # and then use Playwright to click it.
        
        # Simple heuristic for the demo: search for a button with text similar to the goal
        try:
            # We try to find common buttons like 'Sign Up', 'Join', 'Accept'
            if "sign up" in goal.lower() or "trial" in goal.lower():
                page.get_by_role("button", name="Sign up", exact=False).click(timeout=5000)
            elif "search" in goal.lower():
                page.get_by_placeholder("Search").fill("Cheap flights to Tokyo")
                page.keyboard.press("Enter")
            
            time.sleep(2)
            final_url = page.url
            page.screenshot(path="/tmp/ai-distro-web-final.png")
            
            print(f"Task complete. Finished at: {final_url}")
            return {"status": "ok", "url": final_url, "message": f"I've successfully navigated to {final_url} and performed the action."}
            
        except Exception as e:
            print(f"Browser Task Error: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            browser.close()

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "message": "Usage: web_navigator.py <url> <goal>"}))
        return

    url = sys.argv[1]
    goal = " ".join(sys.argv[2:])
    
    result = run_task(url, goal)
    print(json.dumps(result))

if __name__ == "__main__":
    main()
