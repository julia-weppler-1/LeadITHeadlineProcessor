from openai import OpenAI
import os
import pandas as pd
import string
import json
from site_text.questions import PROJECT_STATUS
def new_openai_session(openai_apikey):
    os.environ["OPENAI_API_KEY"] = openai_apikey
    client = OpenAI()
    gpt_model = "gpt-4o" 
    max_num_chars = 10
    return client, gpt_model, max_num_chars


def create_gpt_messages(query, run_on_full_text):
    text_label = "collection of text excerpts"
    if run_on_full_text:
        text_label = "document"
    system_command = (
        "Use the provided "
        + text_label
        + " delimited by triple quotes to respond to instructions delimited with XML tags. Be precise. Be accurate. Be exhaustive: do not truncate your response if response is incomplete. Proceed progressively through all text provided. Do not stop processing until all text has been read. Do not be redundant. Be consistent with your responses to the same query."
    )
    return [
        {"role": "system", "content": system_command},
        {"role": "user", "content": query},
    ]


def chat_gpt_query(gpt_client, gpt_model, resp_fmt, msgs):
    response = gpt_client.chat.completions.create(
        model=gpt_model,
        temperature=0,
        response_format={"type": resp_fmt},
        messages=msgs,
    )
    return response.choices[0].message.content


def fetch_variable_info(gpt_client, gpt_model, query, resp_fmt, run_on_full_text):
    msgs = create_gpt_messages(query, run_on_full_text)
    return chat_gpt_query(gpt_client, gpt_model, resp_fmt, msgs)
    """msgs.append({"role": "assistant", "content": init_response})
    follow_up_prompt = "<instructions>Based on the previous instructions, ensure that your response has included all correct answers and/or text excerpts. If your previous resposne is correct, return the same response. If there is more to add to your previous response, return the same format with the complete, correct response.</instructions>"
    msgs.append({"role": "user", "content": follow_up_prompt})
    follow_up_response = chat_gpt_query(gpt_client, gpt_model, resp_fmt, msgs)
    return follow_up_response"""

def query_gpt_for_relevance(
    gpt_analyzer, df, variable_specs, run_on_full_text, gpt_client, gpt_model
):
    print("Variable specs", variable_specs)
    print("Querying each element in the dataframe...")

    results = []
    for index, row in df.iterrows():
        row_results = {
            "index": index,
            "Title": row.get("title", "Unknown Title")  # Store article title
        }  
        for var_name, var_desc in variable_specs.items():
            query = f'Please respond with only "yes" or "no". Is this relevant to "{var_name}", given "{var_desc}"?\n\nContent:\n"""{row["text_column"]}"""'
            resp_fmt = gpt_analyzer.resp_format_type()
            response = fetch_variable_info(gpt_client, gpt_model, query, resp_fmt, run_on_full_text)
            
            # Ensure response is stripped and standardized
            response_cleaned = response.strip().lower().translate(str.maketrans('', '', string.punctuation))
            if response_cleaned not in ["yes", "no"]:
                response_cleaned = "no"  # Default to "no" if unexpected response
            
            row_results[var_name] = response_cleaned  # Store response under variable name
        
        results.append(row_results)

    return pd.DataFrame(results)

def query_gpt_for_relevance_iterative(gpt_analyzer, df, target_questions, run_on_full_text, gpt_client, gpt_model):
    """
    Iterates through target_questions for each article in df.
    For each article, it asks each question until one returns "yes".
    If any question returns "yes", the article is marked as irrelevant ("no").
    Otherwise, it's marked as relevant ("yes").
    
    Returns:
        pd.DataFrame: A DataFrame with one row per article including the article index, title, and a "relevant" flag.
    """
    results = []
    for index, row in df.iterrows():
        is_irrelevant = False
        for question in target_questions:
            query = (
                f'Forget all previous instructions. Answer this question to the best of your ability: {question}. '
                f'Please respond with only "yes" or "no". Here is the headline: {row["text_column"]}'
            )
            resp_fmt = gpt_analyzer.resp_format_type()
            response = fetch_variable_info(gpt_client, gpt_model, query, resp_fmt, run_on_full_text)
            response_cleaned = response.strip().lower().translate(str.maketrans('', '', string.punctuation))
            print(response_cleaned)
            if response_cleaned not in ["yes", "no"]:
                response_cleaned = "no"
            if response_cleaned == "yes":
                is_irrelevant = True
                print("Skipping article due to query: ", query)
                break
        results.append({
            "index": index,
            "title": row.get("title", "Unknown Title"),
            "relevant": "no" if is_irrelevant else "yes"
        })
    return pd.DataFrame(results)

import json
from site_text.questions import PROJECT_STATUS

def query_gpt_for_project_details(gpt_client, gpt_model, article_text, steel_tech_list):
    """
    Uses GPT to extract project details from the article text in two rounds.
    
    First round (core details): 
      - scale: one of 'pilot', 'demonstration', or 'full scale'
      - project_name: the name of the project mentioned
      - timeline: the year when it will be operative. If not explicitly stated, skip.
      - technology: one of the following: <steel_tech_list>
    
    Second round (additional details): (queried only if any core detail is available)
      - company: the name of the company leading the project
      - projects mentioned: how many projects are mentioned in this article? (Multiple or one main one)
      - partners: the names of partner companies or organizations
      - continent: the continent where the project is located
      - country: the country where the project is located
      - project_status: the current status of the project, one of: <PROJECT_STATUS>
      
      Additionally, if the article text is not related to cement production at all, return empty values for these fields and include a key "irrelevant" with value true.
    
    Returns a dictionary with all keys. Missing details are returned as empty strings.
    """
    print("Inside detail module")
    tech_list_str = ", ".join(steel_tech_list)
    
    # --- First round: Core details ---
    core_prompt = (
        "You are an information extraction assistant. Given the article text below, extract the following core details if available. You may need to infer them:\n"
        "- scale: one of 'pilot', 'demonstration', or 'full scale'\n"
        "- project_name: the name of the project mentioned\n"
        "- timeline: the year when it will be operative. If not explicitly stated, skip.\n"
        f"- technology: one of the following: {tech_list_str}\n\n"
        "Return your answer as a JSON object with keys exactly: 'scale', 'project_name', 'timeline', 'technology'. "
        "If a detail is not available, leave its value as an empty string.\n\n"
        "Article text:\n\"\"\"\n" + article_text + "\n\"\"\""
    )
    
    msgs_core = [
        {"role": "system", "content": "You are an assistant that extracts project details from text."},
        {"role": "user", "content": core_prompt}
    ]
    
    try:
        response_core = gpt_client.chat.completions.create(
            model=gpt_model,
            temperature=0,
            messages=msgs_core,
        )
        print("MODEL RESP (core):", response_core)
        output_core = response_core.choices[0].message.content.strip()
        if output_core.startswith("```json"):
            output_core = output_core[len("```json"):].strip()
        if output_core.endswith("```"):
            output_core = output_core[:-3].strip()
        core_details = json.loads(output_core)
    except Exception as e:
        print(f"Error extracting core project details: {e}")
        core_details = {}
    
    # Ensure that all core keys are present.
    for key in ['scale', 'project_name', 'timeline', 'technology']:
        if key not in core_details:
            core_details[key] = ""
    
    # --- Second round: Additional details ---
    if any(core_details[key] for key in ['scale', 'project_name', 'timeline', 'technology']):
        additional_prompt = (
            "You are an information extraction assistant. Given the article text below, extract the following additional details if available. You may need to infer them:\n"
            "- company: the name of the company leading the project\n"
            "- projects mentioned: how many projects are mentioned in this article? (Multiple or one main one)\n"
            "- partners: the names of partner companies or organizations\n"
            "- continent: the continent where the project is located\n"
            "- country: the country where the project is located\n"
            f"- project_status: the current status of the project, one of the following: {', '.join(PROJECT_STATUS)}\n\n"
            "IMPORTANT: If the article text is not related to cement production at all or it is about a FINISHED product, return empty values for all these fields "
            "and include a key \"irrelevant\" with value true.\n\n"
            "Return your answer as a JSON object with keys exactly: 'company', 'projects mentioned', 'partners', 'continent', 'country', 'project_status', and optionally 'irrelevant'. "
            "If a detail is not available, leave its value as an empty string.\n\n"
            "Article text:\n\"\"\"\n" + article_text + "\n\"\"\""
        )
        
        msgs_additional = [
            {"role": "system", "content": "You are an assistant that extracts additional project details from text."},
            {"role": "user", "content": additional_prompt}
        ]
        
        try:
            response_additional = gpt_client.chat.completions.create(
                model=gpt_model,
                temperature=0,
                messages=msgs_additional,
            )
            print("MODEL RESP (additional):", response_additional)
            output_additional = response_additional.choices[0].message.content.strip()
            if output_additional.startswith("```json"):
                output_additional = output_additional[len("```json"):].strip()
            if output_additional.endswith("```"):
                output_additional = output_additional[:-3].strip()
            additional_details = json.loads(output_additional)
        except Exception as e:
            print(f"Error extracting additional project details: {e}")
            additional_details = {}
        
        for key in ['company', 'partners', 'continent', 'country', 'project_status']:
            if key not in additional_details:
                additional_details[key] = ""
    else:
        additional_details = {
            'company': "",
            'projects mentioned': "",
            'partners': "",
            'continent': "",
            'country': "",
            'project_status': ""
        }
    
    combined_details = {**core_details, **additional_details}
    return combined_details
