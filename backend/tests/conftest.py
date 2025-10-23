"""
This module provides test fixtures for the backend tests.
"""

import pytest
import os
import json
import tempfile
from pathlib import Path

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment with mock concept graph and session store"""
    # Create temporary files
    temp_dir = tempfile.mkdtemp()
    concept_graph_path = os.path.join(temp_dir, "seed_concept_graph.json")
    sessions_path = os.path.join(temp_dir, "sessions_store.json")
    
    # Mock concept graph
    mock_concept_graph = [{
        "title": "Addition",
        "class_grade": 9,
        "subject": "Mathematics",
        "description": "Basic arithmetic addition",
        "keywords": ["add", "plus", "sum"],
        "questions": [
            {
                "type": "elicitation",
                "question": "What is 2+2?",
                "hint": "Try counting fingers",
                "follow_up": "Can you explain how you got this?"
            }
        ]
    }]
    
    # Write mock data
    with open(concept_graph_path, "w") as f:
        json.dump(mock_concept_graph, f)
    
    with open(sessions_path, "w") as f:
        json.dump({}, f)
    
    # Mock environment variables
    monkeypatch.setenv("GROQ_API_KEY", "mock_api_key")
    monkeypatch.setenv("GROQ_MODEL", "mixtral-8x7b-32768")
    monkeypatch.setenv("GROQ_API_URL", "https://api.groq.com/v1")
    monkeypatch.setenv("USE_JSON_PERSISTENCE", "true")
    
    # Update paths in backend module
    from backend import backend as backend_module
    monkeypatch.setattr(backend_module, "SEED_PATH", concept_graph_path)
    monkeypatch.setattr(backend_module, "SESSIONS_PATH", sessions_path)
    
    yield
    
    # Cleanup
    Path(concept_graph_path).unlink(missing_ok=True)
    Path(sessions_path).unlink(missing_ok=True)
    Path(temp_dir).rmdir()