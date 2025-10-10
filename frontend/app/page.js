"use client"; // 1️⃣ client component

import { useState } from "react";

export default function HomePage() {
  // 2️⃣ state
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

  // 3️⃣ backend base
  const backendBase = "http://127.0.0.1:8000";

  // helper: safe fetch wrapper
  async function safeFetch(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) {
      const body = await res.text().catch(()=>"");
      throw new Error(body || res.statusText);
    }
    return res.json();
  }

  // 4️⃣ start session
  const startSession = async () => {
    setDialogue([]);
    setReflection(null);
    setProgress(null);
    setHintText("");
    setCurrentQuestion(null);
    try {
      const data = await safeFetch(`${backendBase}/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          class_grade: Number(classGrade),
          subject,
          concept_title: concept,
        }),
      });
      setSessionId(data.session_id);
      setCurrentQuestion(data);
      setDialogue([{ speaker: "AI", text: data.question }]);
      fetchProgress(data.session_id);
    } catch (e) {
      alert("Start session failed: " + e.message);
    }
  };

  // 5️⃣ submit answer
  const submitAnswer = async () => {
    if (!sessionId) return alert("Start a session first.");
    if (!userAnswer.trim()) return alert("Please type an answer or use Skip/Retry.");

    try {
      setDialogue((p) => [...p, { speaker: "You", text: userAnswer }]);
      const data = await safeFetch(`${backendBase}/session/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, user_answer: userAnswer }),
      });
      setCurrentQuestion(data);
      if (data.question) setDialogue((p) => [...p, { speaker: "AI", text: data.question }]);
      setUserAnswer("");
      setHintText("");
      fetchProgress(sessionId);
    } catch (e) {
      alert("Submit failed: " + e.message);
    }
  };

  // 6️⃣ get hint (dynamic)
  const getHint = async () => {
    if (!sessionId) return alert("Start a session first.");
    try {
      const data = await safeFetch(`${backendBase}/hint/${sessionId}`);
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
      const data = await safeFetch(`${backendBase}/retry/${sessionId}`, { method: "POST" });
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
      const data = await safeFetch(`${backendBase}/skip/${sessionId}`, { method: "POST" });
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
      const data = await safeFetch(`${backendBase}/reflection/${sessionId}`);
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
      const data = await safeFetch(`${backendBase}/progress/${id}`);
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
    <div style={{ maxWidth: 900, margin: "20px auto", fontFamily: "Inter, Arial, sans-serif", padding: 12 }}>
      <h1>SocraticBSE — MVP</h1>

      {/* Start */}
      <section style={{ padding: 12, border: "1px solid #eee", borderRadius: 8 }}>
        <h3>Start a session</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <input style={inputStyle} value={userId} onChange={(e)=>setUserId(e.target.value)} />
          <select value={classGrade} onChange={(e)=>setClassGrade(e.target.value)}>
            <option value={9}>Class 9</option><option value={10}>Class 10</option><option value={11}>Class 11</option><option value={12}>Class 12</option>
          </select>
          <select value={subject} onChange={(e)=>setSubject(e.target.value)}>
            <option>Physics</option><option>Biology</option><option>Mathematics</option><option>Chemistry</option>
          </select>
          <input style={{...inputStyle, minWidth:220}} value={concept} onChange={(e)=>setConcept(e.target.value)} />
          <button style={{...btn, background:"#2563eb", color:"#fff"}} onClick={startSession}>Start</button>
        </div>
      </section>

      {/* Question + controls */}
      {currentQuestion && (
        <section style={{ padding: 12, marginTop: 12, borderRadius: 8, border: "1px solid #e6f0ff", background:"#fbfdff" }}>
          <h3>AI Question</h3>
          <p style={{ marginBottom: 12 }}>{currentQuestion.question}</p>

          <div style={{ display:"flex", gap:8, alignItems:"center", flexWrap:"wrap" }}>
            <input
              style={inputStyle}
              value={userAnswer}
              onChange={(e)=>setUserAnswer(e.target.value)}
              placeholder={isCompleted ? "Session completed — use Retry/Skip or Get Reflection" : "Type your answer..."}
              disabled={isCompleted}
            />
            <button style={{...btn, background:"#16a34a", color:"#fff"}} onClick={submitAnswer} disabled={isCompleted}>Submit</button>
            <button style={{...btn, background:"#f59e0b"}} onClick={getHint} disabled={isCompleted}>Get Hint</button>
            <button style={{...btn, background:"#0ea5e9", color:"#fff"}} onClick={retryQuestion}>Retry</button>
            <button style={{...btn, background:"#ef4444", color:"#fff"}} onClick={skipQuestion}>Skip</button>
            <button style={{...btn, background:"#fff1b8"}} onClick={fetchReflection}>Get Reflection</button>
          </div>

          {hintText && <div style={{ marginTop: 8, color:"#0b5fff" }}><strong>Hint:</strong> {hintText}</div>}
          {isCompleted && <div style={{ marginTop:8, color:"green" }}>✅ Completed for this concept — fetch reflection or Retry/Skip to revisit.</div>}
        </section>
      )}

      {/* Dialogue */}
      <section style={{ marginTop:12 }}>
        <h3>Dialogue</h3>
        <div style={{ padding:12, background:"#fafafa", borderRadius:8, minHeight:80 }}>
          {dialogue.length === 0 ? <div style={{ color:"#888" }}>No dialogue — start a session.</div> :
            dialogue.map((d,i)=> (<div key={i} style={{ marginBottom:6 }}><strong>{d.speaker}:</strong> <span style={{marginLeft:8}}>{d.text}</span></div>))
          }
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

      <footer style={{ marginTop:18, fontSize:13, color:"#666" }}>
        Frontend: <a href="http://localhost:3000" target="_blank" rel="noreferrer">http://localhost:3000</a> |
        Backend: <a href="http://127.0.0.1:8000" target="_blank" rel="noreferrer">http://127.0.0.1:8000</a> (health: <a href="http://127.0.0.1:8000/health">/health</a>)
      </footer>
    </div>
  );
}