import streamlit as st
import requests
import time
import urllib.parse
from utils.read_json import parse_inoreader_feed
from newspaper import Article
import re
import urllib.parse
from bs4 import BeautifulSoup
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
    params = {"ot": one_week_ago}
    
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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")  # waiting for network idle can catch JS redirects
        # Optionally wait a few extra seconds if needed:
        # page.wait_for_timeout(2000)
        final_url = page.url
        browser.close()
        return final_url
def fetch_full_article_text(row):
    # Try to get URL from summary content first
    ino_url = row.get("url")
    real_url = resolve_with_playwright(ino_url)
    # Fallback to provided URL if summary doesn't help
    if not real_url:
        real_url = row.get("url", "")

    print(f"Extracted final URL: {real_url}")
    try:
        article = Article(real_url)
        print(article)
        article.download()
        article.parse()
        print(article.text)
        return article.text
    except Exception as e:
        print(f"Error fetching article from {real_url}: {e}")
        return ""