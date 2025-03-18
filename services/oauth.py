from urllib.parse import urlencode
import streamlit as st
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