import os
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

WOLFRAM_API_KEY = os.environ.get("WOLFRAM_API_KEY")


def wolfram_query_full(query, app_id=WOLFRAM_API_KEY):
    """
    Query Wolfram Alpha's full API and extract the most relevant text response.

    Args:
        query (str): The question/query to ask Wolfram Alpha
        app_id (str): Your Wolfram Alpha App ID

    Returns:
        str: Simplified text response extracted from XML
    """
    # Encode the query for URL
    encoded_query = quote(query)

    # Use the full API endpoint
    url = f"http://api.wolframalpha.com/v2/query?appid={app_id}&input={encoded_query}&format=plaintext"

    response = requests.get(url, timeout=15)

    if response.status_code != 200:
        return (
            f"Error: Unable to get response (status code: {response.status_code})"
        )

    # Parse the XML response
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        return "uhh"

    # Check if query was successful
    if root.get("success") != "true":
        return "wot?"

    # Extract the best answer
    best_answer = extract_best_answer(root)

    if best_answer:
        return best_answer
    else:
        return "AI is not that advanced"


def extract_best_answer(root):
    """
    Extract the most relevant answer from Wolfram Alpha XML response.

    Args:
        root: XML root element from Wolfram Alpha response

    Returns:
        str: Best answer text or None if no good answer found
    """
    answers = []

    # Priority order for pod titles (most useful first)
    priority_pods = [
        "Result",
        "Decimal approximation",
        "Exact result",
        "Solution",
        "Value",
        "Answer",
        "Simplified form",
        "Derivative",
        "Integral",
        "Population",
        "Current result",
        "Basic information",
    ]

    # Get all pods
    pods = root.findall(".//pod")

    # First, look for high-priority pods
    for priority_title in priority_pods:
        for pod in pods:
            title = pod.get("title", "").lower()
            if priority_title.lower() in title:
                text = extract_pod_text(pod)
                if text and is_good_answer(text):
                    return f"{pod.get('title')}: {text}"

    # If no priority pods found, look for any pod with useful content
    for pod in pods:
        title = pod.get("title", "")

        # Skip input interpretation and other meta pods
        if should_skip_pod(title):
            continue

        text = extract_pod_text(pod)
        if text and is_good_answer(text):
            answers.append(f"{title}: {text}")

    # Return the first good answer we found
    return answers[0] if answers else None


def extract_pod_text(pod):
    """Extract plaintext from a pod."""
    plaintext_elements = pod.findall(".//plaintext")
    texts = []

    for elem in plaintext_elements:
        if elem.text and elem.text.strip():
            texts.append(elem.text.strip())

    return " | ".join(texts) if texts else None


def should_skip_pod(title):
    """Check if we should skip this pod based on its title."""
    skip_titles = [
        "input interpretation",
        "input",
        "plots",
        "plot",
        "number line",
        "visual representation",
        "illustration",
        "wikipedia summary",
        "web definitions",
        "alternate forms",
    ]

    title_lower = title.lower()
    return any(skip in title_lower for skip in skip_titles)


def is_good_answer(text):
    """Check if the text looks like a useful answer."""
    if not text or len(text.strip()) < 2:
        return False

    # Filter out unhelpful responses
    bad_indicators = [
        "(no data available)",
        "(not available)",
        "(computation timed out)",
        "(requires interactivity)",
        "wolfram|alpha cannot",
        "cannot be computed",
    ]

    text_lower = text.lower()
    return not any(bad in text_lower for bad in bad_indicators)


# Example usage with better formatting
def chatbot_wolfram_query(query, app_id=WOLFRAM_API_KEY):
    """
    Wrapper function that returns a clean response for chatbot use.
    """
    result = wolfram_query_full(query, app_id)

    # Clean up the response for better readability
    if result.startswith("Result:"):
        result = result[7:].strip()  # Remove 'Result:' prefix for cleaner output

    # Limit response length for chat
    # if len(result) > 500:
    #     result = result[:497] + "..."

    return result
