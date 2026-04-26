#!/usr/bin/env python3
"""
Web Research Tool — Performs web searches via DuckDuckGo's HTML interface.

Fetches the lightweight HTML version of DuckDuckGo, parses result titles
and snippets from the response, and returns structured search results.

Usage:
  python3 web_research_tool.py "query string"
  python3 web_research_tool.py '{"query": "something"}'
"""
import json
import re
import subprocess
import sys
import urllib.parse


def extract_results(html):
    """Parse search result titles and snippets from DuckDuckGo HTML."""
    results = []

    # DuckDuckGo HTML wraps each result in <div class="result...">
    # Each result has:
    #   <a class="result__a" href="...">Title</a>
    #   <a class="result__snippet" ...>Snippet text</a>
    # We use regex since we can't depend on external HTML parsers.

    # Extract result blocks
    blocks = re.findall(
        r'<a\s+[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        r'.*?'
        r'<a\s+[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        html,
        re.DOTALL | re.IGNORECASE,
    )

    for href, raw_title, raw_snippet in blocks[:8]:
        title = re.sub(r"<[^>]+>", "", raw_title).strip()
        snippet = re.sub(r"<[^>]+>", "", raw_snippet).strip()
        snippet = re.sub(r"\s+", " ", snippet)

        # DuckDuckGo HTML wraps outgoing links in a redirect
        url = href
        if "uddg=" in url:
            match = re.search(r"uddg=([^&]+)", url)
            if match:
                url = urllib.parse.unquote(match.group(1))

        if title:
            results.append({
                "title": title,
                "snippet": snippet[:300],
                "url": url,
            })

    if not results:
        # Fallback: try to grab any <a> with result text
        links = re.findall(
            r'<a\s+[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        for href, raw_title in links[:5]:
            title = re.sub(r"<[^>]+>", "", raw_title).strip()
            if title and len(title) > 5 and "duckduckgo" not in href.lower():
                results.append({
                    "title": title,
                    "snippet": "",
                    "url": href,
                })

    return results


def search_duckduckgo(query):
    """Search DuckDuckGo's HTML-only endpoint and parse results."""
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

    ua = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-A", ua, url],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return None, f"curl failed with code {result.returncode}"

        html = result.stdout
        if not html or len(html) < 100:
            return None, "Empty response from search engine"

        results = extract_results(html)
        if not results:
            # Check if DDG returned a "no results" page
            if "No more results" in html or "no results" in html.lower():
                return [], None
            return [], "Could not parse results from response"

        return results, None

    except subprocess.TimeoutExpired:
        return None, "Search request timed out"
    except FileNotFoundError:
        return None, "curl is not installed"
    except Exception as e:
        return None, f"Search failed: {e}"


def format_results(results, query):
    """Format results into a human-readable summary."""
    if not results:
        return f"No results found for '{query}'."

    lines = [f"Search results for '{query}':"]
    for i, r in enumerate(results[:5], 1):
        lines.append(f"\n{i}. {r['title']}")
        if r.get("snippet"):
            lines.append(f"   {r['snippet']}")
        lines.append(f"   {r['url']}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Usage: web_research_tool.py \"query\""
        }))
        return

    query = sys.argv[1]
    # Handle JSON payload from the brain
    if query.startswith("{"):
        try:
            data = json.loads(query)
            query = data.get("query", query)
        except Exception:
            pass

    results, error = search_duckduckgo(query)

    if error and results is None:
        print(json.dumps({
            "status": "error",
            "message": error,
            "data": {"query": query}
        }))
        return

    summary = format_results(results or [], query)

    print(json.dumps({
        "status": "ok",
        "message": summary,
        "data": {
            "query": query,
            "result_count": len(results or []),
            "results": results or [],
        }
    }))


if __name__ == "__main__":
    main()
