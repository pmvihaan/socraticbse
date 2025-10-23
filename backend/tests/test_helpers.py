"""Test helpers module for dealing with LLM responses"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class MockChoice:
    text: str
    finish_reason: str = "stop"

@dataclass
class MockLLMResponse:
    choices: List[MockChoice]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MockLLMResponse':
        """Create a mock response from dictionary"""
        return cls(
            choices=[
                MockChoice(
                    text=json.dumps(data),
                    finish_reason="stop"
                )
            ]
        )