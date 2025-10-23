export function DialogueView({ dialogue = [] }) {
  if (dialogue.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <p>No dialogue yet — start a session to begin the conversation.</p>
      </div>
    );
  }

  const getSpeakerEmoji = (speaker) => {
    if (speaker === 'AI') return '🤖';
    if (speaker === 'AI (Hint)') return '💡';
    return '👤';
  };

  const getSpeedBadge = (speed, timeSpent) => {
    if (!speed) return null;
    
    const badgeClasses = {
      fast: 'text-xs font-medium bg-green-100 text-green-800 px-2 py-0.5 rounded',
      medium: 'text-xs font-medium bg-amber-100 text-amber-800 px-2 py-0.5 rounded',
      slow: 'text-xs font-medium bg-red-100 text-red-800 px-2 py-0.5 rounded'
    };
    
    const speedText = speed.toUpperCase();
    const timeText = timeSpent ? ` • ${timeSpent}s` : '';
    
    return (
      <span className={badgeClasses[speed]} title={`${speedText}${timeText}`}>
        {speedText}{timeText}
      </span>
    );
  };

  return (
    <div className="dialog-container space-y-4">
      {dialogue.map((d, i) => {
        const isAI = d.speaker === 'AI' || d.speaker === 'AI (Hint)';
        return (
          <div 
            key={i} 
            className={`flex ${isAI ? 'justify-start' : 'justify-end'}`}
          >
            <div 
              className={`
                message-bubble max-w-[80%] p-4 rounded-2xl shadow-sm
                ${isAI 
                  ? 'bg-blue-50 text-gray-800 border border-blue-100' 
                  : 'bg-green-50 text-gray-800 border border-green-100'
                }
              `}
            >
              <div className="flex items-center justify-between font-medium mb-2 text-sm">
                <div className="flex items-center gap-2">
                  <span>{getSpeakerEmoji(d.speaker)}</span>
                  <span>{d.speaker}</span>
                </div>
                {!isAI && getSpeedBadge(d.speed, d.time_spent)}
              </div>
              <div className="leading-relaxed whitespace-pre-wrap">{d.text}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}