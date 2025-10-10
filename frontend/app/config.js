// API Configuration
export const API_CONFIG = {
  backendBase: process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000",
  endpoints: {
    startSession: "/session/start",
    turn: "/session/turn",
    hint: "/hint",
    retry: "/retry",
    skip: "/skip",
    reflection: "/reflection",
    progress: "/progress",
    health: "/health"
  }
};