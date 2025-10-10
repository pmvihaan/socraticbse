# SocraticBSE

A Socratic learning platform for BSE (Board of Secondary Education) students.

## Project Structure

```
backend/
  ├── backend.py         # FastAPI backend server
  ├── requirements.txt   # Python dependencies
  └── seed_concept_graph.json  # Initial concept data

frontend/
  ├── app/              # Next.js app directory
  │   ├── components/   # React components
  │   ├── config.js     # Frontend configuration
  │   └── page.js       # Main page component
  └── package.json      # Node.js dependencies
```

## Setup

### Backend

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Start the backend server:
```bash
uvicorn backend:app --reload
```

The backend will be available at http://127.0.0.1:8000

### Frontend

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at http://localhost:3000

## Environment Variables

Backend:
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins
  Default: "http://localhost:3000,http://127.0.0.1:3000"

Frontend:
- `NEXT_PUBLIC_BACKEND_URL`: Backend API base URL
  Default: "http://127.0.0.1:8000"

## API Endpoints

- POST `/session/start`: Start a new learning session
- POST `/session/turn`: Submit an answer and get next question
- GET `/hint/{session_id}`: Get a hint for current question
- POST `/retry/{session_id}`: Retry current question
- POST `/skip/{session_id}`: Skip to next question
- GET `/reflection/{session_id}`: Get session reflection
- GET `/progress/{session_id}`: Get session progress
- GET `/health`: Health check endpoint

## Development

- Backend uses FastAPI with file-based session persistence
- Frontend uses Next.js 13+ with App Router
- Communication via REST API endpoints
- Simple styling with inline styles (MVP version)