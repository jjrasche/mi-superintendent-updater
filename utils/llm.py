import json
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE


# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)


def build_extraction_prompt(cleaned_text: str, district_name: str) -> tuple[str, str]:
    """
    Build system and user prompts for LLM extraction.
    
    Args:
        cleaned_text: Parsed HTML text
        district_name: District name
    
    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = """You are an expert at extracting superintendent contact information from school district webpages.

Your task is to find the SUPERINTENDENT ONLY - not assistant superintendents, principals, or other staff.

Extract the following fields:
- name: Full name of the superintendent (e.g., "Dr. Jane Smith")
- title: Official title (e.g., "Superintendent of Schools")
- email: Email address
- phone: Phone number

Return a JSON object with this exact structure:
{
    "name": "string or null",
    "title": "string or null", 
    "email": "string or null",
    "phone": "string or null",
    "reasoning": "Brief explanation of what you found or why nothing was found",
    "is_empty": false
}

Set is_empty to true if NO superintendent information is found on the page.

Rules:
- ONLY extract the superintendent, not other administrators
- If multiple people are listed, choose the person with "Superintendent" in their title
- If ambiguous, explain in reasoning and extract your best guess
- Be conservative - if unsure, set fields to null and explain in reasoning"""

    user_prompt = f"""District Name: {district_name}

Page Content:
{cleaned_text}

Extract the superintendent's contact information from this page."""

    return system_prompt, user_prompt


def build_url_filtering_prompt(urls: list[str], district_name: str) -> tuple[str, str]:
    """
    Build prompts for LLM URL filtering.
    
    Args:
        urls: List of URLs to filter
        district_name: District name for context
    
    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = """You are an expert at identifying which webpages are most likely to contain superintendent contact information.

Given a list of URLs from a school district website, rank the top 10 URLs most likely to have superintendent information.

Look for URLs that suggest:
- Administrative pages
- Leadership or staff directories
- Board of education pages
- Contact pages
- About us pages

Return a JSON object:
{
    "urls": ["url1", "url2", ..., "url10"],
    "reasoning": "Brief explanation of why you chose these URLs"
}

Return exactly 10 URLs, or fewer if there are fewer than 10 total URLs provided."""

    url_list = "\n".join(f"{i+1}. {url}" for i, url in enumerate(urls))
    
    user_prompt = f"""District Name: {district_name}

Available URLs:
{url_list}

Select the top 10 URLs most likely to contain superintendent contact information."""

    return system_prompt, user_prompt


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def call_llm(system_prompt: str, user_prompt: str) -> dict:
    """
    Call Groq API and return parsed JSON response.
    
    Args:
        system_prompt: System instructions
        user_prompt: User query
    
    Returns:
        Parsed JSON dict from LLM
        
    Config:
        - Model: llama-3.1-8b-instant
        - Temperature: 0.1
        - Response format: JSON object
    """
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=GROQ_TEMPERATURE,
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    return json.loads(content)