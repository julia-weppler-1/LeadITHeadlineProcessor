from openai import OpenAI
import os
import pandas as pd
import string

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
