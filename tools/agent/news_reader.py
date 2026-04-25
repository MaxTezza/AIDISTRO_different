#!/usr/bin/env python3
import sys
import requests
import json
import xml.etree.ElementTree as ET

def get_news():
    url = "http://feeds.bbci.co.uk/news/world/rss.xml"
    try:
        resp = requests.get(url, timeout=10)
        root = ET.fromstring(resp.content)
        headlines = []
        for item in root.findall('.//item')[:5]: # Top 5
            headlines.append(item.find('title').text)
        
        if not headlines:
            return "I couldn't find any news headlines right now."
            
        msg = "Here are the top headlines: " + ". ".join(headlines)
        return msg
    except Exception as e:
        return f"I had trouble connecting to the news service: {e}"

def main():
    result = get_news()
    print(json.dumps({"status": "ok", "message": result}))

if __name__ == "__main__":
    main()
