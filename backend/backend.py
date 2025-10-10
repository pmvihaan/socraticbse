# backend/backend.py

# 1️⃣ Imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import os
import threading
import time

# 2️⃣ Paths and seed graph
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEED_PATH = os.path.join(BASE_DIR, "seed_concept_graph.json")
SESSIONS_PATH = os.path.join(BASE_DIR, "sessions_store.json")  # persistent sessions file

with open(SEED_PATH, "r", encoding="utf-8") as f:
    concept_graph: List[Dict[str, Any]] = json.load(f)

# 3️⃣ In-memory sessions (will be loaded/saved to disk)
sessions: Dict[str, Dict[str, Any]] = {}

# 4️⃣ FastAPI app
app = FastAPI(title="SocraticBSE Backend — Persistent + Dynamic Hints")

# 5️⃣ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
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

class HintResponse(BaseModel):
    hint: str

# 7️⃣ Persistence helpers
_persist_lock = threading.Lock()

def load_sessions():
    """Load sessions from disk (if exists). Called at startup."""
    global sessions
    try:
        if os.path.exists(SESSIONS_PATH):
            with open(SESSIONS_PATH, "r", encoding="utf-8") as f:
                sessions = json.load(f)
                # JSON keys were strings; ensure types are fine (no special objects)
    except Exception as e:
        print("Warning: failed to load sessions:", e)

def save_sessions_debounced(delay=0.5):
    """Small debounce wrapper to avoid writing too frequently in quick succession."""
    def _do_save():
        time.sleep(delay)
        with _persist_lock:
            try:
                with open(SESSIONS_PATH, "w", encoding="utf-8") as f:
                    json.dump(sessions, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print("Failed to save sessions:", e)
    t = threading.Thread(target=_do_save, daemon=True)
    t.start()

def persist_sessions():
    """Call this after mutating sessions."""
    save_sessions_debounced()

# Load existing sessions on startup
load_sessions()

# 8️⃣ Helper: find concept
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
def start_session(req: SessionStartRequest):
    concept = find_concept(req.class_grade, req.subject, req.concept_title)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "user_id": req.user_id,
        "current_concept": concept,
        "dialogue": [],
        "next_q_idx": 0,
        "progress": {
            "questions_answered": 0,
            "total_questions": len(concept.get("questions", [])),
            "concepts_covered": [concept["title"]]
        },
        "hint_level": 0
    }

    # Save
    persist_sessions()

    questions = concept.get("questions", [])
    if not questions:
        raise HTTPException(status_code=500, detail="Concept has no questions")
    first_q = questions[0]
    sessions[session_id]["dialogue"].append({"speaker": "AI", "text": first_q["question"]})
    sessions[session_id]["next_q_idx"] = 1
    persist_sessions()

    return SessionStartResponse(session_id=session_id, question_type=first_q.get("type","elicitation"), question=first_q.get("question",""), hint_level=0)

# 1️⃣1️⃣ Submit answer / next turn
@app.post("/session/turn", response_model=DialogueTurnResponse)
def session_turn(req: DialogueTurnRequest):
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update progress only for non-empty answers
    if req.user_answer.strip():
        session["progress"]["questions_answered"] += 1

    # Store user answer
    session["dialogue"].append({"speaker": "User", "text": req.user_answer})
    persist_sessions()

    concept = session["current_concept"]
    questions = concept.get("questions", [])
    idx = session.get("next_q_idx", 0)

    if idx >= len(questions):
        # Completed current concept (no auto-advance in this endpoint)
        return DialogueTurnResponse(session_id=req.session_id, question_type="completed", question="All questions completed. Fetch reflection.", hint_level=0)

    # Next question
    next_q = questions[idx]
    session["dialogue"].append({"speaker": "AI", "text": next_q["question"]})
    session["next_q_idx"] = idx + 1
    session["hint_level"] = 0
    persist_sessions()

    return DialogueTurnResponse(session_id=req.session_id, question_type=next_q.get("type","elicitation"), question=next_q.get("question",""), hint_level=0)

# 1️⃣2️⃣ Reflection
@app.get("/reflection/{session_id}", response_model=ReflectionResponse)
def get_reflection(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    dialogue = session.get("dialogue", [])
    user_turns = [d["text"] for d in dialogue if d["speaker"]=="User" and d["text"].strip()]
    suggested_next = session["current_concept"].get("prerequisites", [])
    summary_text = f"During '{session['current_concept']['title']}', you answered {len(user_turns)} questions. Key ideas: {', '.join(user_turns) if user_turns else 'none'}."
    return ReflectionResponse(session_id=session_id, summary_text=summary_text, suggested_next_concepts=suggested_next)

# 1️⃣3️⃣ Progress endpoint (accurate totals)
@app.get("/progress/{session_id}", response_model=ProgressResponse)
def get_progress(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # total_questions is stored in session.progress; we kept it updated on start and when queue grows
    return ProgressResponse(
        questions_answered=session["progress"].get("questions_answered",0),
        total_questions=session["progress"].get("total_questions",0),
        concepts_covered=session["progress"].get("concepts_covered",[])
    )

# 1️⃣4️⃣ Hint endpoint (dynamic)
@app.get("/hint/{session_id}", response_model=HintResponse)
def get_hint(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    hint_text = generate_dynamic_hint(session)
    return HintResponse(hint=hint_text)

# 1️⃣5️⃣ Retry endpoint (re-ask current question)
@app.post("/retry/{session_id}", response_model=DialogueTurnResponse)
def retry_question(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    idx = max(session.get("next_q_idx",1)-1, 0)
    question = session["current_concept"].get("questions", [])[idx]
    # re-add the AI question to dialogue
    session["dialogue"].append({"speaker":"AI","text":question.get("question","")})
    session["hint_level"] = 0
    persist_sessions()
    return DialogueTurnResponse(session_id=session_id, question_type=question.get("type","elicitation"), question=question.get("question",""), hint_level=0)

# 1️⃣6️⃣ Skip endpoint (advance to next question without user answer)
@app.post("/skip/{session_id}", response_model=DialogueTurnResponse)
def skip_question(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    concept = session["current_concept"]
    idx = session.get("next_q_idx", 0)
    questions = concept.get("questions", [])
    if idx >= len(questions):
        return DialogueTurnResponse(session_id=session_id, question_type="completed", question="All questions completed. Fetch reflection.", hint_level=0)
    next_q = questions[idx]
    session["dialogue"].append({"speaker":"AI","text":next_q.get("question","")})
    session["next_q_idx"] = idx + 1
    session["hint_level"] = 0
    # no change to questions_answered on skip
    persist_sessions()
    return DialogueTurnResponse(session_id=session_id, question_type=next_q.get("type","elicitation"), question=next_q.get("question",""), hint_level=0)

# 1️⃣7️⃣ Health
@app.get("/health")
def health():
    return {"status":"ok","sessions_active":len(sessions)}