import streamlit as st
import requests
import time
import urllib.parse
from utils.read_json import parse_inoreader_feed
from newspaper import Article
import re
import urllib.parse
from playwright.sync_api import sync_playwright


def fetch_inoreader_articles(folder_name):
    if "access_token" not in st.session_state:
        st.error("You need to log in to Inoreader first.")
        return []

    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
    
    # Calculate the Unix timestamp for one week ago
    one_week_ago = int(time.time()) - 7 * 24 * 60 * 60
    
    # Build the stream ID by URL-encoding the folder (label) name
    stream_id = urllib.parse.quote(f"user/-/label/{folder_name}", safe='')
    url = f"https://www.inoreader.com/reader/api/0/stream/contents/{stream_id}"
    
    # Set parameters to filter for items published since one week ago
    params = {"n": 1}
    
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"Failed to fetch Inoreader articles: {response.text}")
        return []


def build_df_for_folder(folder_name):
    response = fetch_inoreader_articles(folder_name)
    df = parse_inoreader_feed(response)
    return(df)

def resolve_with_playwright(url):
    print("here", url)
    with sync_playwright() as p:
        print("creating browser")
        browser = p.chromium.launch(headless=True)
        print("creating page")
        page = browser.new_page()
        
        # Optionally block resources that aren't needed to speed up loading.
        def block_resource(route, request):
            if request.resource_type in ["image", "stylesheet", "font"]:
                return route.abort()
            return route.continue_()
        page.route("**/*", block_resource)
        
        try:
            # Use a faster waiting criterion and a shorter timeout.
            page.goto(url, wait_until="networkidle", timeout=15000)
            # Wait a bit for any possible redirect (adjust if necessary)
            page.wait_for_timeout(1000)
            print("went to page")
        except Exception as e:
            print(f"Error during page.goto: {e}")
            # Optionally, you could try a fallback here
        final_url = page.url
        browser.close()
        return final_url

def fetch_full_article_text(row):
    # Try to get URL from summary content first
    print("fetching article")
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