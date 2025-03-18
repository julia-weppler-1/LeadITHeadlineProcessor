import streamlit as st
import requests

def fetch_inoreader_articles():
    if "inoreader_access_token" not in st.session_state:
        st.error("You need to log in to Inoreader first.")
        return []

    headers = {"Authorization": f"Bearer {st.session_state['inoreader_access_token']}"}
    response = requests.get("https://www.inoreader.com/reader/api/0/stream/contents", headers=headers)

    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"Failed to fetch Inoreader articles: {response.text}")
        return []
