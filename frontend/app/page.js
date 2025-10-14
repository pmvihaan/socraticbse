"use client"; // 1️⃣ client component

import { useState } from "react";
import { API_CONFIG } from "./config";
import { DialogueView } from "./components/DialogueView";
import { LoadingSpinner } from "./components/LoadingSpinner";

export default function HomePage() {
  // State
  const [userId, setUserId] = useState("student1");
  const [classGrade, setClassGrade] = useState(10);
  const [subject, setSubject] = useState("Biology");
  const [concept, setConcept] = useState("Photosynthesis");
  const [sessionId, setSessionId] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [userAnswer, setUserAnswer] = useState("");
  const [dialogue, setDialogue] = useState([]);
  const [progress, setProgress] = useState(null);
  const [reflection, setReflection] = useState(null);
  const [hintText, setHintText] = useState("");
  const [loading, setLoading] = useState(false);
  
  // Loading states
  const [isStarting, setIsStarting] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGettingHint, setIsGettingHint] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isSkipping, setIsSkipping] = useState(false);
  const [isGettingReflection, setIsGettingReflection] = useState(false);
  const [questionShownAt, setQuestionShownAt] = useState(null);

  // helper: safe fetch wrapper
  async function safeFetch(endpoint, options) {
    const url = `${API_CONFIG.backendBase}${endpoint}`;
    setLoading(true);
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        const body = await res.text().catch(() => "");
        throw new Error(body || res.statusText);
      }
      return await res.json();
    } finally {
      setLoading(false);
    }
  }

  // 4️⃣ start session
  const startSession = async () => {
    setDialogue([]);
    setReflection(null);
    setProgress(null);
    setHintText("");
    setCurrentQuestion(null);
    setIsStarting(true);
    try {
      const data = await safeFetch(API_CONFIG.endpoints.startSession, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          class_grade: Number(classGrade),
          subject,
          concept_title: concept,
          started_at: new Date().toISOString(),
        }),
      });
      setSessionId(data.session_id);
      setCurrentQuestion(data);
      setDialogue([{ speaker: "AI", text: data.question }]);
      setQuestionShownAt(Date.now());
      fetchProgress(data.session_id);
    } catch (e) {
      alert("Start session failed: " + e.message);
    } finally {
      setIsStarting(false);
    }
  };

  // 5️⃣ submit answer
  const submitAnswer = async () => {
    if (!sessionId) return alert("Start a session first.");
    if (!userAnswer.trim()) return alert("Please type an answer or use Skip/Retry.");

    setIsSubmitting(true);
    try {
      const timeSpent = Date.now() - questionShownAt;
      setDialogue((p) => [...p, { speaker: "You", text: userAnswer }]);
      const data = await safeFetch(API_CONFIG.endpoints.turn, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          session_id: sessionId, 
          user_answer: userAnswer,
          answered_at: new Date().toISOString(),
          time_spent_ms: timeSpent
        }),
      });
      setCurrentQuestion(data);
      if (data.question) {
        setDialogue((p) => [...p, { speaker: "AI", text: data.question }]);
        setQuestionShownAt(Date.now());
      }
      setUserAnswer("");
      setHintText("");
      fetchProgress(sessionId);
    } catch (e) {
      alert("Submit failed: " + e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // 6️⃣ get hint (dynamic)
  const getHint = async () => {
    if (!sessionId) return alert("Start a session first.");
    try {
      const data = await safeFetch(`${API_CONFIG.endpoints.hint}/${sessionId}`);
      setHintText(data.hint);
      setDialogue((p) => [...p, { speaker: "AI (Hint)", text: data.hint }]);
      fetchProgress(sessionId);
    } catch (e) {
      alert("Hint failed: " + e.message);
    }
  };

  // 7️⃣ retry question
  const retryQuestion = async () => {
    if (!sessionId) return alert("Start a session first.");
    try {
      const data = await safeFetch(`${API_CONFIG.endpoints.retry}/${sessionId}`, { method: "POST" });
      setCurrentQuestion(data);
      if (data.question) setDialogue((p) => [...p, { speaker: "AI", text: data.question }]);
      setHintText("");
      fetchProgress(sessionId);
    } catch (e) {
      alert("Retry failed: " + e.message);
    }
  };

  // 8️⃣ skip question
  const skipQuestion = async () => {
    if (!sessionId) return alert("Start a session first.");
    try {
      const data = await safeFetch(`${API_CONFIG.endpoints.skip}/${sessionId}`, { method: "POST" });
      setCurrentQuestion(data);
      if (data.question) setDialogue((p) => [...p, { speaker: "AI", text: data.question }]);
      setHintText("");
      fetchProgress(sessionId);
    } catch (e) {
      alert("Skip failed: " + e.message);
    }
  };

  // 9️⃣ reflection (always available)
  const fetchReflection = async () => {
    if (!sessionId) return alert("Start a session first.");
    try {
      const data = await safeFetch(`${API_CONFIG.endpoints.reflection}/${sessionId}`);
      setReflection(data);
    } catch (e) {
      alert("Reflection failed: " + e.message);
    }
  };

  // 🔟 progress
  const fetchProgress = async (sid) => {
    try {
      const id = sid || sessionId;
      if (!id) return;
      const data = await safeFetch(`${API_CONFIG.endpoints.progress}/${id}`);
      setProgress(data);
    } catch (e) {
      console.warn("Progress fetch:", e.message);
    }
  };

  // 1️⃣1️⃣ derived
  const isCompleted = currentQuestion?.question_type === "completed";

  // 1️⃣2️⃣ styles (simple)
  const inputStyle = { padding: 8, minWidth: 220, borderRadius: 4, border: "1px solid #ccc" };
  const btn = { padding: "8px 10px", borderRadius: 6, border: "none", cursor: "pointer" };

  return (
    <div className="max-w-4xl mx-auto p-6 font-sans">
      <h1 className="text-3xl font-bold mb-6">SocraticBSE — MVP</h1>

      {/* Start */}
      <section className="p-4 border border-gray-200 rounded-lg bg-white shadow-sm">
        <h3 className="text-xl font-semibold mb-4">Start a session</h3>
        <div className="flex flex-wrap gap-4 items-center">
          <input
            className="input-field"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Student ID"
          />
          <select
            className="input-field"
            value={classGrade}
            onChange={(e) => setClassGrade(e.target.value)}
          >
            <option value={9}>Class 9</option>
            <option value={10}>Class 10</option>
            <option value={11}>Class 11</option>
            <option value={12}>Class 12</option>
          </select>
          <select
            className="input-field"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          >
            <option>Physics</option>
            <option>Biology</option>
            <option>Mathematics</option>
            <option>Chemistry</option>
          </select>
          <input
            className="input-field"
            value={concept}
            onChange={(e) => setConcept(e.target.value)}
            placeholder="Concept (e.g., Photosynthesis)"
          />
          <button
            className="button-primary"
            onClick={startSession}
            disabled={isStarting}
          >
            {isStarting ? <LoadingSpinner /> : "Start"}
          </button>
        </div>
      </section>

      {/* Question + controls */}
      {currentQuestion && (
        <section className="mt-6 p-6 rounded-lg border border-blue-100 bg-blue-50">
          <h3 className="text-xl font-semibold mb-4">AI Question</h3>
          <p className="mb-4 text-lg">{currentQuestion.question}</p>

          <div className="flex flex-wrap gap-3 items-center">
            <input
              className="input-field flex-grow"
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder={isCompleted ? "Session completed — use Retry/Skip or Get Reflection" : "Type your answer..."}
              disabled={isCompleted || isSubmitting}
            />
            <button
              className="button-primary"
              onClick={submitAnswer}
              disabled={isCompleted || isSubmitting || !userAnswer.trim()}
            >
              {isSubmitting ? <LoadingSpinner /> : "Submit"}
            </button>
            <button
              className="button-hint"
              onClick={getHint}
              disabled={isCompleted || isGettingHint}
            >
              {isGettingHint ? <LoadingSpinner /> : "Get Hint"}
            </button>
            <button
              className="button-secondary"
              onClick={retryQuestion}
              disabled={isRetrying}
            >
              {isRetrying ? <LoadingSpinner /> : "Retry"}
            </button>
            <button
              className="button-warning"
              onClick={skipQuestion}
              disabled={isSkipping}
            >
              {isSkipping ? <LoadingSpinner /> : "Skip"}
            </button>
            <button
              className="button-reflection"
              onClick={fetchReflection}
              disabled={isGettingReflection}
            >
              {isGettingReflection ? <LoadingSpinner /> : "Get Reflection"}
            </button>
          </div>

          {hintText && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-100 rounded text-yellow-800">
              <strong>Hint:</strong> {hintText}
            </div>
          )}
          {isCompleted && (
            <div className="mt-4 p-3 bg-green-50 border border-green-100 rounded text-green-800">
              ✅ Completed for this concept — fetch reflection or Retry/Skip to revisit.
            </div>
          )}
        </section>
      )}

      {/* Dialogue */}
      <section style={{ marginTop:12 }}>
        <h3>Dialogue</h3>
        <div style={{ padding:12, background:"#fafafa", borderRadius:8, minHeight:80 }}>
          <DialogueView dialogue={dialogue} />
        </div>
      </section>

      {/* Progress */}
      {progress && (
        <section style={{ marginTop:12, padding:12, borderRadius:8, border:"1px solid #eee" }}>
          <h3>Progress</h3>
          <div style={{ display:"flex", gap:12, alignItems:"center" }}>
            <progress value={progress.questions_answered} max={progress.total_questions} style={{ width:"100%" }} />
            <div style={{ minWidth:60, textAlign:"right" }}>{Math.round((progress.questions_answered / Math.max(progress.total_questions,1))*100)}%</div>
          </div>
          <div style={{ marginTop:8 }}>{progress.questions_answered} / {progress.total_questions} answered</div>
          <div>Concepts covered: {progress.concepts_covered.join(", ")}</div>
        </section>
      )}

      {/* Reflection */}
      {reflection && (
        <section style={{ marginTop:12, padding:12, background:"#fffbe6", borderRadius:8 }}>
          <h3>Reflection</h3>
          <div style={{ marginBottom:8 }}>{reflection.summary_text}</div>
          <div><strong>Suggested next concepts:</strong> {reflection.suggested_next_concepts.join(", ")}</div>
        </section>
      )}

      <footer className="mt-8 text-sm text-gray-500">
        <div className="flex gap-4 items-center justify-center">
          <a 
            href="http://localhost:3000" 
            target="_blank" 
            rel="noreferrer"
            className="hover:text-gray-700"
          >
            Frontend
          </a>
          <span>|</span>
          <a 
            href="http://127.0.0.1:8000" 
            target="_blank" 
            rel="noreferrer"
            className="hover:text-gray-700"
          >
            Backend
          </a>
          <span>|</span>
          <a 
            href="http://127.0.0.1:8000/health" 
            target="_blank" 
            rel="noreferrer"
            className="hover:text-gray-700"
          >
            Health Check
          </a>
        </div>
      </footer>
    </div>
  );
}