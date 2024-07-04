import os
import json
import requests

BRAVE_URL = os.environ.get("BRAVE_URL")
BRAVE_AUTH = os.environ.get("BRAVE_AUTH")

def web_result_to_link_desc(result):
    pass

def search_top(query):
    return fetch_brave(query).get("web", {}).get("results",[])

def fetch_brave(query):
    if BRAVE_URL and BRAVE_AUTH:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_AUTH,
        }

        params = {
            "country": "us",
            "search_lang": "en",
            "count": "10",
            "safesearch": "off",
            "units": "imperial",
            "result_filter": "web",
            "spellcheck": "0",
            "summary": "1",
            "q": query
        }

        response = requests.get(f"{BRAVE_URL}/web/search", headers=headers, params=params)
        return json.loads(response.content)
    else:
        raise ValueError("BRAVE_URL and/or BRAVE_AUTH is not set")
