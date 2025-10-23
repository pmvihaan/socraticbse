import unittest
from unittest.mock import patch, Mock
import json
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm_client import send_prompt, generate_socratic_prompt, parse_llm_question, LLMError
from backend.backend import app
from fastapi.testclient import TestClient

class TestLLMIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Mock question response
        self.mock_question_response = json.dumps({
            "question": "What is 2+2?",
            "type": "elicitation",
            "hint": "Try counting on your fingers",
            "follow_up": "Can you explain your reasoning?"
        })

        # Mock evaluation response
        self.mock_evaluation_response = json.dumps({
            "is_correct": True,
            "feedback": "Great job! The answer is correct."
        })

        # Mock hint response  
        self.mock_hint_response = json.dumps({
            "hint": "Try breaking down the problem into smaller steps."
        })

        # Mock LLM response
        self.mock_llm_response = {
            "choices": [{
                "text": json.dumps({
                    "question": "What is 2+2?",
                    "feedback": "Good attempt, keep going",
                    "next_question": {
                        "question": "What is 3+3?",
                        "type": "challenge" 
                    }
                }),
                "finish_reason": "stop"
            }]
        }
        
        # Start a test session
        response = self.client.post(
            "/session/start",
            json={
                "user_id": "test_user",
                "class_grade": 9,
                "subject": "Mathematics",
                "concept_title": "Addition"
            }
        )
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        self.test_session_id = response.json()["session_id"]
    @patch('llm_client.requests.post')
    def test_llm_client_send_prompt(self, mock_post):
        """Test that send_prompt returns text response"""
        mock_post.return_value.json.return_value = self.mock_llm_response
        
        response = send_prompt("Test prompt")
        
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        mock_post.assert_called_once()

    def test_generate_socratic_prompt(self):
        """Test Socratic prompt generation"""
        prompt = generate_socratic_prompt(
            concept_title="Addition",
            class_grade=9,
            subject="Mathematics"
        )
        self.assertIsInstance(prompt, str)
        self.assertIn("Addition", prompt)
        self.assertIn("Mathematics", prompt)
        self.assertIn("9", prompt)

    def test_parse_llm_question(self):
        """Test parsing LLM JSON response"""
        test_response = json.dumps({
            "question": "What is 2+2?",
            "type": "elicitation",
            "hint": "Try counting",
            "follow_up": "Can you explain?"
        })
        
        result = parse_llm_question(test_response)
        self.assertEqual(result["question"], "What is 2+2?")
        self.assertEqual(result["type"], "elicitation")
        self.assertEqual(result["hint"], "Try counting")
        self.assertEqual(result["follow_up"], "Can you explain?")

    @patch('llm_client.requests.post')
    def test_hint_endpoint(self, mock_post):
        """Test that hint endpoint calls LLM and returns hint"""
        mock_response = {
            "choices": [{
                "text": json.dumps({
                    "hint": "Try breaking down the problem"
                }),
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value.json.return_value = mock_response
        
        response = self.client.get(
            f"/hint/{self.test_session_id}",
            params={
                "current_question": "What is 2+2?",
                "dialogue_history": json.dumps([])
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("hint", data)
        self.assertTrue(len(data["hint"]) > 0)

    @patch('llm_client.requests.post')
    def test_retry_endpoint(self, mock_post):
        """Test that retry endpoint generates new question"""
        mock_post.return_value.json.return_value = self.mock_llm_response
        
        response = self.client.post(
            f"/retry/{self.test_session_id}",
            json={
                "current_concept": "addition",
                "dialogue_history": []
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("question", data)
        self.assertTrue(len(data["question"]) > 0)

    @patch('llm_client.requests.post')
    def test_skip_endpoint(self, mock_post):
        """Test that skip endpoint moves to next question"""
        mock_post.return_value.json.return_value = self.mock_llm_response
        
        response = self.client.post(
            f"/skip/{self.test_session_id}",
            json={
                "current_concept": "addition",
                "dialogue_history": []
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("question", data)
        self.assertTrue(len(data["question"]) > 0)

    @patch('llm_client.requests.post')
    def test_answer_endpoint(self, mock_post):
        """Test answer endpoint with LLM evaluation"""
        mock_response = {
            "choices": [{
                "text": json.dumps({
                    "is_correct": True,
                    "feedback": "Great job!",
                    "next_question": {
                        "question": "What is 3+3?",
                        "type": "elicitation",
                        "hint": "",
                        "follow_up": ""
                    }
                }),
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value.json.return_value = mock_response
        
        response = self.client.post(
            "/session/turn",
            json={
                "session_id": self.test_session_id,
                "current_question": "What is 2+2?",
                "user_answer": "4",
                "dialogue_history": []
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("is_correct", data)
        self.assertIn("feedback", data)
        self.assertIn("next_question", data)

    @patch('llm_client.requests.post')
    def test_reflection_endpoint(self, mock_post):
        """Test reflection generation"""
        mock_response = {
            "choices": [{
                "text": "Here's your progress reflection",
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value.json.return_value = mock_response
        
        response = self.client.get(
            f"/reflection/{self.test_session_id}",
            params={
                "dialogue_history": json.dumps([]),
                "progress": json.dumps({
                    "questions_answered": 5,
                    "total_questions": 10,
                    "concepts_covered": ["addition"]
                })
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reflection", data)
        self.assertTrue(len(data["reflection"]) > 0)

    @patch('llm_client.requests.post')
    def test_llm_error_handling(self, mock_post):
        """Test error handling when LLM service is unavailable"""
        mock_post.side_effect = Exception("LLM service unavailable")
            
        # Create a session first
        session_response = self.client.post(
            "/session/start",
            json={
                "user_id": "test_user",
                "class_grade": 9,
                "subject": "Mathematics",
                "concept_title": "Addition"
            }
        )
        session_id = session_response.json()["session_id"]
            
        response = self.client.get(f"/hint/{session_id}")
            
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("detail", data)

    @patch('llm_client.requests.post')
    def test_progress_tracking(self, mock_post):
        """Test progress tracking in session"""
        # Mock a series of interactions to verify progress updates
        responses = []

        # Mock first answer
        first_response = {
            "choices": [{
                "text": json.dumps({
                    "is_correct": True,
                    "feedback": "Correct!",
                    "next_question": {
                        "question": "What is 3+3?",
                        "type": "elicitation",
                        "hint": "",
                        "follow_up": ""
                    }
                }),
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value.json.return_value = first_response
        
        responses.append(self.client.post(
            "/session/turn",
            json={
                "session_id": self.test_session_id,
                "current_question": "What is 2+2?",
                "user_answer": "4",
                "dialogue_history": []
            }
        ))
        
        # Mock second answer
        second_response = {
            "choices": [{
                "text": json.dumps({
                    "is_correct": True,
                    "feedback": "Excellent!",
                    "next_question": {
                        "question": "What is 4+4?",
                        "type": "elicitation",
                        "hint": "",
                        "follow_up": ""
                    }
                }),
                "finish_reason": "stop"
            }]
        }
        mock_post.return_value.json.return_value = second_response
        
        responses.append(self.client.post(
            "/session/turn",
            json={
                "session_id": self.test_session_id,
                "current_question": "What is 3+3?",
                "user_answer": "6",
                "dialogue_history": []
            }
        ))        # Verify progress tracking
        for resp in responses:
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("progress", data)
            progress = data["progress"]
            self.assertIn("questions_answered", progress)
            self.assertIn("total_questions", progress)
            self.assertIn("concepts_covered", progress)
            self.assertIsInstance(progress["questions_answered"], int)
            self.assertGreater(progress["questions_answered"], 0)
            self.assertIsInstance(progress["concepts_covered"], list)

    def test_invalid_json_response(self):
        """Test handling of invalid JSON responses from LLM"""
        invalid_response = "Not a JSON response"
        
        with self.assertRaises(LLMError):
            parse_llm_question(invalid_response)
            
    def test_missing_required_fields(self):
        """Test handling of JSON responses missing required fields"""
        incomplete_response = json.dumps({
            "type": "elicitation",
            "hint": "Try counting"
            # Missing required 'question' field
        })
        
        with self.assertRaises(LLMError):
            parse_llm_question(incomplete_response)

if __name__ == '__main__':
    unittest.main()