export function DialogueView({ dialogue = [] }) {
  if (dialogue.length === 0) {
    return (
      <div style={{ color: "#888" }}>No dialogue — start a session.</div>
    );
  }

  return dialogue.map((d, i) => (
    <div key={i} style={{ marginBottom: 6 }}>
      <strong>{d.speaker}:</strong> 
      <span style={{ marginLeft: 8 }}>{d.text}</span>
    </div>
  ));
}