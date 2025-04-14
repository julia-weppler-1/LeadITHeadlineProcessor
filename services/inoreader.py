import streamlit as st
import requests
import time
import urllib.parse
from utils.read_json import parse_inoreader_feed
from newspaper import Article
import re
import urllib.parse
from playwright.async_api import async_playwright
import logging
import asyncio
import os
import subprocess
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def ensure_playwright_browsers():
    # Define the expected path to the Chromium executable.
    chrome_path = os.path.expanduser("~/.cache/ms-playwright/chromium-1112/chrome-linux/chrome")
    if not os.path.exists(chrome_path):
        logger.info("Chromium executable not found at %s. Installing...", chrome_path)
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["playwright", "install", "chromium"],
                check=True
            )
            logger.info("Browser installation completed.")
        except Exception as e:
            logger.error("Error installing browsers via playwright install: %s", e)
            raise

async def resolve_with_playwright_async(url):
    logger.info("Starting resolve_with_playwright_async for URL: %s", url)
    # Ensure the required browsers are installed before launching.
    await ensure_playwright_browsers()
    
    async with async_playwright() as p:
        logger.info("Creating browser")
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        logger.info("Creating page")
        page = await browser.new_page()

        async def block_resource(route, request):
            if request.resource_type in ["image", "stylesheet", "font"]:
                await route.abort()
            else:
                await route.continue_()
        await page.route("**/*", block_resource)

        try:
            logger.info("Navigating to URL: %s", url)
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(1000)
            logger.info("Navigation complete. Current page URL: %s", page.url)
        except Exception as e:
            logger.error("Error during page.goto: %s", e)
        final_url = page.url
        await browser.close()
        return final_url

def resolve_with_playwright(url):
    """
    Synchronously run the async resolve_with_playwright_async function.
    Uses WindowsProactorEventLoopPolicy on Windows if needed.
    """
    try:
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        result = asyncio.run(resolve_with_playwright_async(url))
        return result
    except Exception as e:
        logger.error("Error running async Playwright: %s", e)
        return None

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