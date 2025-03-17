import json
import pandas as pd
import os

def parse_json_feed(json_path):
    """
    Parses a JSON feed file and extracts article information into a DataFrame.
    
    Args:
        json_path (str): Path to the JSON feed file.
    
    Returns:
        pd.DataFrame: DataFrame containing extracted article information (title, url, content_html, date_published, tags, id).
    """
    if not os.path.exists(json_path):
        print(f"Error: File '{json_path}' not found.")
        return pd.DataFrame()

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            content = file.read().strip()
            if not content:
                print(f"Error: JSON file '{json_path}' is empty.")
                return pd.DataFrame()
            data = json.loads(content)

        # Ensure "items" is a list
        if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
            print(f"Error: Invalid JSON structure in '{json_path}'. Expected a dictionary with a list under 'items'.")
            return pd.DataFrame()

        # Extract relevant fields
        articles = []
        for item in data["items"]:
            if not isinstance(item, dict):
                print("Warning: Skipping invalid item (not a dictionary).")
                continue

            article_info = {
                "title": item.get("title", "Unknown"),
                "url": item.get("url", "Unknown"),
                "content_html": item.get("content_html", "Unknown"),
                "date_published": item.get("date_published", "Unknown"),
                "tags": ", ".join(item.get("tags", [])) if isinstance(item.get("tags"), list) else "Unknown",
                "id": item.get("id", "Unknown")
            }
            articles.append(article_info)

        return pd.DataFrame(articles)

    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON file '{json_path}'. Ensure it's properly formatted.")
    except Exception as e:
        print(f"Unexpected error while parsing JSON: {e}")

    return pd.DataFrame()
