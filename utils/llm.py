import json
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def llm_rank_urls(district_name: str, urls: list[str]) -> list[str]:
    """Use LLM to rank URLs by relevance"""
    url_list = '\n'.join(f"{i+1}. {url}" for i, url in enumerate(urls[:20]))
    
    prompt = f"""District: {district_name}

URLs from sitemap:
{url_list}

Return the top 5 URLs most likely to have current superintendent contact information.
Look for pages like: administration, leadership, superintendent bio, staff directory.
Avoid: news articles, calendar, sports, lunch menus.

Reply ONLY with valid JSON in this exact format:
{{"ranked_urls": ["url1", "url2", "url3", "url4", "url5"]}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        # Try to extract JSON if wrapped in markdown
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        result = json.loads(content)
        return result["ranked_urls"][:5]
    except Exception as e:
        print(f"  LLM ranking failed: {e}")
        return urls[:5]  # Fallback to first 5
