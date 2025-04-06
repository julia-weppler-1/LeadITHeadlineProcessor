# validate_gpt_results.py
from rapidfuzz import fuzz

def check_detail_in_text_fuzzy(detail, article_text):
    """
    Returns the fuzzy matching score between detail and article_text.
    """
    detail_norm = detail.strip().lower()
    text_norm = article_text.lower()
    score = fuzz.partial_ratio(detail_norm, text_norm)
    return score

def get_check_results_flag(extracted_details, article_text):
    """
    For each non-empty field in extracted_details, compute the fuzzy match score with article_text.
    If any score is below the threshold, return "CHECK RESULTS" along with the scores.
    Otherwise, return an empty string.
    """
    threshold=90
    print("ED:", extracted_details)
    scores = {}
    for key, value in extracted_details.items():
        print("KV:", key , value)
        if value.strip():
            score = check_detail_in_text_fuzzy(value, article_text)
            print("SCORE:", score)
            scores[key] = score
    # If any score is below threshold, flag the row.
    if any(score < threshold for score in scores.values()):
        print("returning")
        return "CHECK RESULTS", scores
    return "", scores
