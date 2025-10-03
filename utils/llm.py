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
            model="llama-3.3-70b-versatile",
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

def llm_pick_best_urls(district_name: str, url_contexts: list[dict]) -> list[str]:
    """LLM picks best URLs based on actual page content"""
    context_list = []
    for i, ctx in enumerate(url_contexts, 1):
        headings_str = ", ".join(ctx['headings'][:3]) if ctx['headings'] else "none"
        context_list.append( f"{i}. URL: {ctx['url']}\n" f"   Title: {ctx['title']}\n" f"   Headings: {headings_str}" )
    contexts = "\n\n".join(context_list)
    system_prompt = """You are an expert at analyzing school district websites to find superintendent contact information.\n\nYour task: Pick the top 3-5 URLs most likely to contain the superintendent's name, email, and phone number.\n\nLook for: administration pages, leadership bios, staff directories, superintendent pages.\nAvoid: board policies, transparency reports, FOIA pages, news articles.\n\nReply ONLY with valid JSON in this format:\n{"selected_urls": ["url1", "url2", "url3"]}"""
    user_prompt = f"""District: {district_name}\n\nI need to find the current superintendent's contact information. Here are candidate pages with their titles and headings:\n\n{contexts}"""
    response = client.chat.completions.create(model="llama-3.1-8b-instant", temperature=0.1, max_tokens=500, response_format={"type": "json_object"}, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
    content = response.choices[0].message.content.strip()
    result = json.loads(content)
    return result["selected_urls"][:5]

def llm_filter_urls_by_path(district_name: str, urls: list[str]) -> list[str]:
    """Quick LLM filter based only on URL paths"""
    url_list = '\n'.join(f"{i+1}. {url}" for i, url in enumerate(urls[:100]))
    system_prompt = """You filter URLs to find pages likely containing superintendent contact info.\nLook for: /admin, /leadership, /superintendent, /staff, /about, /contact, /directory\nAvoid: /news, /calendar, /sports, /lunch, /events, /students, /parents\nReply ONLY with valid JSON: {"top_urls": ["url1", "url2", ...]}"""
    user_prompt = f"""District: {district_name}\n\nPick the top 20 URLs most likely to have the superintendent's contact information:\n\n{url_list}"""
    response = client.chat.completions.create(model="llama-3.1-8b-instant", temperature=0.1, max_tokens=500, response_format={"type": "json_object"}, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
    content = response.choices[0].message.content.strip()
    result = json.loads(content)
    return result["top_urls"][:20]


def llm_get_json(prompts: list[str], model: str = "llama-3.1-8b-instant") -> dict:
    messages = [
        {"role": "system" if i == 0 else "user", "content": prompt}
        for i, prompt in enumerate(prompts)
    ]
    response = client.chat.completions.create( model=model, temperature=0.1, response_format={"type": "json_object"}, messages=messages )
    return json.loads(response.choices[0].message.content.strip())