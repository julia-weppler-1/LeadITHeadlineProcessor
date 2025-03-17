"""
This module contains classes and functions for analyzing GPT responses from Inoreader feeds.
It includes an analyzer ONLY for headline extraction.
"""

import json


class GPTAnalyzer:
    """
    Base class for analyzing GPT responses from PDFs.
    """

    def __init__(
        self, json, main_query, variable_specs, output_fmt, additional_info
    ):
        """
        Initializes the GPTAnalyzer with the given parameters.
        """
        self.json = json
        self.main_query = main_query
        self.variable_specs = variable_specs
        self.output_fmt = output_fmt
        self.additional_info = additional_info

    def __str__(self):
        """
        Returns a string representation of the GPTAnalyzer.
        """
        class_name = self.__class__.__name__
        return f"{class_name} -- JSON: {self.json}, Main Query: {self.main_query}, Variables: {self.variable_specs}"

    def output_fmt_prompt(self, var_name):
        """
        Returns the output format prompt for the given variable name.
        """
        pass

    def format_gpt_response(self, resp):
        """
        Formats the GPT response.
        """
        pass

    def get_chunk_size(self):
        """
        Returns the chunk size for processing PDFs.
        """
        return 200

    def get_results(self, headline_info):
        """
        Processes the headline information and returns the results.
        """
        print("headline Info Received:", headline_info)
        
        gpt_responses = {}
        
        headers = self.get_output_headers()
        
        if len(headers) < 2:
            print("Error: Not enough headers returned!")
            return {}
        
        hdr = headers[1]
        
        for var_name, var_val in headline_info.items():
            print(f"Processing {var_name}: {var_val}")  # Debug print
            
            if var_val.count('"') == 2 and var_val[0] == '"' and var_val[-1] == '"':
                var_val = var_val[1:-1]
            
            if len(var_val) > len(var_name):
                if var_val[: len(var_name)] == var_name:
                    var_val = var_val.replace(f"{var_name}: ", "", 1)
            
            gpt_responses[var_name] = {hdr: var_val}
        
        return gpt_responses


    def get_output_headers(self):
        """
        Returns the output headers for the results.
        """
        return ["Variable Name", "GPT Response"]

    def get_num_excerpts(self, num_pages):
        """
        Returns the number of excerpts to process based on the number of pages.
        """
        if num_pages < 100:
            return 40
        else:
            return 40 + int(num_pages / 5.0)

    def optional_add_categorization(self, v_name, query):
        """
        Optionally adds categorization to the query.
        """
        return query

    def resp_format_type(self):
        """
        Returns the response format type.
        """
        return "json_object"


class DefaultAnalyzer(GPTAnalyzer):
    """
    Analyzer for handling default GPT responses.
    """

    def __init__(
        self, json, main_query, variable_specs, output_fmt, additional_info
    ):
        """
        Initializes the DefaultAnalyzer with the given parameters.
        """
        super().__init__(
            json, main_query, variable_specs, output_fmt, additional_info
        )

    def output_fmt_prompt(self, var_name):
        """
        Returns the output format prompt for the given variable name.
        """
        output_fmt_str = "{'value': '...', 'relevant_page_numbers': '...'}"
        return f"Return your response in the following json format: \n {output_fmt_str}"

    def format_gpt_response(self, resp):
        """
        Formats the GPT response.
        """
        return f"{json.loads(resp)['value']} [page(s) {resp['relevant_page_numbers']}]"



class HeadlineAnalyzer(GPTAnalyzer):
    """
    Analyzer for extracting and formatting quotes from GPT responses.
    """

    def __init__(
        self, json, main_query, variable_specs, output_fmt, additional_info
    ):
        """
        Initializes the QuoteAnalyzer with the given parameters.
        """
        super().__init__(
            json, main_query, variable_specs, output_fmt, additional_info
        )

    def output_fmt_prompt(self, var_name):
        """
        Returns the output format prompt for the given variable name.
        """
        if self.output_fmt == "quotes_gpt_resp":
            return "Provide an exhaustive list of relevant quotes."
        else:
            output_json_fmt = {
                "list_of_quotes": [{"quote": "...", "page_number": "..."}]
            }
            if self.output_fmt == "quotes_sorted_and_labelled":
                for col in self.additional_info.columns[1:]:
                    label = f"relevant_{col.lower().replace(' ', '_')}"
                    output_json_fmt["list_of_quotes"][0][label] = "..."
            output_fmt_str = str(output_json_fmt).replace("]}", ", ...}]")
            return f"Return your response in the following json format: \n {output_fmt_str}"

    def optional_add_categorization(self, var_name, query):
        """
        Optionally adds categorization to the query.
        """
        if self.output_fmt == "quotes_sorted_and_labelled":
            row = self.additional_info[
                self.additional_info["variable_name"] == var_name
            ].iloc[0]
            subcat_label1 = self.additional_info.columns[1]
            query += f"For each relevant quote, select which {subcat_label1} it addresses from the following list ({row[subcat_label1]})"
            if len(self.additional_info.columns) > 2:
                if self.additional_info.columns[2]:
                    subcat_label2 = self.additional_info.columns[1]
                    query += f" and which {subcat_label2} it addresses from the following list ({row[subcat_label1]})"
            query += "."
        return query

    def format_gpt_response(self, resp):
        """
        Formats the GPT response.
        """
        if self.output_fmt == "quotes_gpt_resp":
            return resp
        else:
            return json.loads(resp)["list_of_quotes"]

    def get_results(self, stream_info):
        """
        Processes the headline information and returns the results.
        """
        relevant_articles = []  # List to store relevant article titles
        quotes = {}
        if self.output_fmt == "quotes_gpt_resp":
            for article in stream_info:  # Iterate through the list of dictionaries
                title = article.get("Title", "Unknown Title")  # Get the title safely
                relevance = article.get("Relevant", "no").strip().lower()  # Standardize response
                if relevance == "yes":
                    relevant_articles.append(title)  # Store relevant article title
                quotes[title] = {'Relevant': relevance}  # Store relevant information
            return quotes, relevant_articles  # Return relevant articles as well
        
        else:
            return quotes, relevant_articles

    def get_output_headers(self):
        """
        Returns the output headers for the results.
        """
        if self.output_fmt == "quotes_gpt_resp":
            return ["Variable", "Relevant Quotes"]
        else:
            headers = ["Quote", "Relevant Variables"]
            if self.output_fmt == "quotes_sorted_and_labelled":
                for subcat_header in self.additional_info.columns[1:]:
                    headers.append(subcat_header)
            return headers

    def get_chunk_size(self):
        """
        Returns the chunk size for processing PDFs.
        """
        return 200

    def get_num_excerpts(self, num_pages):
        """
        Returns the number of excerpts to process based on the number of pages.
        """
        if num_pages < 200:
            return 20 + num_pages
        else:
            return 220

    def resp_format_type(self):
        """
        Returns the response format type.
        """
        return "text" if self.output_fmt == "quotes_gpt_resp" else "json_object"

def get_task_types():
    """
    Returns a dictionary mapping task types to their corresponding analyzer classes.
    """
    return {
        "Headline extraction": HeadlineAnalyzer,
        "Targeted inquiries": DefaultAnalyzer,
    }


def get_analyzer(
    task_type, output_fmt, json, main_query, variable_specs,additional_info
):
    """
    Returns an instance of the appropriate analyzer class based on the task type.
    """
    task_analyzer_class = get_task_types()[task_type]

    return task_analyzer_class(
        json, main_query, variable_specs, output_fmt, additional_info
    )
