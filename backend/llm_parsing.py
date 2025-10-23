"""Helper functions for parsing LLM responses"""
from typing import Dict, Any, Union
import json

class LLMParsingError(Exception):
    """Exception raised for errors parsing LLM responses"""
    pass

def parse_llm_response(response: Any) -> Dict[str, Any]:
    """Parse any response from LLM"""
    try:
        # Extract the raw text from various response formats
        if isinstance(response, (str, bytes)):
            text = response
        elif isinstance(response, dict):
            if "choices" not in response:
                return response
            # Handle both chat completions and text completions
            if "message" in response["choices"][0] and "content" in response["choices"][0]["message"]:
                text = response["choices"][0]["message"]["content"]
            elif "text" in response["choices"][0]:
                text = response["choices"][0]["text"]
            else:
                raise LLMParsingError("No content found in response")
        elif hasattr(response, "choices"):
            if hasattr(response.choices[0], "message") and hasattr(response.choices[0].message, "content"):
                text = response.choices[0].message.content
            elif hasattr(response.choices[0], "text"):
                text = response.choices[0].text
            else:
                raise LLMParsingError("No content found in response")
        else:
            raise LLMParsingError("Invalid response format")

        # Handle empty response
        if not text or not text.strip():
            raise LLMParsingError("Empty response from LLM")

        # Handle both direct JSON and JSON embedded in text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON if it's embedded in text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            raise LLMParsingError("Failed to parse response as JSON")
    except Exception as e:
        raise LLMParsingError(f"Failed to parse LLM response: {str(e)}")

def parse_llm_evaluation(response: Any) -> Dict[str, Any]:
    """Parse evaluation from LLM response"""
    result = parse_llm_response(response)
    
    # Validate required fields
    if "is_correct" not in result:
        raise LLMParsingError("Missing is_correct field in evaluation")
    if "feedback" not in result:
        raise LLMParsingError("Missing feedback field in evaluation")
        
    return result

def parse_llm_question(response: Any) -> Dict[str, Any]:
    """Parse question from LLM response"""
    result = parse_llm_response(response)
    
    # Validate required fields
    if "question" not in result:
        raise LLMParsingError("Missing question field in response")
    
    # Set default type if missing
    if "type" not in result:
        result["type"] = "elicitation"
        
    return result

def parse_llm_hint(response: Any) -> Dict[str, Any]:
    """Parse hint from LLM response"""
    result = parse_llm_response(response)
    
    # Validate required field
    if "hint" not in result:
        raise LLMParsingError("Missing hint field in response")
        
    return result