"""
LLM Client module for interacting with Groq API.
Handles prompt sending, response parsing, and error handling.
Includes utilities for generating educational prompts.
"""

from typing import Optional, Dict, Any, Union
import os
import requests
from dotenv import load_dotenv
import json
from typing import Dict

# Load environment variables
load_dotenv()

# Template for generating Socratic questions
LLM_PROMPT_TEMPLATE = """
You are an intelligent Socratic tutor for CBSE students.

Concept: {concept_title}
Subject: {subject}
Class: {class_grade}

Rules:
1. Always ask the student a Socratic-style question that encourages reasoning.
2. Include one follow-up question if the student might need further guidance.
3. Provide hints only if requested.
4. Adapt your question style to the subject:
   - Biology: focus on processes, cause-effect, and real-life examples.
   - Physics: relate concepts to formulas, experiments, and real-world phenomena.
   - Mathematics: ask stepwise problem-solving questions; focus on logical reasoning.
   - Chemistry: emphasize reactions, structures, and mechanisms.

Generate output as JSON:
{{
  "question": "<Your Socratic question here>",
  "type": "elicitation",
  "hint": "<Optional hint or leave blank>",
  "follow_up": "<Optional follow-up question or leave blank>"
}}
"""

def generate_socratic_prompt(concept_title: str, class_grade: int, subject: str) -> str:
    """
    Generate a context-specific prompt for Socratic questioning based on subject and topic.
    
    Args:
        concept_title (str): The specific concept or topic to generate questions for
        class_grade (int): The class/grade level (9-12)
        subject (str): The subject area (Physics, Chemistry, Biology, Mathematics)
        
    Returns:
        str: A formatted prompt for the LLM using the template
    """
    return LLM_PROMPT_TEMPLATE.format(
        concept_title=concept_title,
        subject=subject,
        class_grade=class_grade
    )

# Configuration from environment
API_KEY: str = os.getenv("GROQ_API_KEY", "")
MODEL: str = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
BASE_URL: str = os.getenv("GROQ_API_URL", "https://api.groq.com/v1")

class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass

def _validate_config() -> None:
    """
    Validate that required environment variables are set.
    
    Raises:
        LLMError: If any required configuration is missing.
    """
    if not API_KEY:
        raise LLMError("GROQ_API_KEY not found in environment variables")
    if not BASE_URL:
        raise LLMError("GROQ_API_URL not found in environment variables")

def _build_headers() -> Dict[str, str]:
    """
    Build headers for Groq API requests.
    
    Returns:
        Dict[str, str]: Headers dictionary including authorization and content type.
    """
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

def parse_llm_question(response_text: str) -> Dict[str, str]:
    """
    Parse the LLM's JSON response into a structured question format.
    
    Args:
        response_text (str): Raw text response from the LLM
        
    Returns:
        Dict[str, str]: Parsed question data with keys:
            - question: The main Socratic question
            - type: Question type (usually "elicitation")
            - hint: Optional hint text
            - follow_up: Optional follow-up question
            
    Raises:
        LLMError: If response parsing fails
    """
    try:
        # Clean up the response text to ensure valid JSON
        clean_text = response_text.strip()
        if not clean_text.startswith("{"):
            # Extract JSON if it's embedded in other text
            start = clean_text.find("{")
            end = clean_text.rfind("}") + 1
            if start >= 0 and end > start:
                clean_text = clean_text[start:end]
            else:
                raise LLMError("No valid JSON found in response")
        
        # Parse the JSON
        data = json.loads(clean_text)
        
        # Validate required fields
        if "question" not in data:
            raise LLMError("Response missing required 'question' field")
            
        # Ensure all fields exist with defaults
        return {
            "question": data["question"],
            "type": data.get("type", "elicitation"),
            "hint": data.get("hint", ""),
            "follow_up": data.get("follow_up", "")
        }
    except json.JSONDecodeError as e:
        raise LLMError(f"Failed to parse LLM response as JSON: {e}")
    except Exception as e:
        raise LLMError(f"Error processing LLM response: {e}")

def _parse_response(response: requests.Response) -> str:
    """
    Parse the response from Groq API and extract the generated text.
    
    Args:
        response (requests.Response): Response object from the API call.
        
    Returns:
        str: Generated text from the model.
        
    Raises:
        LLMError: If response parsing fails or API returns an error.
    """
    try:
        data = response.json()
        if "choices" not in data or not data["choices"]:
            raise LLMError("Invalid response format from API")
        # For chat completions, the content is in choices[0].message.content
        if "message" in data["choices"][0] and "content" in data["choices"][0]["message"]:
            return data["choices"][0]["message"]["content"].strip()
        # Fallback to text field for backward compatibility
        elif "text" in data["choices"][0]:
            return data["choices"][0]["text"].strip()
        else:
            raise LLMError("No content found in response")
    except json.JSONDecodeError:
        raise LLMError("Failed to parse API response")
    except KeyError as e:
        raise LLMError(f"Unexpected response structure: {e}")

def send_prompt(prompt: str, max_tokens: int = 512) -> str:
    """
    Send a prompt to the Groq API and get the generated response.
    
    Args:
        prompt (str): The prompt text to send to the model.
        max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 512.
        
    Returns:
        str: The generated text response.
        
    Raises:
        LLMError: If API call fails, configuration is invalid, or response parsing fails.
        requests.RequestException: If network request fails.
    """
    # Validate configuration
    try:
        _validate_config()
    except LLMError:
        # Return empty string if config is invalid - allows graceful fallback
        return ""
    
    # Prepare request
    endpoint = f"{BASE_URL}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "top_p": 1,
        "stream": False
    }
    
    try:
        # Make API call
        response = requests.post(
            endpoint,
            headers=_build_headers(),
            json=payload,
            timeout=30
        )
        
        # Check for HTTP errors
        response.raise_for_status()
        
        # Parse and return response
        return _parse_response(response)
        
    except (requests.RequestException, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        # Log error and return empty string for graceful fallback
        print(f"LLM service unavailable: {str(e)}")
        return ""
    except Exception as e:
        # Log unexpected errors and return empty for graceful fallback
        print(f"Unexpected LLM error: {str(e)}")
        return ""