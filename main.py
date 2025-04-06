"""
This script processes PDF documents to extract relevant policy information using OpenAI's GPT API.
It reads the PDFs, extracts text chunks, generates embeddings, and queries GPT for specific variables.
The results are formatted and saved in a Word document, which can be emailed to the user.

Modules:
- analysis: Contains classes that define different ways of analyzing documents.
    - Note: the analyzer module is ont directly referenced in this file (it is in interface.py)
- interface: Handles the user interface and interactions.
- query_gpt: Manages the GPT session and queries.
- read_pdf: Extracts text chunks from PDF documents.
- relevant_excerpts: Generates embeddings and finds relevant text excerpts for each variable.
- results: Formats and outputs the results.

Functions:
- get_resource_path: Returns the resource path for a given relative path.
- extract_news_doc_info: Extracts policy document information by querying GPT for each variable.
- print_milestone: Prints a milestone with the elapsed time and additional information.
- fetch_gist_content: Fetches the content of a gist from GitHub.
- log: Logs new content to a GitHub gist.
- main: Main function to process PDFs and generate an output document.

Usage:
Run "python -m streamlit run .\main.py" to start the Streamlit application.
"""

from interface import (
    build_interface,
    display_output,
    get_user_inputs,
    load_header,
    # display_onedrive_auth
)
from tabs.about import about_tab
from tabs.faq import faq_tab
from services.query_gpt import new_openai_session, query_gpt_for_relevance, query_gpt_for_relevance_iterative, query_gpt_for_project_details
from site_text.questions import STEEL_YES, STEEL_NO, IRON_YES, IRON_NO, STEEL_TECH, IRON_TECH
from utils.read_pdf import extract_text_chunks_from_pdf
from utils.read_docx import extract_text_chunks_from_docx
from utils.read_json import parse_json_feed
from services.inoreader import build_df_for_folder, fetch_full_article_text
from utils.relevant_excerpts import (
    find_top_relevant_texts
)
from utils.results import format_output_doc, get_output_fname, output_results, output_results_excel  
from services.onedrive import get_onedrive_access_token, upload_file_to_onedrive
from services.inoreader import resolve_with_playwright
from docx import Document
from tempfile import TemporaryDirectory
import json
import os
import requests
import streamlit as st
import time
import traceback
import secrets

def get_resource_path(relative_path):
    """
    Returns the resource path for a given relative path.
    """
    return relative_path

def extract_text_chunks(file_path, max_chunk_size):
    """
    Extracts text chunks from a file (PDF or DOCX).

    Args:
        file_path (str): The path to the file.
        max_chunk_size (int): The maximum size of each text chunk.

    Returns:
        list: A list of dictionaries containing text chunks, number of pages, character count, and section number.
    """
    if file_path.lower().endswith(".pdf"):
        return extract_text_chunks_from_pdf(file_path, max_chunk_size)
    elif file_path.lower().endswith(".docx"):
        return extract_text_chunks_from_docx(file_path, max_chunk_size)
    else:
        return [{"error": f"Unsupported file format: {file_path}"}]
# USE THIS LATER FOR NEWS ARTICLE INFO?
def extract_news_doc_info(
    gpt_analyzer,
    text_embeddings,
    input_text_chunks,
    char_count,
    var_embeddings,
    num_excerpts,
    openai_apikey,
):
    """
    Extracts policy document information by querying GPT for each variable specified.

    Args:
        gpt_analyzer: The GPT analyzer object .
        text_embeddings: Embeddings of the text chunks.
        input_text_chunks: List of text chunks from the input document.
        char_count: Character count of the text.
        var_embeddings: Embeddings for the variables.
        num_excerpts: Number of excerpts to extract.
        openai_apikey: API key for OpenAI.

    Returns:
        A dictionary listing for each variable the response from GPT.
        The response format depends on the Analyzer class selected.
    """
    news_doc_data = {}
    text_chunks = input_text_chunks
    client, gpt_model, max_num_chars = new_openai_session(openai_apikey)
    # If the text is short, we don't need to generate embeddings to find "relevant texts"
    # If the text is long, text_chunks (defined above) will be replaced with the top relevant texts
    run_on_full_text = char_count < (max_num_chars - 1000)
    for var_name in var_embeddings:
        var_embedding, var_desc, context = (
            var_embeddings[var_name]["embedding"],
            var_embeddings[var_name]["variable_description"],
            var_embeddings[var_name]["context"],
        )
        if not run_on_full_text:
            top_text_chunks_w_emb = find_top_relevant_texts(
                text_embeddings,
                input_text_chunks,
                var_embedding,
                num_excerpts,
                var_name,
            )
            text_chunks = [chunk_tuple[1] for chunk_tuple in top_text_chunks_w_emb]
        resp = query_gpt_for_relevance(
            gpt_analyzer,
            var_name,
            var_desc,
            context,
            text_chunks,
            run_on_full_text,
            client,
            gpt_model,
        )
        news_doc_data[var_name] = gpt_analyzer.format_gpt_response(resp)
    return news_doc_data


def print_milestone(milestone_desc, last_milestone_time, extras={}, mins=True):
    """
    Prints a milestone with the elapsed time and additional information.

    Args:
        milestone_desc: Description of the milestone.
        last_milestone_time: Time of the last milestone.
        extras: Additional information to print.
        mins: Whether to print the elapsed time in minutes or seconds.
    """
    unit = "minutes" if mins else "seconds"
    elapsed = time.time() - last_milestone_time
    elapsed = elapsed / 60.0 if mins else elapsed
    print(f"{milestone_desc}: {elapsed:.2f} {unit}")
    for extra in extras:
        print(f"{extra}: {extras[extra]}")


def fetch_gist_content(gist_url, headers, log_fname):
    """
    Fetches the content of a gist from GitHub.
    This is used to update our log file with the latest run information.

    Args:
        gist_url: URL of the gist.
        headers: Headers for the request.
        log_fname: Filename of the log file in the gist.

    Returns:
        The content of the gist file if successful, None otherwise.
    """
    response = requests.get(gist_url, headers=headers)
    if response.status_code == 200:
        gist_data = response.json()
        return gist_data["files"][log_fname]["content"]
    else:
        print("Failed to fetch gist content.")
        return None


def log(new_content):
    """
    Logs new activity to a GitHub gist.

    Args:
        new_content: The new content to log.
    """
    github_token = st.secrets["github_token"]
    log_fname = "log"
    gist_base_url = "https://api.github.com/gists"
    gist_url = f"{gist_base_url}/47029f286297a129a654110ebe420f5f"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    current_content = fetch_gist_content(gist_url, headers, log_fname)
    if current_content is not None:
        updated_content = f"{current_content} \n {new_content}"
        data = {"files": {log_fname: {"content": updated_content}}}
        requests.patch(gist_url, headers=headers, data=json.dumps(data))


def main(gpt_analyzer, openai_apikey):
    """
    Main function to process headlines and generate an output document.

    Args:
        gpt_analyzer: The GPT analyzer object.
        openai_apikey: API key for OpenAI.

    Returns:
        The total number of articles processed.
    """

    total_start_time = time.time()
    if st.session_state["active_tab"] == "JSON File":
        json_path = get_resource_path(gpt_analyzer.json[0])
        try:
            headlines = parse_json_feed(json_path)
            print(f"Parsed {len(headlines)} headlines from JSON.")
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            return 0
    else:
        try:
            headlines = build_df_for_folder("LeadIT-Iron")
            json_path = "Inoreader"
            print(headlines)
            print(f"Parsed {len(headlines)} headlines from JSON.")
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            return 0
    openai_client, gpt_model, _ = new_openai_session(openai_apikey)
    
    # Convert headlines into a DataFrame with necessary text column
    headlines["text_column"] = headlines["title"] + " " + headlines.get("summary", "")
    folder = "LeadIT-Iron"
    print("Folder", folder)
    if folder == "LeadIT-Steel":
        target_questions = STEEL_NO
    elif folder == "LeadIT-Iron":
        target_questions = IRON_NO
    else:
        target_questions = []  # or some default
    print("Target q's", target_questions)
    # Assuming your DataFrame of articles is in `headlines` and you have run_on_full_text defined
    relevance_df = query_gpt_for_relevance_iterative(
        gpt_analyzer,
        headlines,
        target_questions,
        run_on_full_text=True,  # or False, as applicable
        gpt_client=openai_client,
        gpt_model=gpt_model
    )
    # Process relevant results for output
    # After obtaining relevance_df from query_gpt_for_relevance_iterative:
    relevant_articles = []
    irrelevant_articles = []

    for _, row in relevance_df.iterrows():
        article_index = row["index"]
        article_row = headlines.loc[article_index]
        article_row["title"] = article_row["title"].split(" - ")[0].strip()
        title = article_row["title"] 
        article_row["url"] = resolve_with_playwright(article_row["url"])
        url = article_row["url"]
        if row["relevant"] != "no":
            # Fetch full article text (or use text from the article if already available)
            full_text = fetch_full_article_text(article_row)
            # Extract project details from the article text using the new GPT function.
            details = query_gpt_for_project_details(openai_client, gpt_model, full_text, IRON_TECH)
            print("done w/ details")
            if details:
                # Merge the details into the article dictionary.
                article_info = {
                    "title": title,
                    "url": url,
                    "full_text": full_text,
                    **details
                }
                relevant_articles.append(article_info)
            else:
                article_info = {
                    "title": title,
                    "url": url
                }
                relevant_articles.append(article_info)
        else:
            irrelevant_articles.append({
                "title": title,
                "url": url
            })

    print(f"Total relevant articles: {len(relevant_articles)}")
    print(f"Total irrelevant articles: {len(irrelevant_articles)}")

    # Define output file name and path
    output_fname = get_output_fname(get_resource_path, filetype="xlsx")
    print(f"Saving Excel file to {output_fname}")

    # Use the new Excel output function
    output_results_excel(relevant_articles, irrelevant_articles, output_fname)

    # Optionally, display or notify the user that the file has been created
    display_output(output_fname)

    # At the bottom of your main() function (after display_output)
    if "onedrive_clicked" not in st.session_state:
        st.session_state.onedrive_clicked = False

    # Create a container for output messages.
    onedrive_output = st.empty()

    if st.button("Send Results to OneDrive"):
        st.session_state.onedrive_clicked = True

    if st.session_state.onedrive_clicked:
        onedrive_output.write("Trying to get access token...")
        access_token = get_onedrive_access_token()
        onedrive_output.write("Access token:", access_token)
        if access_token:
            # Hardcode the OneDrive file name or allow the user to specify one.
            onedrive_filename = "results.xlsx"
            result = upload_file_to_onedrive(access_token, output_fname, onedrive_filename)
            if result:
                onedrive_output.success("Results successfully sent to OneDrive!")
            else:
                onedrive_output.error("OneDrive upload failed.")

    print_milestone("Done processing headlines", total_start_time, {"Number of articles": len(relevant_articles)})
    return len(relevant_articles)



if __name__ == "__main__":
    query_params = st.query_params

    if "state" in query_params and "code" in query_params:
        st.session_state["oauth_state"] = query_params["state"]
    elif "oauth_state" not in st.session_state:
        st.session_state["oauth_state"] = secrets.token_urlsafe(16)
    
    try:
        with TemporaryDirectory() as temp_dir:
            logo_path = os.path.join(os.path.dirname(__file__), "public", "logo2.jpg")
            st.set_page_config(
                layout="wide", page_title="AI Headline Processor", page_icon=logo_path
            )
            load_header()
            # display_onedrive_auth()
            
            _, centered_div, _ = st.columns([1, 3, 1])
            with centered_div:
                tab1, tab2, tab3 = st.tabs(["Tool", "About", "FAQ"])
                with tab1:
                    build_interface(temp_dir)
                    if st.button("Run", disabled=st.session_state.get("run_disabled", False)):
                        gpt_analyzer = get_user_inputs()
                        with st.spinner("Generating output document..."):
                            apikey_id = "openai_apikey"
                            if "apikey_id" in st.session_state:
                                apikey_id = st.session_state["apikey_id"]
                            openai_apikey = st.secrets[apikey_id]
                            num_pages = main(gpt_analyzer, openai_apikey)
                            log(
                                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} GMT --> apikey_id; {num_pages} pages; {gpt_analyzer}"
                            )
                        st.success("Document generated!")
                        os.unlink(st.session_state["temp_zip_path"])
                with tab2:
                    about_tab()
                with tab3:
                    faq_tab()
    except Exception as e:
        log(
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} GMT --> apikey_id:{e}"
        )
        log(traceback.format_exc())
