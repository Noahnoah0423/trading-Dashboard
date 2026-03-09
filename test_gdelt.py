import requests
import json
import urllib.parse
from datetime import datetime, timedelta

def get_gdelt_news(keywords=["Economy", "Interest Rate", "Crisis"], max_results=20):
    """
    Query the GDELT 2.0 DOC API for recent news containing specific keywords.
    """
    # GDELT 2.0 DOC API endpoint
    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    # Constructing query
    query_str = " OR ".join(f'"{kw}"' for kw in keywords)
    query_str += ' sourcelang:eng'
    
    params = {
        "query": query_str,
        "mode": "artlist",
        "maxrecords": max_results,
        "format": "json",
    }
    
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        articles = data.get("articles", [])
        
        # Filtering and structuring the results
        results = []
        seen_urls = set()
        
        for art in articles:
            url = art.get("url")
            if url in seen_urls:
                continue
                
            seen_urls.add(url)
            
            # GDELT provides 'tone' occasionally in other modes or can be parsed
            # Not natively provided in 'artlist' mode out of the box unless Tone mode is used
            # But let's grab what we can.
            results.append({
                "title": art.get("title", "No Title"),
                "url": url,
                "domain": art.get("domain", "Unknown"),
                "seendate": art.get("seendate")
            })
            
        return results

    except Exception as e:
        print(f"Error fetching GDELT data: {e}")
        return []

if __name__ == "__main__":
    news = get_gdelt_news()
    print(f"Fetched {len(news)} news articles.")
    if news:
        print(json.dumps(news[:2], indent=2))
