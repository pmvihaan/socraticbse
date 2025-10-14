# SocraticCBSE

A Socratic learning platform designed specifically for CBSE (Central Board of Secondary Education) students in India. Currently focused on classes 9-12.

## Features

- 🎓 Interactive dialogue-based learning
- 📚 CBSE curriculum-aligned content
- 💡 Contextual hints and assistance
- 🤔 Reflective learning approach
- 📊 Progress tracking
- 🔄 Adaptive questioning

## Current Status

- ✅ Core dialogue system implemented
- ✅ Basic UI with React components
- ✅ Question-answer workflow
- ✅ Progress tracking
- ✅ Hint system
- ✅ Loading states and error handling
- 🟡 Currently supporting:
  - Classes: 9th to 12th
  - Initial subjects: Biology, Physics, Chemistry

## Project Structure

```
backend/
  ├── backend.py         # FastAPI backend server
  ├── requirements.txt   # Python dependencies
  └── seed_concept_graph.json  # Initial concept data

frontend/
  ├── app/              # Next.js app directory
  │   ├── components/   # React components
  │   │   ├── DialogueView.js    # Chat interface
  │   │   └── LoadingSpinner.js  # Loading states
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

## Technical Stack

### Frontend
- Next.js 13+
- React 18
- Tailwind CSS for styling
- Responsive design for all devices

### Backend
- FastAPI for high-performance API
- File-based session persistence
- Concept graph for adaptive learning

## Environment Variables

Backend:
- `ALLOWED_ORIGINS`: Comma-separated list of allowed CORS origins
  Default: "http://localhost:3000,http://127.0.0.1:3000"

Frontend:
- `NEXT_PUBLIC_BACKEND_URL`: Backend API base URL
  Default: "http://127.0.0.1:8000"

## API Endpoints

### Session Management
- POST `/session/start`: Start a new learning session
- POST `/session/turn`: Submit an answer and get next question
- GET `/progress/{session_id}`: Get session progress

### Learning Support
- GET `/hint/{session_id}`: Get contextual hints
- POST `/retry/{session_id}`: Retry current question
- POST `/skip/{session_id}`: Move to next question
- GET `/reflection/{session_id}`: Get personalized reflection

### System
- GET `/health`: Health check endpoint

## Upcoming Features

- [ ] Support for more CBSE subjects
- [ ] Enhanced concept mapping with LLM integration
- [ ] AI-powered personalized learning paths
- [ ] Performance analytics
- [ ] Offline mode support
- [ ] Parent/Teacher dashboard
- [ ] Practice tests and assessments

## Contributing

We welcome contributions from educators, developers, and CBSE experts. Please see our contributing guidelines for more information.

## License

This project is proprietary and all rights are reserved. © 2025 SocraticCBSE
- Communication via REST API endpoints
- Simple styling with inline styles (MVP version)