import streamlit as st
import requests
import time
import urllib.parse
from utils.read_json import parse_inoreader_feed
from newspaper import Article
import re
import urllib.parse
from playwright.async_api import async_playwright


def fetch_inoreader_articles(folder_name):
    """
    Fetch all articles from a given folder (label) that were published in the past week.
    This function uses pagination (via the continuation token) and query parameters:
      - n: max number of items per request (100)
      - r: order ("o" for oldest first so that we can use the ot parameter)
      - ot: start time (Unix timestamp) from which to return items
    """
    access_token = st.session_state["access_token"]
    if not access_token:
        return []
    
    # Compute the Unix timestamp for one week ago.
    one_week_ago = int(time.time()) - 7 * 24 * 60 * 60
    
    articles = []
    n = 5
    continuation = None
    
    # Build the stream URL.
    stream_id = urllib.parse.quote(f"user/-/label/{folder_name}", safe='')
    base_url = f"https://www.inoreader.com/reader/api/0/stream/contents/{stream_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Loop until no continuation token is returned.
    #while True:
        # Set parameters: using r="o" (oldest first) and ot with the start time.
    params = {
        "n": n,
        "r": "o",
        "ot": one_week_ago,
        "output": "json"  # explicitly request JSON, though this endpoint returns JSON by default.
    }
    if continuation:
        params["c"] = continuation
    
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
        json_data = response.json()
        items = json_data.get("items", [])
        # if not items:
        #     break
        articles.extend(items)
        
        continuation = json_data.get("continuation")
        # if not continuation:
        #     break
    # else:
    #     break
            
    return articles


def build_df_for_folder(folder_name):
    response = fetch_inoreader_articles(folder_name)
    df = parse_inoreader_feed(response)
    return(df)

async def resolve_with_playwright(url):
    print("here", url)
    with async_playwright() as p:
        print("creating browser")
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        print("creating page")
        page = await browser.new_page()
        
        # Optionally block resources that aren't needed to speed up loading.
        async def block_resource(route, request):
            if request.resource_type in ["image", "stylesheet", "font"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_resource)
        
        try:
            print("Navigating to url", url)
            # Use a faster waiting criterion and a shorter timeout.
            await page.goto(url, wait_until="networkidle", timeout=15000)
            # Wait a bit for any possible redirect (adjust if necessary)
            await page.wait_for_timeout(1000)
            print("went to page")
        except Exception as e:
            print(f"Error during page.goto: {e}")
            # Optionally, you could try a fallback here
        final_url = page.url
        await browser.close()
        return final_url

def fetch_full_article_text(row):
    real_url = row.get("url")
    #real_url = resolve_with_playwright(ino_url)
    # Fallback to provided URL if summary doesn't help
    if not real_url:
        real_url = row.get("url", "")

    print(f"Extracted final URL: {real_url}")
    try:
        article = Article(real_url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"Error fetching article from {real_url}: {e}")
        return ""