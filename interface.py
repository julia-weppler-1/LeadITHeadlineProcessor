from utils.analysis import get_analyzer, get_task_types
from tempfile import NamedTemporaryFile
import base64
import json
import os
import pandas as pd
import streamlit as st
import zipfile
from services import oauth
import logging
from services import inoreader
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
"""

    st.markdown(instructions)
    st.markdown("""## Submit your processing request""")

def upload_file(temp_dir):
    st.subheader("I. Choose Your Input Method")
    # Track active tab in session state
    query_params = st.query_params 
    if "state" in query_params:
        default_tab = "Connect to Inoreader"
    else:
        default_tab = "JSON File"

    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = default_tab

    active_tab_radio = st.radio(
        "Select analysis type:", 
        ["JSON File", "Connect to Inoreader"],
        index=["JSON File", "Connect to Inoreader"].index(st.session_state["active_tab"]),
        key="active_tab_radio",
        horizontal=True,
        help="""Select **JSON File** if using tool for the first time on a selection of downloaded news articles from an RSS app. 
        **Connect to Inoreader** may be run on an existing Inoreader stream."""
    )

    # Detect if the tab has changed
    if active_tab_radio != st.session_state["active_tab"]:
        # Clear any previous uploads when switching tabs
        st.session_state["json"] = []
        st.session_state["selected_json"] = []
        st.session_state["temp_zip_path"] = None
        st.session_state["run_disabled"] = True  # Prevent running with no files

    # Update the active_tab value in session state
    st.session_state["active_tab"] = active_tab_radio
    active_tab = active_tab_radio

    if active_tab != st.session_state["active_tab"]:
        # Clear any previous uploads when switching tabs
        st.session_state["json"] = []
        st.session_state["selected_json"] = []
        st.session_state["temp_zip_path"] = None
        st.session_state["run_disabled"] = True  

    st.session_state["active_tab"] = active_tab 

    json = []  
    if active_tab == "JSON File":
        uploaded_file = st.file_uploader(
            "Upload a **single JSON** file exported from your Inoreader feed (download folder as JSON)",
            type=["JSON"],
        )

        st.markdown(
            "*Please note: uploaded information will be processed by OpenAI and may be used to train further models. "
        )
        if uploaded_file is not None:
            file_name = uploaded_file.name

            if file_name.endswith(".json"):
                # Save the single uploaded JSON to a temporary location
                file_path = os.path.join(temp_dir, file_name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                json.append(file_path)

        if json:
            st.session_state["json"] = json
            st.success(f"Uploaded {len(json)} document(s) successfully!", icon="✅")

            if len(json) == 1:
                # Disable the subset checkbox if only one PDF is uploaded
                st.session_state["max_files"] = None
                st.session_state["file_select_label"] = "No need to select subset for analysis."
            st.session_state["selected_json"] = [json[0]]
            st.session_state["run_disabled"] = False  # Enable Run if only one PDF
        else:
            st.warning("Please upload a single JSON file.", icon="⚠️")
    elif active_tab == "Connect to Inoreader":
        st.subheader("Authorize Inoreader Access")
        query_params = st.query_params 
        stored_state = st.session_state.get("oauth_state")
        
        # Initialize target_folder if not already present.
        if "target_folder" not in st.session_state:
            st.session_state["target_folder"] = ""
        
        if "code" in query_params and "state" in query_params:
            returned_state = query_params["state"]
            if returned_state != stored_state:
                st.error("State parameter mismatch. Potential CSRF attack detected.")
            else:
                auth_code = query_params["code"]
                token = oauth.exchange_code_for_token(auth_code)
                if token:
                    st.session_state.access_token = token["access_token"]
                    st.session_state.refresh_token = token.get("refresh_token")
                    st.success("Successfully authenticated with Inoreader!")
                    
                    # Use a text input with its own key so its value is stored in a separate widget key.
                    folder_input = st.text_input(
                        "Target Folder", 
                        value=st.session_state["target_folder"], 
                        key="target_folder_input", 
                        help="Enter the target folder name from Inoreader (e.g., LeadIT-Iron)"
                    )
                    
                    # Use a button to trigger article fetching.
                    if st.button("Fetch Articles", key="fetch_articles_button"):
                        if folder_input.strip():
                            # Update the target folder in session state.
                            st.session_state["target_folder"] = folder_input.strip()
                            articles = inoreader.fetch_inoreader_articles(folder_input.strip())
                            st.session_state["json"] = articles
                            st.session_state["selected_json"] = articles
                            st.session_state["run_disabled"] = False
                            st.session_state["inoreader_authenticated"] = True
                            st.success(f"Fetched {len(articles)} articles from folder '{folder_input.strip()}'.")
                            # Optionally, you may delay or remove the experimental rerun while debugging:
                            st.experimental_rerun()
                        else:
                            st.error("Please enter a valid target folder.")
                else:
                    st.error("Failed to exchange token.")
        else:
            auth_url = oauth.get_authorization_url()
            st.markdown(f'<a href="{auth_url}">Authorize with Inoreader</a>', unsafe_allow_html=True)











        


        



def input_main_query():
    st.markdown("")
    st.subheader("II. Edit Main Query Template")
    # qtemplate_instructions = (
    #     "Modify the generalized template query below. Please note curly brackets indicate "
    #     "keywords. *{variable_name}*, *{variable_description}*, and *{context}* will be replaced by each "
    #     "of variable specification listed in the table below (i.e. [SDG1: End poverty in all "
    #     "its forms everywhere, SDG2: End hunger, achieve food security..])."
    # )
    # qtemplate = (
    #     "Extract any quote that addresses “{variable_name}” which we define as “{variable_description}”. "
    #     "Only include direct quotations with the corresponding page number(s)."
    # )
    # st.session_state["main_query_input"] = st.text_area(
    #     qtemplate_instructions, value=qtemplate, height=150
    # )
    qtemplate_tips = (
        "This option is disabled during development"
    )
    st.session_state["main_query_input"] = "Extract any quote that addresses “{variable_name}” which we define as “{variable_description}”. "
    st.markdown(qtemplate_tips)


def var_json_to_df(json_fname):
    var_info_path = os.path.join(os.path.dirname(__file__), "site_text", json_fname)
    with open(var_info_path, "r", encoding="utf-8") as file:
        sdg_var_specs = json.load(file)
        return pd.DataFrame(sdg_var_specs)

def clear_variables():
    empty_df = pd.DataFrame(
        [{"variable_name": None, "variable_description": None, "context": None}]
    )
    st.session_state["variables_df"] = empty_df


def input_data_specs():
    st.markdown("")
    st.subheader("III. Specify Variables to Extract from Headlines")

    st.markdown(
        "**Type-in variable details or copy-and-paste from an excel spreadsheet (3 columns, no headers).**"
    )
    if "variables_df" not in st.session_state:
        st.session_state["variables_df"] = var_json_to_df("default_var_specs.json")
    variable_specification_parameters = [
        "variable_name",
        "variable_description",
        "context",
    ]
    variables_df = st.session_state["variables_df"]
    st.session_state["schema_table"] = st.data_editor(
        variables_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_order=variable_specification_parameters,
    )
    st.button("Clear", on_click=clear_variables)
    



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





# def build_interface(tmp_dir):
#     if "task_type" not in st.session_state:
#         st.session_state["task_type"] = "Headline extraction"
#     if "is_test_run" not in st.session_state:
#         st.session_state["is_test_run"] = True
#     load_text()
#     upload_file(tmp_dir)
#     input_main_query()
#     if "output_format_options" not in st.session_state:
#         st.session_state["output_format_options"] = {
#             "Sort by quotes; each quote will be one row": "quotes_sorted",
#             "Simply return GPT responses for each variable": "quotes_gpt_resp",
#             "Sort by quotes labelled with variable_name and subcategories": "quotes_sorted_and_labelled",
#             "Return list of quotes per variable": "quotes_structured",
#         }
#     if "json" not in st.session_state:
#         st.session_state["json"] = "no_upload"
#     if "schema_input_format" not in st.session_state:
#         st.session_state["schema_input_format"] = "Manual Entry"
#     if "output_format" not in st.session_state:
#         st.session_state["output_format"] = list(
#             st.session_state["output_format_options"].keys()
#         )[1]
#     if "custom_output_fmt" not in st.session_state:
#         st.session_state["custom_output_fmt"] = None
#     if "output_detail_df" not in st.session_state:
#         st.session_state["output_detail_df"] = None
#     input_data_specs()
#     st.divider()
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
    st.divider()

def get_user_inputs():
    json = st.session_state["json"]

    # if st.session_state["is_test_run"]:
    #     json = st.session_state["selected_json"]
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


