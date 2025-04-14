from utils.analysis import get_analyzer, get_task_types
from tempfile import NamedTemporaryFile
import base64
import json
import os
import pandas as pd
import streamlit as st
from services.onedrive import send_results_to_drive
from services import oauth
import logging
from services import inoreader
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from services.onedrive import get_authorization_url

def display_onedrive_login():
    """
    If the OneDrive token is missing, show a dedicated login page.
    This page includes a clear sign-in link (retrieved from Microsoft) that the user must click,
    and instructions telling them to sign in.
    """
    import streamlit as st
    from services.onedrive import get_authorization_url, exchange_code_for_token

    st.title("OneDrive Login Required")
    st.write("To continue, you must sign in to Microsoft and authorize the app to access your OneDrive.")

    # Check query parameters to see if we have a code (i.e. user returned from Microsoft)
    query_params = st.query_params
    print("hi")
    if "code" in query_params:
        auth_code = query_params["code"][0]
        st.write("Processing authorization code...")
        token_response = exchange_code_for_token(auth_code)
        st.write("Token response:", token_response)  # Debug: inspect the token response
        if token_response and "access_token" in token_response:
            st.session_state["onedrive_token"] = token_response["access_token"]
            st.success("OneDrive authorization complete!")
            st.experimental_set_query_params()  # Clear query parameters
        else:
            st.error("Error obtaining OneDrive token. Please try again.")
            st.stop()
    
    # If there’s still no token, show the sign‑in link.
    if "onedrive_token" not in st.session_state or not st.session_state["onedrive_token"]:
        print("here")
        auth_url = get_authorization_url()
        st.markdown(f'[Sign in with Microsoft]({auth_url})', unsafe_allow_html=True)
        st.write("After signing in, come back to this page.")
        st.stop()  # Stop further processing until authentication is complete.



def load_header():
    logo_path = os.path.join(os.path.dirname(__file__), "public", "logo.png")
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()

    html_temp = f"""
    <div style="background-color:#00D29A;padding:10px;border-radius:10px;margin-bottom:20px;">
        <img src="data:image/png;base64,{encoded_string}" alt="logo" style="height:50px;width:auto;float:right;">
        <h2 style="color:white;text-align:center;">AI Headline Reader (beta)</h2>
        <h5 style="color:white;text-align:center;">This Tool allows users to analyze headlines in bulk using the Large Language Model ChatGPT.\n
Users can define specific queries to extract targeted information from any collection of JSON files or RSS apps.</h5>
        <br>
    </div>
    """
    st.markdown(html_temp, unsafe_allow_html=True)
def load_text():
    instructions = """
## How to use

Start by connecting the application to your Inoreader account. Once it has successfully connected, choose the folder you'd like to connect to. As soon as one is chosen and the articles are fetched, click "Run". It make take up to an hour to process all of the articles in your given folder for the past week. Please be patient. When the results are done, you can click the option to download your results. Please DO NOT refresh while your results are being loaded.
"""

    st.markdown(instructions)



def upload_file(temp_dir):
    # Track active tab in session state
    query_params = st.query_params 
    st.session_state["active_tab"] = "Connect to Inoreader"

    json = []  
    
    if st.session_state["active_tab"] == "Connect to Inoreader":
        st.subheader("Authorize Inoreader Access")
        query_params = st.query_params 
        stored_state = st.session_state.get("oauth_state")
        
        # Initialize target_folder if not already present.
        if "target_folder" not in st.session_state:
            st.session_state["target_folder"] = ""
        
        if "code" in query_params and "state" in query_params:
            returned_state = query_params["state"]
            if returned_state == stored_state:
                auth_code = query_params["code"]
                token = oauth.exchange_code_for_token(auth_code)
                if token:
                    st.session_state.access_token = token["access_token"]
                    st.session_state.refresh_token = token.get("refresh_token")
                    st.success("Successfully authenticated with Inoreader!")
                    
                    # Use a text input with its own key so its value is stored in a separate widget key.
                    
        else:
            st.session_state["run_disabled"] = True
            auth_url = oauth.get_authorization_url()
            st.markdown(f'<a href="{auth_url}">Authorize with Inoreader</a>', unsafe_allow_html=True)
            st.stop()
    folder_choice = st.selectbox(
        "Select Target Folder", 
        options=["LeadIT-Iron", "LeadIT-Steel", "LeadIT-Cement"],
        key="target_folder_input"
    )
    
    # Display a "Fetch Articles" button.
    if st.button("Fetch Articles", key="fetch_articles_button"):
        st.session_state["target_folder"] = folder_choice
        # Fetch articles using the chosen folder.
        articles = inoreader.fetch_inoreader_articles(folder_choice)
        st.session_state["json"] = articles
        st.session_state["selected_json"] = articles
        st.session_state["run_disabled"] = False
        st.session_state["inoreader_authenticated"] = True
        st.success(f"Fetched {len(articles)} articles from folder '{folder_choice}'.")




        


        



def input_main_query():
    st.session_state["main_query_input"] = "Extract any quote that addresses “{variable_name}” which we define as “{variable_description}”. "


def var_json_to_df(json_fname):
    var_info_path = os.path.join(os.path.dirname(__file__), "site_text", json_fname)
    with open(var_info_path, "r", encoding="utf-8") as file:
        sdg_var_specs = json.load(file)
        return pd.DataFrame(sdg_var_specs)


def input_data_specs():
    if "variables_df" not in st.session_state:
        st.session_state["variables_df"] = var_json_to_df("default_var_specs.json")
    # Instead of displaying an editable table, just store the DataFrame in session state.
    st.session_state["schema_table"] = st.session_state["variables_df"]
    



def process_table():
    df = st.session_state["schema_table"]
    df = df.fillna("")
    num_cols = df.shape[1]
    df.columns = ["variable_name", "variable_description", "context"][:num_cols]
    df["variable_name"] = df["variable_name"].replace("", pd.NA)
    df.dropna(subset=["variable_name"], inplace=True)
    df = df[df["variable_name"].notnull()]
    return {
        row["variable_name"]: {
            "variable_description": row["variable_description"],
            **({"context": row["context"]} if "context" in df.columns else {}),
        }
        for _, row in df.iterrows()
    }

def build_interface(tmp_dir):
    if "task_type" not in st.session_state:
        st.session_state["task_type"] = "Headline extraction"
    if "is_test_run" not in st.session_state:
        st.session_state["is_test_run"] = True
    load_text()
    upload_file(tmp_dir)
    # Call input_main_query unconditionally to populate section II.
    input_main_query()
    # If output_format_options isn’t set, initialize it.
    if "output_format_options" not in st.session_state:
        st.session_state["output_format_options"] = {
            "Sort by quotes; each quote will be one row": "quotes_sorted",
            "Simply return GPT responses for each variable": "quotes_gpt_resp",
            "Sort by quotes labelled with variable_name and subcategories": "quotes_sorted_and_labelled",
            "Return list of quotes per variable": "quotes_structured",
        }
    # If no JSON is set, default to "no_upload".
    if "json" not in st.session_state:
        st.session_state["json"] = "no_upload"
    if "schema_input_format" not in st.session_state:
        st.session_state["schema_input_format"] = "Manual Entry"
    if "output_format" not in st.session_state:
        st.session_state["output_format"] = list(st.session_state["output_format_options"].keys())[1]
    if "custom_output_fmt" not in st.session_state:
        st.session_state["custom_output_fmt"] = None
    if "output_detail_df" not in st.session_state:
        st.session_state["output_detail_df"] = None
    # Unconditionally call input_data_specs to populate section III.
    input_data_specs()

def get_user_inputs():
    json = st.session_state["json"]
    main_query = st.session_state["main_query_input"]
    variable_specs = process_table()
    task_type = st.session_state["task_type"]
    output_fmt = st.session_state["output_format_options"][
        st.session_state["output_format"]
    ]
    additional_info = None
    if task_type == "Headline extraction" and output_fmt == "quotes_sorted_and_labelled":
        additional_info = st.session_state["subcategories_df"]
    
    return get_analyzer(
        task_type, output_fmt, json, main_query, variable_specs, additional_info
    )


def display_output(xlsx_fname):
    with open(xlsx_fname, "rb") as f:
        binary_file = f.read()
        st.download_button(
            label="Download Results",
            data=binary_file,
            file_name="results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    # Add a button to send results to OneDrive.
    # if st.button("Send Results to OneDrive"):
    #     send_results_to_drive(xlsx_fname)


