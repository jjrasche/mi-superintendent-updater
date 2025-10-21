import json
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE


# Initialize Groq client
_client = None

def get_client():
    """Get or create Groq client (lazy initialization)."""
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable must be set")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client

def build_extraction_prompt(cleaned_text: str, district_name: str) -> tuple[str, str]:
    """
    Build system and user prompts for LLM extraction.
    
    Args:
        cleaned_text: Parsed HTML text
        district_name: District name
    
    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = """You are a data extraction specialist. Extract superintendent contact information from school district webpages.

OUTPUT FORMAT:
Return valid JSON with this exact structure:
{
    "name": "string or null",
    "title": "string or null",
    "email": "string or null",
    "phone": "string or null",
    "reasoning": "brief explanation",
    "is_empty": false
}

EXTRACTION RULES (in priority order):

1. SUPERINTENDENT ONLY
   - Title MUST explicitly contain the word "Superintendent"
   - DO NOT extract: Assistant Superintendent, Director, Principal, Coordinator, or any other role
   - Exception: If ONLY Assistant Superintendent is listed, extract them and note in reasoning

2. EXPLICIT DATA ONLY
   - Extract ONLY information directly stated on the page
   - Look for patterns like "Email: address@domain.com" or mailto: links
   - Look for patterns like "Phone: (123) 456-7890" or tel: links
   - NEVER infer, guess, or construct data not shown

3. EMPTY CONTENT HANDLING
   - If page content is empty or under 50 characters → set is_empty=true, all fields null
   - If no superintendent information found → set is_empty=true, all fields null
   - If person found but title lacks "Superintendent" → set is_empty=true, all fields null

4. FIELD REQUIREMENTS
   - name: Required if superintendent found
   - title: Required if superintendent found (must contain "Superintendent")
   - email: Optional - only if explicitly shown
   - phone: Optional - only if explicitly shown

EXAMPLES:

✓ CORRECT:
Input: "Superintendent Dr. Jane Smith | Email: jsmith@district.edu | Phone: (555) 123-4567"
Output: {"name": "Dr. Jane Smith", "title": "Superintendent", "email": "jsmith@district.edu", 
         "phone": "(555) 123-4567", "reasoning": "Found superintendent with complete contact info", "is_empty": false}

✓ CORRECT:
Input: "Superintendent Phil Jankowski [mailto link: pjankowski@abs.misd.net]"
Output: {"name": "Phil Jankowski", "title": "Superintendent", "email": "pjankowski@abs.misd.net",
         "phone": null, "reasoning": "Found superintendent with email from mailto link", "is_empty": false}

✓ CORRECT:
Input: "Director of Elementary Education: Sarah Johnson"
Output: {"name": null, "title": null, "email": null, "phone": null,
         "reasoning": "Found Director role, not Superintendent", "is_empty": true}

✗ WRONG:
Input: "Superintendent John Doe serves our district"
Output: {"name": "John Doe", "title": "Superintendent", "email": "jdoe@district.edu", ...}
Reason: NEVER create email addresses that aren't explicitly shown

✗ WRONG:  
Input: "Assistant Superintendent Mary Brown oversees curriculum"
Output: {"name": "Mary Brown", "title": "Assistant Superintendent", ...}
Reason: Only extract Assistant Superintendent if NO regular Superintendent is listed"""

    user_prompt = f"""District Name: {district_name}

Page Content:
{cleaned_text}

Extract the superintendent's contact information following the rules exactly."""

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
    try:
        client = get_client()
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
    except Exception as e:
        print(f"[LLM ERROR] {type(e).__name__}: {str(e)}")
        raise