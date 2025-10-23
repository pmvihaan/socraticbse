"use client"; // 1️⃣ client component

import { useState, useEffect } from "react";
import { API_CONFIG } from "./config";
import { DialogueView } from "./components/DialogueView";
import { LoadingSpinner } from "./components/LoadingSpinner";
import { ProgressStats } from "./components/ProgressStats";
import { ConceptSelector } from "./components/ConceptSelector";

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
  const [questionStart, setQuestionStart] = useState(null);
  const [dialogueTiming, setDialogueTiming] = useState([]);

  // Auto-fetch progress when session changes
  useEffect(() => {
    if (sessionId) {
      fetchProgress(sessionId);
    }
  }, [sessionId]);

  // Timer start when new question arrives
  useEffect(() => {
    if (currentQuestion && currentQuestion.question) {
      setQuestionStart(Date.now());
      console.debug('Question started at', Date.now());
    }
  }, [currentQuestion?.question]);

  // Helper: classify speed based on elapsed seconds
  const classifySpeed = (elapsedSeconds) => {
    if (elapsedSeconds <= 15) return "fast";
    if (elapsedSeconds <= 45) return "medium";
    return "slow";
  };

  // helper: safe fetch wrapper
  async function safeFetch(endpoint, options = {}) {
    if (!endpoint) throw new Error("Endpoint is required");
    if (endpoint.startsWith('/')) {
      endpoint = endpoint.slice(1); // Remove leading slash if present
    }
    const url = `${API_CONFIG.backendBase}/${endpoint}`;
    setLoading(true);
    
    try {
      console.log("Fetching:", url, options); // Debug log
      const res = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(options?.headers || {})
        },
        mode: 'cors',
        credentials: 'same-origin'
      });
      
      const contentType = res.headers.get("content-type");
      
      if (!res.ok) {
        let errorMessage;
        try {
          if (contentType?.includes("application/json")) {
            const errorData = await res.json();
            errorMessage = errorData.detail || errorData.message || res.statusText;
          } else {
            errorMessage = await res.text();
          }
        } catch {
          errorMessage = res.statusText;
        }
        throw new Error(errorMessage);
      }
      
      if (contentType?.includes("application/json")) {
        return await res.json();
      }
      return await res.text();
      
    } catch (e) {
      console.error("Fetch error:", e); // Debug log
      throw e;
    } finally {
      setLoading(false);
    }
  }

    // 4️⃣ start session
  const startSession = async () => {
    setDialogue([]);
    setQuestionShownAt(Date.now());
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
      // Add AI marker to show this is AI-generated
      setDialogue([{ speaker: "AI 🤖", text: data.question, ai_generated: true }]);
      console.log("🤖 AI-Generated question received from Groq API");
      setQuestionShownAt(Date.now());
      fetchProgress(data.session_id);
    } catch (e) {
      alert("Start session failed: " + e.message);
    } finally {
      setIsStarting(false);
    }
  };

  // 5️⃣ submit answer
  const submitAnswer = async (e) => {
    e?.preventDefault(); // Prevent form submission if called from form submit
    if (!sessionId) return alert("Start a session first.");
    if (!userAnswer.trim()) return alert("Please type an answer or use Skip/Retry.");
    if (isSubmitting) return; // Prevent double submission

    setIsSubmitting(true);
    try {
      // Calculate timing
      const elapsed = Math.round((Date.now() - (questionStart || Date.now())) / 1000);
      const speed = classifySpeed(elapsed);
      
      console.debug('Answer elapsed', elapsed, 'speed', speed);
      
      // Add timing info to dialogue
      const userTurn = { 
        speaker: "You", 
        text: userAnswer, 
        time_spent: elapsed, 
        speed: speed 
      };
      setDialogue((p) => [...p, userTurn]);
      
      // Update dialogue timing state
      setDialogueTiming(prev => [...prev, { elapsed, speed }]);
      
      const data = await safeFetch("/session/turn", {
        method: "POST",
        body: JSON.stringify({ 
          session_id: sessionId, 
          user_answer: userAnswer,
          time_spent_seconds: elapsed,
          time_speed_bucket: speed,
          // TODO: Backend may not accept these fields yet, but including for future use
          client_timestamp: Date.now(),
          question_shown_at: questionShownAt,
          answered_at: new Date().toISOString(),
          time_spent_ms: elapsed * 1000
        }),
      });
      
      setCurrentQuestion(data);
      if (data.question) {
        // Don't add question to dialogue here - backend already handles this
        setQuestionShownAt(Date.now());
        // Reset timer for new question
        setQuestionStart(Date.now());
      }
      setUserAnswer("");
      setHintText("");
      await fetchProgress(sessionId);
      // Refresh dialogue to get the latest from backend
      await refreshDialogue(sessionId);
    } catch (e) {
      alert("Submit failed: " + e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // 6️⃣ get hint (dynamic)
  const getHint = async (e) => {
    e.preventDefault(); // Prevent form submission
    e.stopPropagation(); // Stop event bubbling
    if (!sessionId) return alert("Start a session first.");
    if (isGettingHint) return; // Prevent double clicks
    setIsGettingHint(true);
    try {
      const endpoint = `/hint/${sessionId}`;
      const data = await safeFetch(endpoint);
      setHintText(data.hint);
      if (data.hint) {
        setDialogue((prev) => [...prev, { 
          speaker: "AI (Hint)", 
          text: data.hint,
          timestamp: Date.now()
        }]);
      }
      await fetchProgress(sessionId);
    } catch (e) {
      alert("Hint failed: " + e.message);
    } finally {
      setIsGettingHint(false);
    }
  };

  // 7️⃣ retry question (with improved handling)
  const retryQuestion = async (e) => {
    e.preventDefault(); // Prevent form submission
    if (!sessionId) return alert("Start a session first.");
    setIsRetrying(true);
    try {
      const endpoint = `/retry/${sessionId}`;
      const data = await safeFetch(endpoint, { 
        method: "POST" 
      });
      
      setCurrentQuestion(data);
      if (data.question) {
        setDialogue((prev) => [...prev, {
          speaker: "AI",
          text: data.question,
          timestamp: Date.now(),
          type: data.question_type
        }]);
        setQuestionShownAt(Date.now());
        // Reset timer for new question
        setQuestionStart(Date.now());
      }
      setHintText("");
      setUserAnswer("");
      await fetchProgress(sessionId);
      // Refresh dialogue to get the latest from backend
      await refreshDialogue(sessionId);
    } catch (e) {
      alert("Retry failed: " + e.message);
    } finally {
      setIsRetrying(false);
    }
  };

  // 8️⃣ skip question (with transition handling)
  const skipQuestion = async (e) => {
    e.preventDefault(); // Prevent form submission
    if (!sessionId) return alert("Start a session first.");
    setIsSkipping(true);
    try {
      // Add skipped marker to dialogue
      setDialogue((prev) => [...prev, {
        speaker: "System",
        text: "Question skipped",
        timestamp: Date.now(),
        type: "skip"
      }]);
      
      const endpoint = `/skip/${sessionId}`;
      const data = await safeFetch(endpoint, { 
        method: "POST" 
      });
      
      setCurrentQuestion(data);
      if (data.question) {
        setDialogue((prev) => [...prev, {
          speaker: "AI",
          text: data.question,
          timestamp: Date.now(),
          type: data.question_type
        }]);
        setQuestionShownAt(Date.now());
        // Reset timer for new question
        setQuestionStart(Date.now());
      }
      setHintText("");
      setUserAnswer("");
      await fetchProgress(sessionId);
      // Refresh dialogue to get the latest from backend
      await refreshDialogue(sessionId);
    } catch (e) {
      alert("Skip failed: " + e.message);
    } finally {
      setIsSkipping(false);
    }
  };

  // 9️⃣ reflection (always available)
  const fetchReflection = async (e) => {
    e?.preventDefault(); // Prevent form submission if called from button
    if (!sessionId) return alert("Start a session first.");
    setIsGettingReflection(true);
    try {
      const endpoint = `/reflection/${sessionId}`;
      const data = await safeFetch(endpoint);
      setReflection(data);
      console.log("🤖 AI-Generated reflection received from Groq API");
      
      // Add reflection to dialogue
      if (data.summary_text) {
        setDialogue((prev) => [...prev, {
          speaker: "AI (Reflection)",
          text: data.summary_text,
          timestamp: Date.now(),
          type: "reflection"
        }]);
      }
      
      // Show suggested next concepts
      if (data.suggested_next_concepts?.length) {
        setDialogue((prev) => [...prev, {
          speaker: "System",
          text: `Suggested next concepts: ${data.suggested_next_concepts.join(", ")}`,
          timestamp: Date.now(),
          type: "suggestions"
        }]);
      }
    } catch (e) {
      alert("Reflection failed: " + e.message);
    } finally {
      setIsGettingReflection(false);
    }
  };

  // 🔟 refresh dialogue from backend
  const refreshDialogue = async (sid) => {
    try {
      const id = sid || sessionId;
      if (!id) return;
      
      // Get session data which includes dialogue
      const session = await safeFetch(`/session/${id}`);
      if (session && session.dialogue) {
        setDialogue(session.dialogue);
      }
    } catch (e) {
      console.warn("Dialogue refresh failed:", e.message);
    }
  };

  // 🔟 progress (with error retries)
  const fetchProgress = async (sid) => {
    try {
      const id = sid || sessionId;
      if (!id) return;
      const endpoint = `/progress/${id}`;
      const data = await safeFetch(endpoint);
      
      // Update progress state
      setProgress(data);
      
      // Calculate and log progress percentage
      const percent = Math.min(100, Math.round((data.questions_answered / Math.max(data.total_questions, 1)) * 100));
      console.debug('Progress:', data.questions_answered, '/', data.total_questions, percent + '%');
      
      // Show completion message if all questions answered
      if (data.questions_answered === data.total_questions && !reflection) {
        setDialogue((prev) => {
          // Avoid duplicate completion messages
          if (prev[prev.length - 1]?.type === "completion") return prev;
          return [...prev, {
            speaker: "System",
            text: "✅ Completed for this concept — fetch reflection or Retry/Skip to revisit.",
            timestamp: Date.now(),
            type: "completion"
          }];
        });
      }
    } catch (e) {
      console.warn("Progress fetch:", e.message);
      // Retry once after a short delay
      setTimeout(() => fetchProgress(sid), 1000);
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
          <ConceptSelector
            classGrade={Number(classGrade)}
            subject={subject}
            selectedConcept={concept}
            onConceptChange={setConcept}
            disabled={isStarting}
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

      {/* Question + Controls */}
      {currentQuestion && (
        <section className="mt-6 p-6 rounded-lg border border-blue-100 bg-blue-50">
          <h3 className="text-xl font-semibold mb-4">AI Question</h3>
          <p className="mb-4 text-lg text-gray-800">{currentQuestion.question}</p>

          {/* Answer Form */}
          <form onSubmit={submitAnswer} className="mb-4">
            <div className="flex flex-wrap gap-3 items-center">
              <input
                className="input-field flex-grow min-w-[300px]"
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                placeholder={isCompleted ? "Session completed — use Retry/Skip or Get Reflection" : "Type your answer..."}
                disabled={isCompleted || isSubmitting}
              />
              <button
                type="submit"
                className={`button-primary ${isSubmitting ? 'opacity-75' : ''}`}
                disabled={isCompleted || isSubmitting || !userAnswer.trim()}
              >
                {isSubmitting ? <LoadingSpinner /> : "Submit"}
              </button>
            </div>
          </form>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3 items-center mb-4">
            <button
              type="button"
              className={`button-hint ${isGettingHint ? 'opacity-75' : ''}`}
              onClick={getHint}
              disabled={isGettingHint || isSubmitting}
              title="Get a helpful hint for this question"
            >
              {isGettingHint ? <LoadingSpinner /> : "Get Hint"}
            </button>
            <button
              type="button"
              className={`button-secondary ${isRetrying ? 'opacity-75' : ''}`}
              onClick={retryQuestion}
              disabled={isRetrying || isSubmitting}
              title="Try a different version of this question"
            >
              {isRetrying ? <LoadingSpinner /> : "Retry"}
            </button>
            <button
              type="button"
              className={`button-warning ${isSkipping ? 'opacity-75' : ''}`}
              onClick={skipQuestion}
              disabled={isSkipping || isSubmitting}
              title="Skip this question and move to the next one"
            >
              {isSkipping ? <LoadingSpinner /> : "Skip"}
            </button>
            <button
              type="button"
              className={`button-reflection ${isGettingReflection ? 'opacity-75' : ''} ml-auto`}
              onClick={fetchReflection}
              disabled={isGettingReflection || isSubmitting}
              title="Get a summary of your progress"
            >
              {isGettingReflection ? <LoadingSpinner /> : "Get Reflection"}
            </button>
          </div>

          {/* Status Messages */}
          {hintText && (
            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-100 rounded-lg text-yellow-800 shadow-sm">
              <strong className="font-medium">💡 Hint:</strong> {hintText}
            </div>
          )}
          
          {isCompleted && (
            <div className="mt-4 p-4 bg-green-50 border border-green-100 rounded-lg text-green-800 shadow-sm">
              <p className="font-medium">✅ Concept completed!</p>
              <p className="mt-1 text-sm">Use Get Reflection to review your progress, or Retry/Skip to revisit questions.</p>
            </div>
          )}
          
          {/* Progress Stats - Removed duplicate, using main progress tracker below */}
        </section>
      )}

      {/* Dialogue History */}
      <section className="mt-8">
        <h3 className="text-xl font-semibold mb-4">Dialogue</h3>
        <div className="p-6 bg-white border border-gray-200 rounded-lg shadow-sm min-h-[200px]">
          <DialogueView dialogue={dialogue} />
        </div>
      </section>

      {/* Progress - Single consolidated tracker */}
      {progress && (
        <section className="mt-6 p-6 bg-white border border-gray-200 rounded-lg shadow-sm">
          <h3 className="text-lg font-semibold mb-4 text-gray-800">Session Progress</h3>
          <div className="space-y-4">
            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium text-gray-600">Questions Completed</span>
                <span className="text-sm font-bold text-blue-600">
                  {Math.min(100, Math.round((progress.questions_answered / Math.max(progress.total_questions, 1)) * 100))}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out"
                  style={{ 
                    width: `${Math.min(100, Math.round((progress.questions_answered / Math.max(progress.total_questions, 1)) * 100))}%` 
                  }}
                />
              </div>
              <div className="flex justify-between text-sm text-gray-500">
                <span>{progress.questions_answered} answered</span>
                <span>{progress.total_questions} total</span>
              </div>
            </div>
            
            {/* Additional Progress Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-100">
              <div>
                <span className="text-sm font-medium text-gray-600">Concepts Covered:</span>
                <div className="text-sm text-gray-800 mt-1">
                  {progress.concepts_covered?.join(", ") || "None"}
                </div>
              </div>
              {progress.avg_time_per_question > 0 && (
                <div>
                  <span className="text-sm font-medium text-gray-600">Avg. Time per Question:</span>
                  <div className="text-sm text-gray-800 mt-1">
                    {Math.round(progress.avg_time_per_question)}s
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Reflection */}
      {reflection && (
        <section className="mt-6 p-6 bg-yellow-50 border border-yellow-200 rounded-lg shadow-sm">
          <h3 className="text-lg font-semibold mb-4 text-yellow-800">🤖 AI Reflection</h3>
          <div className="space-y-4">
            <div className="text-gray-800">{reflection.summary_text}</div>
            
            {reflection.focus_areas && reflection.focus_areas.length > 0 && (
              <div>
                <h4 className="font-semibold text-gray-700 mb-2">🎯 Focus Areas for Improvement:</h4>
                <ul className="list-disc list-inside space-y-1 text-gray-700">
                  {reflection.focus_areas.map((area, index) => (
                    <li key={index}>{area}</li>
                  ))}
                </ul>
              </div>
            )}
            
            <div>
              <strong className="text-gray-700">Suggested next concepts:</strong>
              <span className="ml-2 text-gray-600">{reflection.suggested_next_concepts.join(", ")}</span>
            </div>
          </div>
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