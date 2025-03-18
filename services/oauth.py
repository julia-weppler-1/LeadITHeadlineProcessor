from urllib.parse import urlencode
import streamlit as st
import requests
import secrets
import time

def get_inoreader_auth_url():
    state = secrets.token_urlsafe(16)  # Generates a random 16-character string

    # Store it in session state to validate later (optional but recommended)
    st.session_state["inoreader_state"] = state
    params = {
        "client_id": st.secrets["oauth_client_id"],
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "response_type": "code",
        "scope": st.secrets["SCOPE"],
        "state": state
    }
    print("PARAMS:", params)
    return f"{st.secrets['AUTHORIZATION_URL']}?{urlencode(params)}"


def exchange_code_for_token():
    token_url = st.secrets["TOKEN_URL"]
    query_params = st.experimental_get_query_params()
    code = query_params.get("code", [None])[0]

    if not code:
        st.error("Authorization failed: No code received.")
        return

    data = {
        "code": code,
        "client_id": st.secrets["oauth_client_id"],
        "client_secret": st.secrets["inoreader_key"],
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=data)

    if response.status_code == 200:
        access_token = response.json().get("access_token")
        st.session_state["access_token"] = access_token
        st.success("Connected to Inoreader! Redirecting to main page...")
        
        # Wait for 2 seconds before redirecting
        time.sleep(2)

        # Remove code/state from URL and redirect to main page
        st.experimental_set_query_params(connected="true")
        st.experimental_rerun()
    else:
        st.error(f"Failed to exchange code for token: {response.json()}")


def get_access_token(code):
    TOKEN_URL = st.secrets["TOKEN_URL"]
    data = {
        "code": code,
        "client_id": st.secrets["oauth_client_id"],
        "client_secret": st.secrets["inoreader_key"],
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "grant_type": "authorization_code"
    }

    # Make the POST request to get the access token
    response = requests.post(TOKEN_URL, data=data)
    
    if response.status_code == 200:
        access_token = response.json().get("access_token")
        st.session_state["access_token"] = access_token
        st.success("Successfully authorized!")
        # You can now use the access token to make API requests
    else:
        st.error(f"Failed to exchange code for token: {response.json()}")