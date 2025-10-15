export function ProgressStats({ progress }) {
  if (!progress) return null;

  const formatTime = (seconds) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatAvgTime = (seconds) => {
    return `${Math.round(seconds)}s`;
  };

  return (
    <div className="mt-4 p-4 bg-white rounded-lg border border-gray-200">
      <h3 className="text-lg font-semibold mb-2">Progress Stats</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-box">
          <div className="text-sm text-gray-600">Questions</div>
          <div className="text-xl font-semibold">
            {progress.questions_answered} / {progress.total_questions}
          </div>
        </div>
        
        <div className="stat-box">
          <div className="text-sm text-gray-600">Total Time</div>
          <div className="text-xl font-semibold">
            {formatTime(progress.total_time)}
          </div>
        </div>

        <div className="stat-box">
          <div className="text-sm text-gray-600">Avg. Time per Question</div>
          <div className="text-xl font-semibold">
            {formatAvgTime(progress.avg_time_per_question)}
          </div>
        </div>

        <div className="stat-box">
          <div className="text-sm text-gray-600">Concepts Covered</div>
          <div className="text-xl font-semibold">
            {progress.concepts_covered?.length || 0}
          </div>
        </div>
      </div>

      {progress.times_per_question?.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-semibold mb-2">Time per Question</h4>
          <div className="flex gap-2 flex-wrap">
            {progress.times_per_question.map((time, idx) => (
              <div key={idx} className="px-2 py-1 bg-blue-50 rounded text-sm">
                Q{idx + 1}: {formatTime(time)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}