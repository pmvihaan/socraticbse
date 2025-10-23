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

  const calculateProgress = () => {
    return (progress.questions_answered / progress.total_questions) * 100;
  };

  const getStatIcon = (type) => {
    switch (type) {
      case 'questions': return '📝';
      case 'time': return '⏱️';
      case 'average': return '⚡';
      case 'concepts': return '🎯';
      default: return '📊';
    }
  };

  return (
    <div className="mt-4 p-6 bg-white rounded-xl border border-gray-200 shadow-sm transition-all hover:shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Progress Stats</h3>
        <div className="text-sm text-gray-500">
          {Math.round(calculateProgress())}% Complete
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-gray-100 rounded-full mb-6">
        <div 
          className="h-full bg-blue-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${calculateProgress()}%` }}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div className="stat-box p-4 rounded-lg bg-blue-50 border border-blue-100 transition-all hover:shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <span>{getStatIcon('questions')}</span>
            <div className="text-sm font-medium text-gray-600">Questions</div>
          </div>
          <div className="text-2xl font-bold text-blue-700">
            {progress.questions_answered} <span className="text-lg text-blue-400">/ {progress.total_questions}</span>
          </div>
        </div>
        
        <div className="stat-box p-4 rounded-lg bg-green-50 border border-green-100 transition-all hover:shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <span>{getStatIcon('time')}</span>
            <div className="text-sm font-medium text-gray-600">Total Time</div>
          </div>
          <div className="text-2xl font-bold text-green-700">
            {formatTime(progress.total_time)}
          </div>
        </div>

        <div className="stat-box p-4 rounded-lg bg-purple-50 border border-purple-100 transition-all hover:shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <span>{getStatIcon('average')}</span>
            <div className="text-sm font-medium text-gray-600">Avg. Time/Q</div>
          </div>
          <div className="text-2xl font-bold text-purple-700">
            {formatAvgTime(progress.avg_time_per_question)}
          </div>
        </div>

        <div className="stat-box p-4 rounded-lg bg-orange-50 border border-orange-100 transition-all hover:shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <span>{getStatIcon('concepts')}</span>
            <div className="text-sm font-medium text-gray-600">Concepts</div>
          </div>
          <div className="text-2xl font-bold text-orange-700">
            {progress.concepts_covered?.length || 0}
          </div>
        </div>
      </div>

      {progress.times_per_question?.length > 0 && (
        <div className="mt-6 p-4 rounded-lg bg-gray-50 border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-gray-700">Time per Question</h4>
            <div className="text-xs text-gray-500">
              Click for details
            </div>
          </div>
          
          <div className="grid gap-3">
            {progress.times_per_question.map((time, idx) => {
              const maxTime = Math.max(...progress.times_per_question);
              const percentage = (time / maxTime) * 100;
              const getTimeBarColor = (percent) => {
                if (percent <= 33) return 'bg-green-400';
                if (percent <= 66) return 'bg-yellow-400';
                return 'bg-red-400';
              };
              
              return (
                <div 
                  key={idx} 
                  className="group relative p-2 bg-white rounded-lg border border-gray-100 hover:shadow-sm transition-all cursor-pointer"
                  title={`Question ${idx + 1} took ${formatTime(time)}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-sm font-medium text-gray-700">Q{idx + 1}</div>
                    <div className="text-sm text-gray-500">{formatTime(time)}</div>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${getTimeBarColor(percentage)} transition-all duration-500 ease-out`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <div className="absolute inset-0 bg-blue-50 opacity-0 group-hover:opacity-10 rounded-lg transition-opacity" />
                </div>
              );
            })}
          </div>
          
          {/* Legend */}
          <div className="mt-4 flex items-center justify-end gap-4 text-xs text-gray-500">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-400" />
              Fast
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-yellow-400" />
              Average
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              Slow
            </div>
          </div>
        </div>
      )}
    </div>
  );
}