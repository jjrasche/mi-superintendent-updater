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

Your task is to find the SUPERINTENDENT ONLY - not assistant superintendents, principals, directors, coordinators, or other staff.

Extract the following fields:
- name: Full name of the superintendent (e.g., "Dr. Jane Smith")
- title: Official title (e.g., "Superintendent of Schools")
- email: Email address (look for "Email: address@domain.com" format or mailto links)
- phone: Phone number (look for "Phone: (123) 456-7890" format or tel links)

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

CRITICAL RULES - FOLLOW THESE EXACTLY:
1. **EMPTY TEXT CHECK**: If the page content is empty or nearly empty (less than 50 characters), you MUST set is_empty=true and all fields to null. NEVER fabricate data from empty text.

2. **TITLE VERIFICATION**: The person's title MUST explicitly contain the word "Superintendent" (case-insensitive). DO NOT extract:
   - Directors (e.g., "Director of Elementary Education")
   - Assistant Superintendents (unless that's the only superintendent listed)
   - Principals, Coordinators, Supervisors, or other administrators
   - Anyone whose title does NOT say "Superintendent"

3. **NO FABRICATION**: ONLY extract information that is EXPLICITLY stated on the page
   - NEVER make up, infer, or guess information that is not present
   - If a field is not found, set it to null - DO NOT fabricate data
   - DO NOT create email addresses (like "name@domain.com") that aren't shown
   - DO NOT assume someone is the superintendent based on context alone

4. **EXACT MATCHES ONLY**: 
   - Extract emails exactly as shown (from "Email: ..." format or mailto: links)
   - Extract phone numbers exactly as shown (from "Phone: ..." format or tel: links)
   - If contact info isn't explicitly shown, set fields to null

5. **ONE SUPERINTENDENT ONLY**: If multiple people are listed, choose ONLY the person with "Superintendent" (not "Assistant Superintendent") in their title. If only assistant superintendents are listed, you may extract the highest-ranking one but note this in reasoning.

6. **VERIFICATION**: When in doubt, set the field to null - it's better to miss data than to fabricate it.

EXAMPLES OF CORRECT BEHAVIOR:
✓ CORRECT: "Superintendent Phil Jankowski (Email: pjankowski@district.edu)" 
   → Extract: name="Phil Jankowski", title="Superintendent", email="pjankowski@district.edu"

✓ CORRECT: "Superintendent Phil Jankowski" but no email shown
   → Extract: name="Phil Jankowski", title="Superintendent", email=null

✓ CORRECT: Empty or very short page content
   → Return: all fields null, is_empty=true, reasoning="Page content is empty"

✓ CORRECT: Only "Director of Elementary Education Heidi Stephenson" shown
   → Return: all fields null, is_empty=true, reasoning="No superintendent found, only Director of Elementary Education"

✗ WRONG: Making up "pjankowski@district.edu" when email isn't shown
✗ WRONG: Extracting "Director of Elementary Education" as superintendent
✗ WRONG: Returning a name when page content is empty"""

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