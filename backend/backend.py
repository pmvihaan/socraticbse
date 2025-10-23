# backend/backend.py

# 1️⃣ Imports
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import os
import time
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# 2️⃣ Local imports
from db import get_db, init_db, Session as DBSession
from persistence import PersistenceLayer
from llm_client import send_prompt, LLMError, generate_socratic_prompt
from llm_parsing import parse_llm_question, parse_llm_evaluation, parse_llm_hint

# 3️⃣ Paths and configuration
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_PATH = os.path.join(BASE_DIR, "seed_concept_graph.json")
SESSIONS_PATH = os.path.join(BASE_DIR, "sessions_store.json")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
USE_JSON_PERSISTENCE = os.getenv("USE_JSON_PERSISTENCE", "true").lower() == "true"
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"

# Initialize persistence layer
persistence = PersistenceLayer(use_json=USE_JSON_PERSISTENCE, json_path=SESSIONS_PATH)

# Load concept graph with error handling
try:
    if not os.path.exists(SEED_PATH):
        raise FileNotFoundError(f"Concept graph file not found: {SEED_PATH}")
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        concept_graph: List[Dict[str, Any]] = json.load(f)
except Exception as e:
    print(f"Error loading concept graph: {e}")
    concept_graph = []  # Empty fallback for graceful degradation

# 4️⃣ FastAPI app
app = FastAPI(title="SocraticBSE Backend — SQLite + JSON Persistence")

# Use lifespan handler for startup/shutdown tasks (preferred over on_event)
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    init_db()
    yield
    # shutdown (noop for now)


app = FastAPI(title="SocraticBSE Backend — SQLite + JSON Persistence", lifespan=lifespan)

# 5️⃣ CORS - configured from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6️⃣ Models
class SessionStartRequest(BaseModel):
    user_id: str
    class_grade: int
    subject: str
    concept_title: str

class SessionStartResponse(BaseModel):
    session_id: str
    question_type: str
    question: str
    hint_level: int = 0

class DialogueTurnRequest(BaseModel):
    session_id: str
    user_answer: str

class DialogueTurnResponse(BaseModel):
    session_id: str
    question_type: str
    question: str
    hint_level: int = 0
    is_correct: bool = False
    feedback: str = ""
    progress: Dict[str, Any] = {}
    next_question: Optional[Dict[str, Any]] = None

class HintResponse(BaseModel):
    hint: str

class ReflectionResponse(BaseModel):
    session_id: str
    summary_text: str
    suggested_next_concepts: List[str]
    reflection: str
    focus_areas: List[str] = []

class ProgressResponse(BaseModel):
    questions_answered: int
    total_questions: int
    concepts_covered: List[str]
    avg_time_per_question: float = 0
    total_time: float = 0
    times_per_question: List[float] = []

class HintResponse(BaseModel):
    hint: str

# 7️⃣ Helpers for concept handling
def calculate_progress(session: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate progress metrics for a session with validation"""
    concept = session.get("current_concept", {})
    if not concept:
        return {
            "questions_answered": 0,
            "total_questions": 0,
            "concepts_covered": [],
            "percent_complete": 0,
            "is_complete": False
        }
        
    questions = concept.get("questions", [])
    total = len(questions)
    
    # Use the progress object from session which gets updated in persistence layer
    progress = session.get("progress", {})
    answered = progress.get("questions_answered", 0)
    
    # Calculate percentage complete and validate completion
    percent_complete = (answered / total * 100) if total > 0 else 0
    is_complete = answered >= total  # Only mark complete when all questions are done
    
    return {
        "questions_answered": answered,
        "total_questions": total,
        "concepts_covered": [concept["title"]],
        "percent_complete": percent_complete,
        "is_complete": is_complete
    }

def find_concept(class_grade: int, subject: str, title: str) -> Dict[str, Any]:
    """
    Find a concept in the concept graph by grade, subject, and title.
    
    Returns:
        Dict[str, Any]: Concept data with questions (either from seed or LLM-generated)
    """
    print(f"Looking for concept with class_grade={class_grade}, subject={subject}, title={title}")
    print(f"Available concepts: {concept_graph}")
    for c in concept_graph:
        if c.get("class") == class_grade and c.get("subject", "").lower() == subject.lower() and c.get("title", "").lower() == title.lower():
            print(f"Found matching concept: {c}")
            return c
    return None

def generate_llm_concept(base_concept: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a concept with LLM-powered questions while preserving the original concept structure.
    Falls back to seed questions if LLM is unavailable.
    
    Args:
        base_concept: Original concept data from seed
        
    Returns:
        Dict[str, Any]: Concept with dynamically generated questions or seed questions
    """
    if not USE_LLM:
        return base_concept
        
    try:
        # Generate subject-specific Socratic prompt
        prompt = generate_socratic_prompt(
            concept_title=base_concept['title'],
            class_grade=base_concept['class'],
            subject=base_concept['subject']
        )
        
        # Get questions from LLM
        response = send_prompt(prompt)
        
        # If LLM failed (empty response), fall back to seed
        if not response:
            return base_concept
            
        # Parse the response into questions
        questions = []
        for i, q in enumerate(response.strip().split("\n"), 1):
            if not q.strip():
                continue
            questions.append({
                "type": "elicitation",
                "question": q.strip(),
                "hints": [
                    f"Think about the key concepts involved.",
                    f"Consider cause and effect relationships.",
                    f"Try to explain it step by step."
                ]
            })
        
        # Use seed questions if no valid questions were generated
        if not questions:
            return base_concept
            
        # Create new concept with generated questions
        concept = base_concept.copy()
        concept["questions"] = questions
        concept["is_llm_generated"] = True
        print(f"🤖 AI-Generated questions for {concept['title']} using Groq API")
        return concept
        
    except Exception as e:
        # Log error and fallback to original concept
        print(f"LLM generation failed: {e}, falling back to seed questions")
        return base_concept

# 9️⃣ Dynamic hint generator (LLM-powered or rule-based)
def generate_dynamic_hint(session: Dict[str, Any]) -> str:
    """
    Generate a context-sensitive hint for the current question.
    
    If USE_LLM is True:
      - First tries predefined hints
      - Then generates contextual hints using LLM based on:
        * Current question
        * User's previous answer
        * Concept keywords and context
    
    If USE_LLM is False or on LLM failure:
      - Uses predefined hints if available
      - Falls back to rule-based hint generation based on:
        * Question type (why/what/how)
        * Answer length and keywords
        * Concept context
    """
    concept = session["current_concept"]
    idx = max(session.get("next_q_idx", 1) - 1, 0)
    questions = concept.get("questions", [])
    if idx < 0 or idx >= len(questions):
        return "No hints available."

    q = questions[idx]
    hints = q.get("hints", [])  # question-level hints from seed

    # 9.1 If predefined hints exist, consume them in order
    hl = session.get("hint_level", 0)
    if hl < len(hints):
        session["hint_level"] = hl + 1
        # Note: Session will be persisted when the hint is returned
        return hints[hl]

    # 9.2 Generate contextual hint
    dialogue = session.get("dialogue", [])
    user_turns = [d["text"] for d in dialogue if d["speaker"] == "User" and d["text"].strip()]
    last = user_turns[-1] if user_turns else ""
    last_len = len(last.strip())
    
    if USE_LLM:
        try:
            # Generate contextual hint using LLM
            context = (
                f"Given this question: '{q['question']}'\n"
                f"And this student answer: '{last}'\n"
                f"Generate a helpful hint that guides the student to think deeper without giving away the answer. "
                f"Consider these concept keywords: {', '.join(concept.get('keywords', []))}\n"
                "Keep the hint under 2 sentences."
            )
            hint = send_prompt(context, max_tokens=100)
            return hint
        except LLMError:
            # Fall back to rule-based hints on LLM failure
            pass
    
    # Rule-based hint generation (fallback)
    keywords = concept.get("keywords", [])
    lk = last.lower()
    found_kw = [k for k in keywords if k.lower() in lk]

    if last_len == 0:
        hint = "Try writing a short sentence explaining what you think, even if you're unsure."
    elif found_kw:
        hint = f"You mentioned {found_kw[0]}; can you explain how {found_kw[0]} connects to the process asked in the question?"
    elif "why" in q.get("question", "").lower():
        hint = "Think about cause and effect: what causes this to happen and why?"
    elif "what" in q.get("question", "").lower() or "define" in q.get("question", "").lower():
        hint = "Try to define the key term in your own words — what does it mean, step by step?"
    else:
        hint = "Try breaking the problem into smaller parts and describe one part at a time."

    # increment hint_level so future calls change behavior
    session["hint_level"] = session.get("hint_level", 0) + 1
    # Note: Session will be persisted when the hint is returned
    return hint

# 1️⃣0️⃣ Start session endpoint
@app.post("/session/start", response_model=SessionStartResponse)
def start_session(req: SessionStartRequest, db: Session = Depends(get_db)):
    concept = find_concept(req.class_grade, req.subject, req.concept_title)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # Generate LLM-powered concept if enabled
    if USE_LLM:
        concept = generate_llm_concept(concept)
        if concept.get("is_llm_generated"):
            print(f"🤖 Starting session with AI-generated questions for {concept['title']}")

    session_id = str(uuid.uuid4())
    persistence.create_session(db, session_id, req.user_id, concept)

    questions = concept.get("questions", [])
    if not questions:
        raise HTTPException(status_code=500, detail="Concept has no questions")
    first_q = questions[0]
    persistence.add_turn(db, session_id, "AI", first_q["question"])
    
    return SessionStartResponse(session_id=session_id, question_type=first_q.get("type","elicitation"), question=first_q.get("question",""), hint_level=0)

# 1️⃣1️⃣ Submit answer / next turn
@app.post("/session/turn", response_model=DialogueTurnResponse)
def session_turn(req: DialogueTurnRequest, db: Session = Depends(get_db)) -> DialogueTurnResponse:
    session = persistence.get_session(db, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    concept = session["current_concept"]
    questions = concept.get("questions", [])
    current_idx = session.get("next_q_idx", 1) - 1  # Get current question index
    
    if current_idx >= len(questions):
        # Already completed
        completion_message = (
            "🎉 Congratulations! You've completed this concept. "
            "Click 'Get Reflection' to see a summary of your responses and suggested next concepts."
        )
        return DialogueTurnResponse(
            session_id=req.session_id,
            question_type="completed",
            question=completion_message,
            hint_level=0,
            is_correct=True,
            progress=calculate_progress(session)
        )

    # Record user's answer for current question
    current_q = questions[current_idx]
    persistence.add_turn(db, req.session_id, "User", req.user_answer)
    
    # Move to next question
    next_idx = current_idx + 1
    next_q = None
    if next_idx < len(questions):
        next_q = questions[next_idx]
        persistence.add_turn(db, req.session_id, "AI", next_q["question"])
        persistence.update_next_q_idx(db, req.session_id, next_idx + 1)  # Set for next turn
        persistence.update_hint_level(db, req.session_id, 0)

    if USE_LLM and next_q:
        try:
            # Evaluate answer using LLM
            prompt = f"""You are a helpful CBSE tutor. Given:
Question: "{next_q['question']}"
Student Answer: "{req.user_answer}"

Evaluate if the answer is correct and provide feedback. Response as JSON:
{{
    "is_correct": true/false,
    "feedback": "<constructive feedback>"
}}"""
            response = send_prompt(prompt)
            evaluation = parse_llm_evaluation(response)
            
            is_correct = evaluation.get("is_correct", False)
            feedback = evaluation.get("feedback", "Keep thinking about this.")
        except (LLMError, ValueError, Exception) as e:
            # On any error, provide encouraging feedback based on answer length and content
            print(f"LLM evaluation failed: {e}")
            answer = req.user_answer.strip()
            if len(answer) > 100:
                feedback = "Thank you for the detailed response! Let's continue exploring this topic."
            elif len(answer) > 50:
                feedback = "You've put good thought into this. Let's keep building on these ideas."
            elif answer:
                feedback = "Thanks for trying! Every response helps us learn more."
            else:
                feedback = "Don't worry if you're unsure. Let's try the next question."
            is_correct = True  # Give benefit of doubt
    else:
        # Without LLM, simple presence check
        is_correct = bool(req.user_answer.strip())
        feedback = "Thanks for your answer."

    # Note: User answer was already recorded above, no need to add again
    
    # Refresh session to get updated progress
    session = persistence.get_session(db, req.session_id)
    progress = calculate_progress(session)

    # Get the next question in sequence (using the existing next_idx)
    if next_idx < len(questions):
        next_question = questions[next_idx]
    else:
        next_question = None

    # Handle case when there's no next question (session completed)
    if not next_q:
        completion_message = (
            "🎉 Congratulations! You've completed this concept. "
            "Click 'Get Reflection' to see a summary of your responses and suggested next concepts."
        )
        return DialogueTurnResponse(
            session_id=req.session_id,
            question_type="completed",
            question=completion_message,
            hint_level=0,
            is_correct=True,
            progress=progress
        )

    return DialogueTurnResponse(
        session_id=req.session_id,
        question_type=next_q.get("type", "elicitation"),
        question=next_q.get("question", ""),
        hint_level=0,
        is_correct=is_correct,
        feedback=feedback,
        next_question=next_question,  # Include next question if available
        progress=progress
    )

# 1️⃣2️⃣ Reflection
@app.get("/reflection/{session_id}", response_model=ReflectionResponse)
def get_reflection(session_id: str, db: Session = Depends(get_db)):
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    dialogue = session.get("dialogue", [])
    user_turns = [d["text"] for d in dialogue if d["speaker"]=="User" and d["text"].strip()]
    concept = session["current_concept"]
    suggested_next = concept.get("prerequisites", [])
    
    # Generate AI-powered reflection if LLM is enabled
    focus_areas = []
    if USE_LLM:
        try:
            # Create AI prompt for reflection analysis
            reflection_prompt = f"""You are an expert CBSE tutor analyzing a student's learning session.

Session Details:
- Concept: {concept['title']}
- Subject: {concept['subject']}
- Class: {concept.get('class', 'Unknown')}
- Student Responses: {user_turns}

Analyze the student's responses and provide:
1. A brief summary of their understanding
2. 3-5 specific focus areas for improvement
3. Suggested next concepts to explore

Respond as JSON:
{{
    "summary": "Brief summary of student's progress",
    "focus_areas": ["Area 1", "Area 2", "Area 3", "Area 4", "Area 5"],
    "next_concepts": ["Next concept 1", "Next concept 2"]
}}"""

            ai_response = send_prompt(reflection_prompt, max_tokens=300)
            if ai_response:
                import json
                try:
                    ai_data = json.loads(ai_response)
                    focus_areas = ai_data.get("focus_areas", [])
                    suggested_next = ai_data.get("next_concepts", suggested_next)
                    summary_text = ai_data.get("summary", f"During '{concept['title']}', you answered {len(user_turns)} questions.")
                    print(f"🤖 AI-Generated reflection for {concept['title']}")
                except json.JSONDecodeError:
                    # Fallback to basic reflection
                    summary_text = f"During '{concept['title']}', you answered {len(user_turns)} questions. Key ideas: {', '.join(user_turns) if user_turns else 'none'}."
            else:
                # Fallback to basic reflection
                summary_text = f"During '{concept['title']}', you answered {len(user_turns)} questions. Key ideas: {', '.join(user_turns) if user_turns else 'none'}."
        except Exception as e:
            print(f"AI reflection generation failed: {e}")
            # Fallback to basic reflection
            summary_text = f"During '{concept['title']}', you answered {len(user_turns)} questions. Key ideas: {', '.join(user_turns) if user_turns else 'none'}."
    else:
        # Basic reflection without AI
        summary_text = f"During '{concept['title']}', you answered {len(user_turns)} questions. Key ideas: {', '.join(user_turns) if user_turns else 'none'}."
    
    reflection = f"You've made good progress in {concept['title']}. " \
                f"Keep exploring the key concepts and asking questions. " \
                f"This helps build your understanding of {concept['subject']}."

    return ReflectionResponse(
        session_id=session_id,
        summary_text=summary_text,
        suggested_next_concepts=suggested_next,
        reflection=reflection,
        focus_areas=focus_areas  # Add focus_areas to response
    )

# 1️⃣3️⃣ Progress endpoint (accurate totals)
@app.get("/progress/{session_id}", response_model=ProgressResponse)
def get_progress(session_id: str, db: Session = Depends(get_db)):
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Calculate timing metrics
    times = session["progress"].get("times_per_question", [])
    avg_time = sum(times) / len(times) if times else 0
    total_time = sum(times) if times else 0  # Total time is sum of times per question
    
    # total_questions is stored in session.progress; we kept it updated on start and when queue grows
    return ProgressResponse(
        questions_answered=session["progress"].get("questions_answered",0),
        total_questions=session["progress"].get("total_questions",0),
        concepts_covered=session["progress"].get("concepts_covered",[]),
        avg_time_per_question=avg_time,
        total_time=total_time,
        times_per_question=times
    )

# 1️⃣4️⃣ Hint endpoint (LLM-powered)
@app.get("/hint/{session_id}", response_model=HintResponse)
def get_hint(session_id: str, db: Session = Depends(get_db)):
    """Get a hint for the current question"""
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    concept = session["current_concept"]
    hint_level = session.get("hint_level", 0)
    idx = max(session["next_q_idx"] - 1, 0)  # Get current question index
    questions = concept.get("questions", [])
    
    if idx >= len(questions):
        raise HTTPException(status_code=400, detail="No active question")
        
    current_q = questions[idx]
    
    if USE_LLM:
        try:
            # Generate contextual hint using LLM
            prompt = f"""You are a CBSE tutor. Given:
Question: "{current_q['question']}"
Hint Level: {hint_level}
Subject: {concept['subject']}
Class: {concept.get('class')}

Provide a hint that:
1. Gives guidance without revealing the answer
2. Is appropriate for hint level {hint_level} (more detailed at higher levels)
3. Uses Socratic questioning

Response as JSON:
{{
    "hint": "<your hint here>"
}}"""
            response = send_prompt(prompt)
            hint_data = parse_llm_hint(response)  # Use dedicated hint parser
            hint = hint_data["hint"]  # No need for fallback, parser ensures this exists
            
        except LLMError as e:
            # For LLM-specific failures we propagate a 500 so tests and clients
            # can detect service unavailability.
            print(f"LLM hint generation failed (LLMError): {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            # Non-LLM errors fallback to rule-based hints
            print(f"LLM hint generation failed (non-LLM): {e}")
            if "why" in current_q["question"].lower():
                hint = "Think about cause and effect: what leads to this result and why?"
            elif "how" in current_q["question"].lower():
                hint = "Try breaking this down into step-by-step instructions."
            elif "what" in current_q["question"].lower():
                hint = "Start by explaining the concept in your own words."
            else:
                hint = "Try breaking the problem into smaller parts and tackle each one."
    else:
        # Simple hint without LLM
        hint = "Try breaking the problem into smaller parts."
        
    persistence.update_hint_level(db, session_id, hint_level + 1)
    return HintResponse(hint=hint)

# 1️⃣5️⃣ Retry endpoint (LLM-powered rephrasing)
@app.post("/retry/{session_id}", response_model=DialogueTurnResponse)
def retry_question(session_id: str, db: Session = Depends(get_db)):
    """
    Regenerate the current question with a different approach.
    If LLM is enabled, generates a new variation of the question.
    Otherwise, re-asks the original question.
    """
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    concept = session["current_concept"]
    idx = max(session["next_q_idx"] - 1, 0)  # Get current question index
    questions = concept.get("questions", [])
    
    if idx >= len(questions):
        raise HTTPException(status_code=400, detail="No question to retry")
    
    current_q = questions[idx]
    
    if USE_LLM:
        try:
            # Generate a rephrased version of the question
            prompt = f"""You are a CBSE tutor. Given:
Original Question: "{current_q['question']}"
Concept: {concept['title']} (Class {concept.get('class')}, {concept['subject']})

Create a rephrased version that:
1. Maintains the same learning objective
2. Approaches from a different angle
3. Uses Socratic questioning
4. Is appropriate for Class {concept.get('class')}

Response as JSON:
{{
    "question": "<your rephrased question>",
    "type": "elicitation"
}}"""
            
            response = send_prompt(prompt)
            question_data = parse_llm_question(response)
            new_question = question_data["question"]
            
        except LLMError as e:
            print(f"LLM question generation failed: {e}")
            # Use a template to rephrase the question
            q = current_q["question"]
            if q.startswith("What"):
                new_question = q.replace("What", "Could you explain what")
            elif q.startswith("How"):
                new_question = q.replace("How", "In what way")
            elif q.startswith("Why"):
                new_question = q.replace("Why", "What reasons explain why")
            else:
                new_question = f"Let's look at this another way: {q}"
    else:
        new_question = current_q["question"]
    
    # Record the new question
    persistence.add_turn(db, session_id, "AI", new_question)
    persistence.update_hint_level(db, session_id, 0)
    
    return DialogueTurnResponse(
        session_id=session_id,
        question_type="elicitation",
        question=new_question,
        hint_level=0,
        progress=calculate_progress(session)
    )

# 1️⃣6️⃣ Skip endpoint (with LLM-powered transitions)
@app.post("/skip/{session_id}", response_model=DialogueTurnResponse)
def skip_question(session_id: str, db: Session = Depends(get_db)):
    """
    Skip current question and move to next.
    If using LLM, generates a smooth transition and appropriate next question.
    """
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    concept = session["current_concept"]
    idx = max(session["next_q_idx"], 1)  # Move to next question
    questions = concept.get("questions", [])
    
    if idx >= len(questions):
        return DialogueTurnResponse(
            session_id=session_id,
            question_type="completed",
            question="🎯 You've completed this concept. Use 'Get Reflection' to review your progress.",
            hint_level=0,
            progress={"questions_answered": idx, "total_questions": len(questions)}
        )

    if USE_LLM:
        try:
            # Generate a transition and next question
            previous_q = questions[idx - 1]["question"] if idx > 0 else None
            prompt = f"""You are a CBSE tutor. Given:
Concept: {concept['title']} (Class {concept.get('class')}, {concept['subject']})
Previous Question: "{previous_q if previous_q else 'Starting the concept'}"
Student Action: Chose to skip the question

Generate a new Socratic question that:
1. Acknowledges the skip naturally
2. Moves to a different aspect of {concept['title']}
3. Maintains appropriate difficulty for Class {concept.get('class')}
4. Uses a fresh approach to engage the student

Response as JSON:
{{
    "question": "<your question with brief transition>",
    "type": "elicitation"
}}"""
            
            response = send_prompt(prompt)
            question_data = parse_llm_question(response)
            next_question = question_data["question"]
            
        except LLMError as e:
            print(f"LLM question generation failed: {e}")
            # Add a gentle transition message with the next question
            next_question = f"Let's try a different approach. {questions[idx]['question']}"
    else:
        next_question = questions[idx]["question"]
    
    # Record the transition
    persistence.add_turn(db, session_id, "AI", next_question)
    persistence.update_next_q_idx(db, session_id, idx + 1)
    persistence.update_hint_level(db, session_id, 0)
    
    return DialogueTurnResponse(
        session_id=session_id,
        question_type="elicitation",
        question=next_question,
        hint_level=0
    )

# 1️⃣7️⃣ Concepts endpoint
@app.get("/concepts")
def get_concepts(class_grade: Optional[int] = None, subject: Optional[str] = None):
    """
    Get available concepts filtered by class grade and/or subject.
    
    Args:
        class_grade: Optional class/grade level (9-12) to filter by
        subject: Optional subject name to filter by
        
    Returns:
        List of concepts matching the filters
    """
    filtered_concepts = concept_graph.copy()
    
    # Filter by class grade if provided
    if class_grade is not None:
        filtered_concepts = [c for c in filtered_concepts if c.get("class") == class_grade]
    
    # Filter by subject if provided
    if subject is not None:
        filtered_concepts = [c for c in filtered_concepts if c.get("subject", "").lower() == subject.lower()]
    
    # Return simplified concept data for frontend
    return [
        {
            "id": concept.get("id"),
            "title": concept.get("title"),
            "class": concept.get("class"),
            "subject": concept.get("subject"),
            "prerequisites": concept.get("prerequisites", [])
        }
        for concept in filtered_concepts
    ]

# 1️⃣8️⃣ Get session data
@app.get("/session/{session_id}")
def get_session_data(session_id: str, db: Session = Depends(get_db)):
    """Get complete session data including dialogue"""
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

# 1️⃣9️⃣ Health
@app.get("/health")
def health(db: Session = Depends(get_db)):
    # Get active sessions count from database
    active_count = db.query(DBSession).count()
    return {"status": "ok", "sessions_active": active_count}