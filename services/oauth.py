from urllib.parse import urlencode
import streamlit as st
import requests

def get_inoreader_auth_url():
    params = {
        "client_id": st.secrets["oauth_client_id"],
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "response_type": "code",
        "scope": st.secrets["SCOPE"],
        "state": st.secrets["inoreader_key"]
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
