import msal
import webbrowser
import streamlit as st
import requests
import logging
CLIENT_ID = st.secrets["od_client_id"]
CLIENT_SECRET = st.secrets["od_client_secret"]
AUTHORITY = st.secrets["od_authority"]
REDIRECT_URI = st.secrets["od_redirect_uri"]
SCOPES = [s.strip() for s in st.secrets["od_scopes"].split(",")]
def get_authorization_url():
    print("CLIENT_ID:", CLIENT_ID)
    print("AUTHORITY:", AUTHORITY)
    print("REDIRECT_URI:", REDIRECT_URI)
    print("SCOPES:", SCOPES)  # Should be a list of three scopes
    
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY
    )
    auth_url = app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)
    print("Authorization URL:", auth_url)
    return auth_url

def exchange_code_for_token(auth_code):
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY
    )
    result = app.acquire_token_by_authorization_code(auth_code, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    return result

def get_onedrive_access_token():
    """
    Checks if the OneDrive access token is already in session state.
    If not, forces the user to sign in by redirecting them to Microsoft.
    This function should be called at app startup.
    """
    import streamlit as st
    # Check if we already have a token.
    if "onedrive_token" in st.session_state and st.session_state["onedrive_token"]:
        return st.session_state["onedrive_token"]
    
    # Check if a "code" is in the URL (after Microsoft redirects back)
    query_params = st.experimental_get_query_params()
    if "code" in query_params:
        auth_code = query_params["code"][0]
        token_response = exchange_code_for_token(auth_code)
        if token_response and "access_token" in token_response:
            st.session_state["onedrive_token"] = token_response["access_token"]
            return token_response["access_token"]
        else:
            st.error("Error obtaining OneDrive token.")
            return None
    else:
        # No auth code available; force sign in.
        auth_url = get_authorization_url()
        st.error(f"You must sign in to OneDrive to continue. [Click here to sign in]({auth_url})")
        # Optionally, open the URL in the user's default browser
        webbrowser.open(auth_url)
        st.stop()  # Halt further execution until the user has signed in

def upload_file_to_onedrive(access_token, file_path, onedrive_filename, folder_path="personal/julia_weppler_sei_org/Documents/Testing"):
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
def send_results_to_drive():
    """
    Sends a POST request to Microsoft Graph to grant write access to the fixed OneDrive folder.
    (Extend this function to upload your results file as needed.)
    """
    # Microsoft Graph endpoint for updating permissions on the OneDrive folder
    url = "https://graph.microsoft.com/v1.0/drives/b!RuqInJIRV0Cd7fS7BUA0Eza0zwh4svtPoFLjiO6o8niqVQe2V9XYQrtDPem8Sf-U/items/01WQJ7T6XBC2W4SCZ64JHLUH76AMG2NNNV/permissions"
    
    # Payload for the Graph API request
    payload = {
        "roles": ["write"],
        "grantedTo": {
            "application": {
                "id": "4f103ef8-83fb-4fa1-a9d1-e93b00fadf7e"
            }
        }
    }
    
    # Headers with a valid access token (replace YOUR_ACCESS_TOKEN with your token)
    headers = {
        "Authorization": "Bearer YOUR_ACCESS_TOKEN",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code in (200, 201):
        print("Results sent to OneDrive successfully!")
    else:
        print("Error sending results to OneDrive:", response.status_code, response.text)
