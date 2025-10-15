# SocraticBSE

**A Socratic dialogue platform for CBSE students (Classes 9–12)**  
Use the Socratic method with AI — ask, reflect, progress, and learn.

---

## Table of Contents

- [What is SocraticBSE?](#what-is-socraticbse)  
- [Key Features](#key-features)  
- [How the "Socratic" Part Works](#how-the-socratic-part-works)  
- [Architecture & Project Structure](#architecture--project-structure)  
- [Setup & Installation](#setup--installation)  
- [API Endpoints](#api-endpoints)  
- [Usage Workflow](#usage-workflow)  
- [Roadmap & Upcoming Features](#roadmap--upcoming-features)  
- [Contributing](#contributing)  
- [License & Acknowledgments](#license--acknowledgments)  

---

## What is SocraticBSE?

SocraticBSE is an interactive learning platform built around the **Socratic method** (via dialogue) tailored for CBSE students in India (Grades 9–12). Instead of passive reading or multiple-choice, the system asks probing questions, gives hints, allows students to retry or skip, and invites reflection. It's designed to help learners *think* and *articulate reasoning*, not just memorize.

The name "SocraticBSE" blends "Socratic" (question-driven learning) with "CBSE" to highlight its curriculum focus.

---

## Key Features

- Dialogue-based AI tutoring (question → answer → hint → reflection)  
- Advanced progress tracking:
  - Questions answered and completion percentage
  - Time per question and total time tracking
  - Average response time analytics
  - Concepts covered counter
- Hint system (incremental, context-aware)  
- Retry and Skip controls per question  
- SQLite persistence with JSON fallback
  - Reliable data storage with database migrations
  - Session survival across backend restarts
  - Accurate timing and progress metrics
- Modern frontend architecture (React / Next.js)
  - Real-time progress updates
  - Responsive timing displays
  - Clean, accessible UI components
- Configurable backend (FastAPI):
  - CORS and environment setup
  - Clean error handling and fallbacks
  - Efficient database queries

## How the Socratic Part Works

1. **Elicitation questions** — system begins with a question (e.g. "Why do plants need sunlight?").  
2. **Student responds** in their own words (no fixed options).  
3. **Adaptive next questions** — the system either uses static seeded questions or queries an LLM to generate follow-up probing questions.  
4. **Hint mechanism** — if a student is stuck, they can request hints. Hints are incremental, tailored to their answers.  
5. **Retry / Skip** — they can retry the same question (re-ask) or skip it (move ahead) without blocking flow.  
6. **Reflection** — at the end of the concept, the system summarizes the student's answers and suggests next related concepts to explore.  

This mirrors the classic *Socratic tutor* style: guiding by questions, encouraging the student to think deeper, not just handing over answers.

---

## Architecture & Project Structure

```
socraticbse/
├── backend/
│ ├── backend.py
│ ├── requirements.txt
│ └── seed_concept_graph.json
├── frontend/
│ ├── app/
│ │ ├── components/
│ │ │ └── DialogueView.js
│ │ ├── config.js
│ │ └── page.js
│ └── package.json
├── .gitignore
└── README.md
```

- **backend/** — FastAPI server handling sessions, hints, retry, skip, persistence.  
- **seed_concept_graph.json** — initial concept graph data (concepts, questions, hints, prerequisites).  
- **frontend/app/** — Next.js 13 app folder:
  - `DialogueView.js` — component to render the chat.  
  - `config.js` — API endpoint configuration.  
  - `page.js` — main UI logic (state, controls, fetching).  
- **.gitignore** — exclude node_modules, sessions_store, etc.  
- **README.md** — this file.

## Setup & Installation

### Backend

1. Install Python dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

(Optional) Create & activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate    # macOS / Linux
venv\Scripts\activate       # Windows
```

Run the server:
```bash
uvicorn backend:app --reload --host 127.0.0.1 --port 8000
```

Check health:
```
http://127.0.0.1:8000/health
```

### Frontend

In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

Open browser at:
```
http://localhost:3000
```

### Environment variables (optional / advanced)

- `ALLOWED_ORIGINS` (backend) — comma-separated CORS origins.
- `NEXT_PUBLIC_BACKEND_URL` (frontend) — override backend URL.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/session/start` | Start a new session (returns first question) |
| POST | `/session/turn` | Submit user answer, get next question |
| GET | `/hint/{session_id}` | Get a hint for current question |
| POST | `/retry/{session_id}` | Retry (re-ask) the current question |
| POST | `/skip/{session_id}` | Skip to next question |
| GET | `/progress/{session_id}` | Get progress stats (answered, total, concepts) |
| GET | `/reflection/{session_id}` | Get summary and next-concept suggestions |
| GET | `/health` | Health check |

## Usage Workflow

1. **Start session** — choose concept, class, subject → fetch first question.
2. **Answer** — student types answer → system returns next question or "completed".
3. **Hint / Retry / Skip** — optional controls if stuck.
4. **Progress** updates in real time.
5. **Reflection** — summarize student answers, highlight key ideas, suggest next concepts.
6. Optionally, resume session (if implemented later) or teacher review.

## Roadmap & Upcoming Features

- LLM-driven Socratic questioning & hints (Week 3)
- User accounts & session persistence via DB (Week 4)
- Expanded concept graph & vector retrieval (RAG) (Week 5)
- UX polish, teacher dashboard, deployment (Week 6)
- Optional: offline mode, assessment quizzes, multi-student campaigns

## Contributing

We welcome collaboration from educators, CBSE experts, UI designers, and developers.

- Open an issue to discuss features or raise bugs
- Fork the repo and submit pull requests
- Follow the prompt guidelines and write tests where possible
- Ensure seed content (NCERT / textbook extracts) are used within allowable rights

## License & Acknowledgments

This project is under .[Your License Here]

Built with FastAPI, Next.js, and a Socratic learning philosophy

Thanks to CBSE curriculum guides, open educational resource communities