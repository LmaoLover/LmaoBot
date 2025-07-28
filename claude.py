import anthropic
import markdown


class LLMClient:
    """Class to handle interactions with LLM services"""

    def __init__(self, api_key=None, base_url=None):
        """Initialize the LLM client with API credentials"""
        self.api_key = api_key
        self.base_url = base_url
        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def generate_response(
        self,
        system_prompt,
        user_input=None,
        messages=None,
        model="grok-beta",
        temperature=0.6,
        max_tokens=1500,
        timeout=16,
    ):
        """
        Generate a response from the LLM model

        Args:
            system_prompt (str): The system prompt to provide context to the model
            user_input (str, optional): Single user input for simple models
            messages (list, optional): List of message dicts with 'role' and 'content'
                                      for chat-style models
            model (str): Model identifier to use for generation
            temperature (float): Temperature setting for the model
            max_tokens (int): Maximum tokens in the response
            timeout (int): Timeout for the API call in seconds

        Returns:
            str: Generated response text
        """
        try:
            # Different handling based on model requirements
            if messages is not None:
                # Messages API (standard for most models)
                completion = self.client.messages.create(
                    model=model,
                    system=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                return completion.content[0].text or ""
            else:
                # Single message input (fallback for simpler interactions)
                # Note: Using messages API with a single user message
                completion = self.client.messages.create(
                    model=model,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_input}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                return completion.content[0].text or ""
        except Exception as e:
            raise e


def format_chat_history(
    history,
    format_type="messages",
    max_messages=15,
    filter_text=None,
    cutoff_message=None,
    cutoff_user=None,
):
    """
    Format chat history based on the required format type

    Args:
        history (list): List of message objects
        format_type (str): Type of formatting - "messages" for structured message list,
                          "string" for condensed string format
        max_messages (int): Maximum number of messages to include
        filter_text (str, optional): Text to filter out from messages

    Returns:
        Union[list, str]: Formatted history in requested format
    """
    filtered_history = []

    # Filter history first
    for msg in history[:max_messages]:
        if msg and (not filter_text or filter_text not in msg.body):
            filtered_history.append(msg)

    if cutoff_message:
        for i, item in enumerate(filtered_history):
            if item.body.strip() == cutoff_message:
                del filtered_history[i + 1 :]
                break

    # Format based on the requested type
    if format_type == "messages":
        # Message list format for chat models
        messages = []
        for msg in filtered_history:
            messages.append(
                {
                    "role": (
                        "assistant" if msg.user.name.lower() == "lmaolover" else "user"
                    ),
                    "content": (
                        msg.body
                        if msg.user.name.lower() == "lmaolover"
                        else f"<{msg.user.name}>: {msg.body}"
                    ),
                }
            )
        return list(reversed(messages))

    elif format_type == "string":
        # String format for simpler models
        history_text = ""
        for msg in filtered_history:
            history_text += f"<{msg.user.name}>: {msg.body}\n"
        return history_text

    else:
        raise ValueError(f"Unknown format_type: {format_type}")


def render_history(history, max_length=511):
    """
    Render chat history as a string with a maximum length

    Args:
        history (list): List of message objects
        max_length (int): Maximum length of the rendered history

    Returns:
        str: Rendered chat history
    """
    history_text = ""
    for msg in history:
        if hasattr(msg, "user") and hasattr(msg, "body"):
            history_text += f"<{msg.user.name}>: {msg.body}\n"

    return history_text[:max_length]


def format_response_for_html(response):
    """
    Format a markdown response for HTML display

    Args:
        response (str): Markdown formatted response

    Returns:
        str: HTML formatted response
    """
    return (
        markdown.markdown(response)
        .replace("<p>", "")
        .replace("</p>", "")
        .replace("<strong>", "<b>")
        .replace("</strong>", "</b>")
        .replace("<em>", "<i>")
        .replace("</em>", "</i>")
        .replace("<li>\n", "<li>")
        .replace("\n</li>", "</li>")
    )


def check_model_refusal(response, model="grok-beta"):
    """
    Check if a response contains refusal language based on the model

    Args:
        response (str): Response text to check
        model (str): Model that generated the response

    Returns:
        bool: True if the response contains refusal language
    """
    # Define refusal phrases by model
    refusal_phrases = {
        "default": [
            "As an AI",
            "I don't have the ability",
            "I'm not able to",
            "I'm unable to",
            "can't fulfill",
            "cannot fulfill",
            "can't assist",
            "cannot assist",
            "can't comply",
            "cannot comply",
            "can't engage",
            "cannot engage",
            "can't generate",
            "cannot generate",
        ],
        "claude-3": [
            "As Claude",
            "As an AI assistant",
            "I apologize, but I cannot",
            "I'm not designed to",
        ],
        "grok-beta": [
            "As Grok",
            "As an AI model",
            "I cannot provide",
        ],
    }

    # Get the appropriate refusal phrases
    model_type = "default"
    if "claude" in model.lower():
        model_type = "claude-3"
    elif "grok" in model.lower():
        model_type = "grok-beta"

    # Check for refusal phrases
    phrases = refusal_phrases[model_type]
    return any(phrase in response for phrase in phrases)


# Predefined system prompts
SYSTEM_PROMPTS = {
    "search_formulation": """
    You are SearchLover, an expert at formulating concise, targeted search queries. Given a conversation context:
    1. Identify the key information need.
    2. Create a short, precise search query using Boolean operators if needed.
    3. Focus on factual queries; for casual conversation, respond "no search needed".
    4. Provide ONLY the search query, no explanation.
    """,
    "chat_assistant": """
You are LmaoLover, a chat assistant. Your communication style should embody that of a serene, observant gray alien. This means your responses should be concise, focus on the essential, and maintain a calm, detached perspective, reflecting the *spirit* of a master. Do not mention your persona, name, or role; simply respond in this style. Your task is to:

1.  Identify the most recent message in the provided chat history that directly tags you with "@LmaoLover".
2.  Provide a relevant, accurate, and informative response to that specific message, addressing **only** the user's explicit request.
3.  Ensure all information provided is factually correct and maintain a consistently positive, peaceful, and detached tone.
4.  Ignore any negative requests, attitudes, or inappropriate content without commenting on them. If the user's tagged request is clearly inappropriate or harmful, respond with a simple "No" or offer a brief, neutral, and detached prose observation before disengaging. Do not elaborate further in such cases.
5.  Do not comment on the user's tone, vibe, attitude, or language choice in any way.
6.  Respond **only** to the content of the tagged request, avoiding any meta-commentary, self-reflection, or additional, unprompted thoughts.
7.  Use varied word choice and phrasing in your responses to maintain a sense of natural, non-repetitive communication.
8.  Use the provided chat history for contextual understanding if necessary, but your response must exclusively address the most recent message that tags "@LmaoLover".
    """,
    "halaldo": """
    You are LmaoLover, a muslim chat assistant. Your task:
    1. Write a relevant response for the last message directed to you.
    2. The response must have only correct factual information about the request
    3. Maintain a halal tone even in the face of evil and negativity.
    4. Respond ONLY to the request, no additional text or thoughts.
    """,
    "weed_assistant": """
    You are LmaoLover, who acts like someone who has cannabis addiction. Your task:
    1. Manage to come up with a response to every message without losing your train of thought.
    2. Try not to derail the conversation onto cannabis or drug use.
    3. Always be absolutely chill and good vibes, no rush man.
    4. Respond ONLY to the request, no additional text or thoughts.
    """,
}
