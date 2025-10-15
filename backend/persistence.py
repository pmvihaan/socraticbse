from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import json
import os
import time
from datetime import datetime
import db
from db import User, Session as DBSession, Turn, Progress

class PersistenceLayer:
    def __init__(self, use_json: bool = True, json_path: str = None):
        self.use_json = use_json
        self.json_path = json_path or os.path.join(os.path.dirname(__file__), "sessions_store.json")
        self._sessions_cache = {}
        
        if use_json:
            self._load_json()
    
    def _load_json(self):
        """Load sessions from JSON file if it exists"""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self._sessions_cache = json.load(f)
            except Exception as e:
                print(f"Warning: failed to load sessions from JSON: {e}")
                self._sessions_cache = {}
    
    def _save_json(self):
        """Save sessions to JSON file"""
        if not self.use_json:
            return
        try:
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self._sessions_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: failed to save sessions to JSON: {e}")
    
    def create_session(self, db_session: Session, session_id: str, user_id: str, concept_data: Dict[str, Any]) -> None:
        """Create a new session in both DB and optionally JSON"""
        # Create user if doesn't exist
        user = db_session.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id)
            db_session.add(user)
        
        # Create session
        session = DBSession(
            id=session_id,
            user_id=user_id,
            concept_data=concept_data,
            started_at=datetime.utcnow()
        )
        db_session.add(session)
        
        # Create initial progress
        progress = Progress(
            session_id=session_id,
            total_questions=len(concept_data.get("questions", [])),
            concepts_covered=[concept_data["title"]],
            times_per_question=[]
        )
        db_session.add(progress)
        
        if self.use_json:
            self._sessions_cache[session_id] = {
                "user_id": user_id,
                "current_concept": concept_data,
                "dialogue": [],
                "next_q_idx": 0,
                "started_at": datetime.utcnow().timestamp(),
                "last_turn_at": datetime.utcnow().timestamp(),
                "turn_timestamps": [],
                "progress": {
                    "questions_answered": 0,
                    "total_questions": len(concept_data.get("questions", [])),
                    "concepts_covered": [concept_data["title"]],
                    "times_per_question": []
                },
                "hint_level": 0
            }
            self._save_json()
        
        db_session.commit()
    
    def get_session(self, db_session: Session, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from DB and format it like the JSON structure"""
        session = db_session.query(DBSession).filter(DBSession.id == session_id).first()
        if not session:
            return None
        
        # Get turns and progress
        turns = db_session.query(Turn).filter(Turn.session_id == session_id).order_by(Turn.timestamp).all()
        progress = db_session.query(Progress).filter(Progress.session_id == session_id).first()
        
        # Process dialogue and calculate times
        dialogue = []
        times_per_question = []
        last_question_time = None
        
        for turn in turns:
            dialogue.append({
                "speaker": turn.speaker,
                "text": turn.text,
                "timestamp": turn.timestamp.timestamp()
            })
            
            # Calculate time per question when user responds
            if turn.speaker == "User" and last_question_time is not None:
                time_diff = turn.timestamp.timestamp() - last_question_time
                if time_diff < 3600:  # Ignore gaps longer than 1 hour
                    times_per_question.append(round(time_diff, 1))
            elif turn.speaker == "AI" and "Congratulations" not in turn.text:
                last_question_time = turn.timestamp.timestamp()
                
        # Update progress with calculated times
        if progress and times_per_question:
            progress.times_per_question = times_per_question
            db_session.commit()
        
        started = session.started_at.timestamp()
        last_turn = turns[-1].timestamp.timestamp() if turns else started
        
        return {
            "user_id": session.user_id,
            "current_concept": session.concept_data,
            "dialogue": dialogue,
            "next_q_idx": session.next_q_idx,
            "started_at": started,
            "last_turn_at": last_turn,
            "turn_timestamps": [t.timestamp.timestamp() for t in turns],
            "progress": {
                "questions_answered": progress.questions_answered if progress else 0,
                "total_questions": progress.total_questions if progress else 0,
                "concepts_covered": progress.concepts_covered if progress else [],
                "times_per_question": times_per_question
            },
            "hint_level": session.hint_level
        }
    
    def add_turn(self, db_session: Session, session_id: str, speaker: str, text: str, time_spent: Optional[float] = None):
        """Add a turn to the session"""
        # Add to DB
        turn = Turn(
            session_id=session_id,
            speaker=speaker,
            text=text,
            time_spent=time_spent
        )
        db_session.add(turn)
        
        # Update session
        session = db_session.query(DBSession).filter(DBSession.id == session_id).first()
        if speaker == "User":
            # Update progress for user turns
            progress = db_session.query(Progress).filter(Progress.session_id == session_id).first()
            if progress and text.strip():
                progress.questions_answered += 1
                if time_spent:
                    times = progress.times_per_question or []
                    times.append(time_spent)
                    progress.times_per_question = times
        
        if self.use_json:
            if session_id in self._sessions_cache:
                self._sessions_cache[session_id]["dialogue"].append({
                    "speaker": speaker,
                    "text": text
                })
                if speaker == "User" and text.strip():
                    self._sessions_cache[session_id]["progress"]["questions_answered"] += 1
                    if time_spent:
                        self._sessions_cache[session_id]["progress"]["times_per_question"].append(time_spent)
                self._save_json()
        
        db_session.commit()
    
    def update_hint_level(self, db_session: Session, session_id: str, hint_level: int):
        """Update hint level for a session"""
        session = db_session.query(DBSession).filter(DBSession.id == session_id).first()
        if session:
            session.hint_level = hint_level
            if self.use_json and session_id in self._sessions_cache:
                self._sessions_cache[session_id]["hint_level"] = hint_level
                self._save_json()
            db_session.commit()
    
    def update_next_q_idx(self, db_session: Session, session_id: str, next_q_idx: int):
        """Update next question index for a session"""
        session = db_session.query(DBSession).filter(DBSession.id == session_id).first()
        if session:
            session.next_q_idx = next_q_idx
            if self.use_json and session_id in self._sessions_cache:
                self._sessions_cache[session_id]["next_q_idx"] = next_q_idx
                self._save_json()
            db_session.commit()