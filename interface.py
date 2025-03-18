from utils.analysis import get_analyzer, get_task_types
from tempfile import NamedTemporaryFile
import base64
import json
import os
import pandas as pd
import streamlit as st
import zipfile
from services import oauth


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
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "JSON File"

    # Use radio buttons instead of tabs to enforce exclusivity
    active_tab = st.radio(
        "Select analysis type:", 
        ["JSON File", "Connect to Inoreader"],
        horizontal=True,
        help="""Select **JSON File** if using tool for the first time on a selection of downloaded news articles from an RSS app. 
        **Connect to Inoreader** may be run on an existing Inoreader stream."""
        )

    if active_tab != st.session_state["active_tab"]:
        # Clear any previous uploads when switching tabs
        st.session_state["json"] = []
        st.session_state["selected_json"] = []
        st.session_state["temp_zip_path"] = None
        st.session_state["run_disabled"] = True  # Prevent running with no files

    st.session_state["active_tab"] = active_tab  # Update session state

    json = []  # Store uploaded JSON file paths
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
                checked = False  # Automatically set the "Run on subset" checkbox to off
            else:
                if "max_files" not in st.session_state:
                    st.session_state["max_files"] = 3
                if "file_select_label" not in st.session_state:
                    st.session_state["file_select_label"] = "Select 1-3 subfiles to run on"

                checked = st.checkbox(
                    "Run on subset",
                    value=True,
                    help="Do not turn this off until you are ready for your final run.",
                )

            if checked:
                st.session_state["run_disabled"] = False  # Enable run if subset is selected
                fnames = {os.path.basename(p): p for p in json}
                first = os.path.basename(json[0])
                selected_fnames = st.multiselect(
                    st.session_state["file_select_label"],
                    fnames.keys(),
                    default=[first],
                    max_selections=st.session_state["max_files"],
                )
                st.session_state["selected_json"] = [
                    fnames[selected_fname] for selected_fname in selected_fnames
                ]
            else:
                if len(json) > 1: # If not checked to run on subset and there is more than 1 PDF
                    passcode = st.text_input("Enter passcode", type="password")
                    if passcode:
                        apikey_ids = {
                            st.secrets["access_password"]: "openai_apikey",
                            st.secrets["access_password_adis"]: "openai_apikey_adis",
                            st.secrets["access_password_sharone"]: "openai_apikey_sharone",
                            st.secrets["access_password_bb"]: "openai_apikey_bb",
                        }
                        if passcode in apikey_ids:
                            st.session_state["apikey_id"] = apikey_ids[passcode]
                            st.session_state["is_test_run"] = False
                            st.session_state["max_files"] = None
                            st.session_state["file_select_label"] = (
                                "Select any number of PDFs to analyze. Or, uncheck 'Run on Subset' to analyze all uploaded PDFs"
                            )
                            st.session_state["run_disabled"] = False  # Enable Run button
                            st.success("Access granted. All PDFs in the zip-file will be processed. Please proceed.", icon="✅")
                        else:
                            st.session_state["run_disabled"] = True
                            st.error("Incorrect password. Click 'Run on subset' above. The 1-3 documents specified will be processed.", icon="❌")
                    else:
                        st.session_state["run_disabled"] = True  
                        st.error("You need a passcode to proceed. If you do not have one, please select 'Run on subset' above.", icon="❌")
                else: # If not checks and there is 1 PDF, we don't need a passcode
                    st.session_state["selected_json"] = [json[0]]
                    st.session_state["run_disabled"] = False  # Enable Run if only one PDF
        else:
            st.warning("Please upload a single JSON file.", icon="⚠️")
    elif active_tab == "Connect to Inoreader":
        st.subheader("Authorize Inoreader Access")

        auth_url = oauth.get_inoreader_auth_url()
        st.markdown(f"[Click here to authorize with Inoreader]({auth_url})", unsafe_allow_html=True)
    



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





def build_interface(tmp_dir):
    if "task_type" not in st.session_state:
        st.session_state["task_type"] = "Headline extraction"
    if "is_test_run" not in st.session_state:
        st.session_state["is_test_run"] = True
    load_text()
    upload_file(tmp_dir)
    input_main_query()
    if "output_format_options" not in st.session_state:
        st.session_state["output_format_options"] = {
            "Sort by quotes; each quote will be one row": "quotes_sorted",
            "Simply return GPT responses for each variable": "quotes_gpt_resp",
            "Sort by quotes labelled with variable_name and subcategories": "quotes_sorted_and_labelled",
            "Return list of quotes per variable": "quotes_structured",
        }
    if "json" not in st.session_state:
        st.session_state["json"] = "no_upload"
    if "schema_input_format" not in st.session_state:
        st.session_state["schema_input_format"] = "Manual Entry"
    if "output_format" not in st.session_state:
        st.session_state["output_format"] = list(
            st.session_state["output_format_options"].keys()
        )[1]
    if "custom_output_fmt" not in st.session_state:
        st.session_state["custom_output_fmt"] = None
    if "output_detail_df" not in st.session_state:
        st.session_state["output_detail_df"] = None
    input_data_specs()
    st.divider()


def get_user_inputs():
    json = st.session_state["json"]
    if st.session_state["is_test_run"]:
        json = st.session_state["selected_json"]
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


def display_output(docx_fname):
    with open(docx_fname, "rb") as f:
        binary_file = f.read()
        st.download_button(
            label="Download Results",
            data=binary_file,
            file_name="results.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


