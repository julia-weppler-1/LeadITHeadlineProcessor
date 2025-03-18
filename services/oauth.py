from urllib.parse import urlencode
import streamlit as st
def get_inoreader_auth_url():
    params = {
        "client_id": st.secrets["INOREADER_CLIENT_ID"],
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "response_type": "code",
        "scope": st.secrets["SCOPE"]
    }
    return f"{st.secrets['AUTHORIZATION_URL']}?{urlencode(params)}"