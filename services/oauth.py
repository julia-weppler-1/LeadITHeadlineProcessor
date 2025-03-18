# In services/oauth.py
import secrets
import urllib.parse
import streamlit as st
import requests

CLIENT_ID = st.secrets["oauth_client_id"]
CLIENT_SECRET = st.secrets["inoreader_key"]
REDIRECT_URI = "http://localhost:8501/"
AUTHORIZATION_URL = "https://www.inoreader.com/oauth2/auth"
TOKEN_URL = "https://www.inoreader.com/oauth2/token"
SCOPE = "read"

def get_authorization_url():
    state = st.session_state.get("oauth_state")
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "state": state,
    }
    return f"{AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(auth_code):
    data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(TOKEN_URL, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error exchanging code for token: {response.text}")
        return None

def fetch_inoreader_data():
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    response = requests.get("https://www.inoreader.com/reader/api/0/user-info", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching data: {response.text}")
        return None
