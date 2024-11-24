from logger import log_info, log_error
from together import Together

def generate_response(prompt: str) -> str:
    """
    Interacts with Together AI to generate a response based on the given prompt.

    Args:
        prompt (str): The input prompt for Together AI.

    Returns:
        str: The AI-generated response.
    """
    try:
        log_info(f"Sending prompt to Together AI: {prompt}")
        
        # Initialize Together AI client
        together = Together()

        # Request completion from Together AI without streaming
        response = together.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
            messages=[{"role": "user", "content": prompt}],
        )

        # Collect and return the response
        roast = response.choices[0].message.content
        return roast.strip()
    except Exception as e:
        log_error(f"Error interacting with Together AI: {e}")
        raise Exception("Failed to generate response from Together AI")


def generate_roast(style: str, tweet_text: str) -> str:
    """
    Generates a roast for the given tweet using Together AI.

    Args:
        style (str): The style of the roast (e.g., "savage", "Shakespeare").
        tweet_text (str): The content of the tweet to roast.

    Returns:
        str: The generated roast.
    """
    try:
        log_info(f"Generating roast in '{style}' style for tweet: {tweet_text}")
        
        # Construct the prompt for Together AI
        prompt = (
            f"Roast this tweet in the style of {style}: '{tweet_text}'. "
            "Keep it concise (1-2 sentences) and witty."
        )

        # Use Together AI to generate the roast
        roast = generate_response(prompt)
        log_info(f"Generated roast: {roast}")
        return roast
    except Exception as e:
        log_error(f"Error generating roast: {e}")
        raise Exception("Failed to generate roast")
