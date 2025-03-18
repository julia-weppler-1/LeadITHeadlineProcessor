from urllib.parse import urlencode
import streamlit as st
import requests
import secrets

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

def exchange_code_for_token(code):
    # Prepare the data for the POST request to exchange the code for a token
    token_url = "https://www.inoreader.com/oauth2/token"  # Inoreader token endpoint
    data = {
        "code": code,
        "client_id": st.secrets["oauth_client_id"],
        "client_secret": st.secrets["HM8gzAfUuLiNQZYD2w6ibXjSSD3nYuOQ"],
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "grant_type": "authorization_code",
    }

    # Send the request to Inoreader to exchange the code for an access token
    response = requests.post(token_url, data=data)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response and get the access token
        token_data = response.json()
        access_token = token_data.get("access_token")
        if access_token:
            st.session_state["inoreader_access_token"] = access_token
            st.success("Successfully authorized! You can now use the tool.")
            return access_token
        else:
            st.error("Access token not found in response.")
            return None
    else:
        st.error(f"Error exchanging code for token: {response.text}")
        return None
def get_access_token(code):
    TOKEN_URL = st.secrets["TOKEN_URL"]
    data = {
        "code": code,
        "client_id": st.secrets["INOREADER_CLIENT_ID"],
        "client_secret": st.secrets["INOREADER_CLIENT_SECRET"],
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