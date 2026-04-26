#!/usr/bin/env python3
"""
Web Navigator — Autonomous Playwright-based web agent.

Uses Playwright for headless browsing and the local VLM (via vision_brain.py)
for visual reasoning about page contents. Falls back to DOM-based heuristics
when the VLM is unavailable.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

VISION_BRAIN = Path(os.path.dirname(__file__)) / "vision_brain.py"
SCREENSHOT_DIR = Path(os.path.expanduser("~/.cache/ai-distro/screenshots"))


def vlm_reason(screenshot_path, prompt):
    """Use the VLM to reason about a webpage screenshot."""
    try:
        result = subprocess.run(
            [sys.executable, str(VISION_BRAIN), str(screenshot_path), prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return None


def run_task(url, goal):
    """Navigate to a URL and attempt to achieve the stated goal."""
    from playwright.sync_api import sync_playwright

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    result = {"status": "error", "message": "Task not started"}

    print(f"Web Navigator: {url} → {goal}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AI-Distro/1.0"
            )
            page = context.new_page()

            # Navigate
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)

            # Screenshot for VLM analysis
            ss_path = SCREENSHOT_DIR / "web-task-initial.png"
            page.screenshot(path=str(ss_path))

            # Ask VLM what we're looking at
            vlm_analysis = vlm_reason(
                ss_path,
                f"I'm looking at a webpage at {url}. My goal is: {goal}. "
                "What elements do you see? What should I click or fill in?"
            )

            # DOM-based action execution
            goal_lower = goal.lower()

            if "search" in goal_lower:
                # Find a search input
                search_input = (
                    page.query_selector('input[type="search"]')
                    or page.query_selector('input[name="q"]')
                    or page.query_selector('input[placeholder*="Search" i]')
                    or page.query_selector('input[type="text"]')
                )
                if search_input:
                    # Extract what to search for from the goal
                    search_terms = goal_lower.replace("search for", "").replace("search", "").strip()
                    search_input.fill(search_terms or goal)
                    page.keyboard.press("Enter")
                    time.sleep(3)

            elif any(kw in goal_lower for kw in ["sign up", "register", "create account"]):
                signup_btn = (
                    page.query_selector('a:has-text("Sign up")')
                    or page.query_selector('button:has-text("Sign up")')
                    or page.query_selector('a:has-text("Register")')
                    or page.query_selector('a:has-text("Create")')
                )
                if signup_btn:
                    signup_btn.click()
                    time.sleep(3)

            elif any(kw in goal_lower for kw in ["login", "sign in", "log in"]):
                login_btn = (
                    page.query_selector('a:has-text("Login")')
                    or page.query_selector('a:has-text("Sign in")')
                    or page.query_selector('button:has-text("Login")')
                )
                if login_btn:
                    login_btn.click()
                    time.sleep(3)

            elif "click" in goal_lower:
                # "click the X button" → find button by text
                target = goal_lower.split("click")[-1].strip().strip("'\"")
                btn = page.query_selector(f'button:has-text("{target}")')
                if not btn:
                    btn = page.query_selector(f'a:has-text("{target}")')
                if btn:
                    btn.click()
                    time.sleep(3)

            elif "read" in goal_lower or "extract" in goal_lower or "get" in goal_lower:
                # Read page content
                content = page.inner_text("body")[:3000]
                result = {
                    "status": "ok",
                    "message": f"Page content extracted ({len(content)} chars)",
                    "data": {
                        "url": page.url,
                        "title": page.title(),
                        "content": content
                    }
                }
                browser.close()
                return result

            # Final screenshot
            final_ss = SCREENSHOT_DIR / "web-task-final.png"
            page.screenshot(path=str(final_ss))

            # Final VLM analysis
            final_analysis = vlm_reason(
                final_ss,
                f"I tried to: {goal}. What happened? Was the action successful?"
            )

            page_title = page.title()
            final_url = page.url

            msg_parts = [f"Navigated to: {final_url}"]
            if page_title:
                msg_parts.append(f"Page: {page_title}")
            if vlm_analysis:
                msg_parts.append(f"Analysis: {vlm_analysis}")
            elif final_analysis:
                msg_parts.append(f"Result: {final_analysis}")

            result = {
                "status": "ok",
                "url": final_url,
                "title": page_title,
                "message": " | ".join(msg_parts),
                "vlm_available": vlm_analysis is not None
            }

            browser.close()

    except ImportError:
        result = {
            "status": "error",
            "message": "Playwright not installed. Run: pip install playwright && playwright install chromium"
        }
    except Exception as e:
        result = {"status": "error", "message": f"Browser task failed: {e}"}

    return result


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "status": "error",
            "message": "Usage: web_navigator.py <url> <goal>"
        }))
        return

    url = sys.argv[1]
    goal = " ".join(sys.argv[2:])

    task_result = run_task(url, goal)
    print(json.dumps(task_result))


if __name__ == "__main__":
    main()
