export function DialogueView({ dialogue = [] }) {
  if (dialogue.length === 0) {
    return (
      <div className="text-gray-500">No dialogue — start a session.</div>
    );
  }

  return (
    <div className="dialog-container">
      {dialogue.map((d, i) => (
        <div 
          key={i} 
          className={`message-bubble ${d.speaker === 'AI' || d.speaker === 'AI (Hint)' ? 'ai-bubble' : 'user-bubble'}`}
        >
          <div className="font-semibold mb-1">{d.speaker}</div>
          <div>{d.text}</div>
        </div>
      ))}
    </div>
  );
}