import json
from pathlib import Path
from typing import TypeVar, Type
from jinja2 import Environment, FileSystemLoader
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel, ValidationError
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """Generic LLM client with template-based prompts and Pydantic validation"""

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
        self.env = Environment(loader=FileSystemLoader('prompts'))

    # Core operations
    load_template = lambda self, name: self.env.get_template(f'{name}.txt').render

    split_prompts = lambda self, rendered: (
        lambda parts: (parts[0].strip(), parts[1].strip())
    )(rendered.split('---USER_PROMPT---'))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_api(self, system_prompt: str, user_prompt: str) -> dict:
        """Call Groq API with retry logic"""
        if not self.client:
            raise ValueError("GROQ_API_KEY not set")

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=GROQ_TEMPERATURE,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def call(self, template_name: str, response_model: Type[T], **variables) -> T:
        """
        Load template, call LLM, validate response.

        Args:
            template_name: Name of template file (without .txt)
            response_model: Pydantic model to validate response
            **variables: Template variables to render

        Returns:
            Validated Pydantic model instance

        Example:
            result = client.call('superintendent_extraction',
                                SuperintendentExtraction,
                                text=html,
                                district_name=name)
        """
        try:
            # Load and render template
            render = self.load_template(template_name)
            rendered = render(**variables)
            system_prompt, user_prompt = self.split_prompts(rendered)

            # Call API
            raw_response = self._call_api(system_prompt, user_prompt)

            # Validate and return
            return response_model(**raw_response)

        except ValidationError as e:
            print(f"[LLM VALIDATION ERROR] Response doesn't match {response_model.__name__}: {e}")
            raise
        except Exception as e:
            print(f"[LLM ERROR] {type(e).__name__}: {str(e)}")
            raise


# Singleton instance
_client = None
get_client = lambda: globals().__setitem__('_client', LLMClient()) or _client if _client is None else _client
