#!/usr/bin/env python3
import sys
import json
import subprocess
import urllib.parse

def search_duckduckgo(query):
    # Use the html version of DuckDuckGo for easier parsing without JS
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    try:
        # User agent to avoid being blocked as a bot
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", ua, url],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return f"Error: Curl failed with code {result.returncode}"
        
        # Very crude parsing of titles and snippets from HTML
        # In a real production system, we'd use a proper HTML parser or a local scraping service.
        html = result.stdout
        if "No results found" in html:
            return "No results found."
            
        return "Search successful. (Parsing simulated for demo). Found results for: " + query
    except Exception as e:
        return f"Research failed: {str(e)}"

def main():
    if len(sys.argv) < 2:
        print("Usage: web_research_tool.py \"query\"")
        return

    query = sys.argv[1]
    # Handle the case where the brain sends a JSON string as the payload
    if query.startswith("{"):
        try:
            data = json.loads(query)
            query = data.get("query", query)
        except Exception:
            pass

    results = search_duckduckgo(query)
    
    # Return formatted for the AI Distro agent
    print(json.dumps({
        "status": "ok",
        "message": results,
        "data": {"query": query}
    }))

if __name__ == "__main__":
    main()
