# backend/backend.py

# 1️⃣ Imports
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import os
import time
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# 2️⃣ Local imports
from db import get_db, init_db, Session as DBSession
from persistence import PersistenceLayer

# 3️⃣ Paths and configuration
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_PATH = os.path.join(BASE_DIR, "seed_concept_graph.json")
SESSIONS_PATH = os.path.join(BASE_DIR, "sessions_store.json")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
USE_JSON_PERSISTENCE = os.getenv("USE_JSON_PERSISTENCE", "true").lower() == "true"

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

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

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

class ReflectionResponse(BaseModel):
    session_id: str
    summary_text: str
    suggested_next_concepts: List[str]

class ProgressResponse(BaseModel):
    questions_answered: int
    total_questions: int
    concepts_covered: List[str]
    avg_time_per_question: float = 0
    total_time: float = 0
    times_per_question: List[float] = []

class HintResponse(BaseModel):
    hint: str

# 7️⃣ Helper: find concept
def find_concept(class_grade: int, subject: str, title: str):
    for c in concept_graph:
        if c.get("class") == class_grade and c.get("subject", "").lower() == subject.lower() and c.get("title", "").lower() == title.lower():
            return c
    return None

# 9️⃣ Dynamic hint generator (simple, rule-based)
def generate_dynamic_hint(session: Dict[str, Any]) -> str:
    """
    Return a context-sensitive hint for the current question.
    Rules (MVP):
      - If the question has explicit 'hints' list, serve from there (in order).
      - Otherwise, examine the most recent user's answer and produce a short guiding hint:
          * if user's answer is short -> ask to elaborate
          * if it mentions a related keyword (from concept keywords) -> point to elaboration
          * fallback: ask to consider cause/effect or units/definition depending on question text
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
        persist_sessions()
        return hints[hl]

    # 9.2 Otherwise, simple heuristics using last user answer
    dialogue = session.get("dialogue", [])
    user_turns = [d["text"] for d in dialogue if d["speaker"] == "User" and d["text"].strip()]
    last = user_turns[-1] if user_turns else ""
    last_len = len(last.strip())

    # concept-level keywords (if present in seed graph)
    keywords = concept.get("keywords", [])
    # normalize
    lk = last.lower()
    found_kw = [k for k in keywords if k.lower() in lk]

    # Heuristics
    if last_len == 0:
        hint = "Try writing a short sentence explaining what you think, even if you're unsure — start with 'Plants do...' or 'They use...'."
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
    persist_sessions()
    return hint

# 1️⃣0️⃣ Start session endpoint
@app.post("/session/start", response_model=SessionStartResponse)
def start_session(req: SessionStartRequest, db: Session = Depends(get_db)):
    concept = find_concept(req.class_grade, req.subject, req.concept_title)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

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
def session_turn(req: DialogueTurnRequest, db: Session = Depends(get_db)):
    session = persistence.get_session(db, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Store user answer with timestamp
    persistence.add_turn(db, req.session_id, "User", req.user_answer)

    concept = session["current_concept"]
    questions = concept.get("questions", [])
    idx = session.get("next_q_idx", 0)

    if idx >= len(questions):
        # Completed current concept
        completion_message = (
            "🎉 Congratulations! You've completed this concept. "
            "Click 'Get Reflection' to see a summary of your responses and suggested next concepts."
        )
        persistence.add_turn(db, req.session_id, "AI", completion_message)
        return DialogueTurnResponse(
            session_id=req.session_id,
            question_type="completed",
            question=completion_message,
            hint_level=0
        )

    # Next question
    next_q = questions[idx]
    persistence.add_turn(db, req.session_id, "AI", next_q["question"])
    persistence.update_next_q_idx(db, req.session_id, idx + 1)
    persistence.update_hint_level(db, req.session_id, 0)

    return DialogueTurnResponse(session_id=req.session_id, question_type=next_q.get("type","elicitation"), question=next_q.get("question",""), hint_level=0)

# 1️⃣2️⃣ Reflection
@app.get("/reflection/{session_id}", response_model=ReflectionResponse)
def get_reflection(session_id: str, db: Session = Depends(get_db)):
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    dialogue = session.get("dialogue", [])
    user_turns = [d["text"] for d in dialogue if d["speaker"]=="User" and d["text"].strip()]
    suggested_next = session["current_concept"].get("prerequisites", [])
    summary_text = f"During '{session['current_concept']['title']}', you answered {len(user_turns)} questions. Key ideas: {', '.join(user_turns) if user_turns else 'none'}."
    return ReflectionResponse(session_id=session_id, summary_text=summary_text, suggested_next_concepts=suggested_next)

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

# 1️⃣4️⃣ Hint endpoint (dynamic)
@app.get("/hint/{session_id}", response_model=HintResponse)
def get_hint(session_id: str, db: Session = Depends(get_db)):
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    concept = session["current_concept"]
    idx = max(session["next_q_idx"] - 1, 0)
    questions = concept.get("questions", [])
    
    if idx < 0 or idx >= len(questions):
        return HintResponse(hint="No hints available.")

    q = questions[idx]
    hints = q.get("hints", [])
    
    # Use predefined hints if available
    hint_level = session["hint_level"]
    if hint_level < len(hints):
        persistence.update_hint_level(db, session_id, hint_level + 1)
        return HintResponse(hint=hints[hint_level])
    
    # Otherwise, generate dynamic hint
    dialogue = session.get("dialogue", [])
    user_turns = [d["text"] for d in dialogue if d["speaker"] == "User" and d["text"].strip()]
    last = user_turns[-1] if user_turns else ""
    
    # Generate a contextual hint
    if not last.strip():
        hint = "Try writing a short sentence explaining what you think."
    elif "why" in q["question"].lower():
        hint = "Think about cause and effect: what causes this to happen and why?"
    else:
        hint = "Can you explain your answer in more detail?"
    
    persistence.update_hint_level(db, session_id, session["hint_level"] + 1)
    return HintResponse(hint=hint)

# 1️⃣5️⃣ Retry endpoint (re-ask current question)
@app.post("/retry/{session_id}", response_model=DialogueTurnResponse)
def retry_question(session_id: str, db: Session = Depends(get_db)):
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    idx = max(session["next_q_idx"] - 1, 0)
    questions = session["current_concept"].get("questions", [])
    if idx >= len(questions):
        raise HTTPException(status_code=400, detail="No question to retry")
    
    question = questions[idx]
    persistence.add_turn(db, session_id, "AI", question["question"])
    persistence.update_hint_level(db, session_id, 0)
    
    return DialogueTurnResponse(
        session_id=session_id,
        question_type=question.get("type", "elicitation"),
        question=question["question"],
        hint_level=0
    )

# 1️⃣6️⃣ Skip endpoint (advance to next question without user answer)
@app.post("/skip/{session_id}", response_model=DialogueTurnResponse)
def skip_question(session_id: str, db: Session = Depends(get_db)):
    session = persistence.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    idx = session["next_q_idx"]
    questions = session["current_concept"].get("questions", [])
    
    if idx >= len(questions):
        return DialogueTurnResponse(
            session_id=session_id,
            question_type="completed",
            question="All questions completed. Fetch reflection.",
            hint_level=0
        )
    
    next_q = questions[idx]
    persistence.add_turn(db, session_id, "AI", next_q["question"])
    persistence.update_next_q_idx(db, session_id, idx + 1)
    persistence.update_hint_level(db, session_id, 0)
    
    return DialogueTurnResponse(
        session_id=session_id,
        question_type=next_q.get("type", "elicitation"),
        question=next_q["question"],
        hint_level=0
    )

# 1️⃣7️⃣ Health
@app.get("/health")
def health(db: Session = Depends(get_db)):
    # Get active sessions count from database
    active_count = db.query(DBSession).count()
    return {"status": "ok", "sessions_active": active_count}