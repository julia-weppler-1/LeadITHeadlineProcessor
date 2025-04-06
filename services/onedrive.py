# services/onedrive.py
import msal
import webbrowser
import streamlit as st
import requests

CLIENT_ID = st.secrets["od_client_id"]
AUTHORITY = st.secrets["od_authority"]
REDIRECT_URI = st.secrets["od_redirect_uri"]
SCOPES = [st.secrets["od_scopes"]]

def get_authorization_url():
    """
    Returns the Microsoft OAuth authorization URL.
    """
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    auth_url = app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)
    return auth_url

def exchange_code_for_token(auth_code):
    """
    Exchanges the provided authorization code for an access token.
    Returns the token response.
    """
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    result = app.acquire_token_by_authorization_code(auth_code, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    return result

def get_onedrive_access_token():
    """
    Initiates the OAuth flow for OneDrive.
    Displays the sign-in URL and a text input for the auth code.
    Stores the token in st.session_state.
    """
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    auth_url = app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)
    st.markdown(f"[Click here to sign in with Microsoft]({auth_url})", unsafe_allow_html=True)
    
    # Ask the user to paste the authorization code.
    auth_code = st.text_input("Enter the authorization code from Microsoft:", key="onedrive_auth_code")
    if auth_code:
        result = app.acquire_token_by_authorization_code(auth_code, scopes=SCOPES, redirect_uri=REDIRECT_URI)
        if "access_token" in result:
            st.session_state["onedrive_token"] = result["access_token"]
            st.success("OneDrive Authorized!")
            return result["access_token"]
        else:
            st.error(f"Error obtaining token: {result.get('error')} {result.get('error_description')}")
            return None
    return None

def upload_file_to_onedrive(access_token, file_path, onedrive_filename, folder_path="personal/julia_weppler_sei_org/Documents/Testing"):
    """
    Uploads the file to the specified folder on OneDrive.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    with open(file_path, "rb") as f:
        file_content = f.read()
    
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}/{onedrive_filename}:/content"
    response = requests.put(upload_url, headers=headers, data=file_content)
    
    if response.status_code in (200, 201):
        st.success("File uploaded successfully to OneDrive!")
        return response.json()
    else:
        st.error(f"Error uploading file: {response.status_code} {response.text}")
        return None
