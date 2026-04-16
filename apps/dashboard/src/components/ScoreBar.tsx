interface ScoreBarProps {
  score: number;
  maxScore?: number;
  label?: string;
  showValue?: boolean;
  size?: "sm" | "md" | "lg";
}

export function ScoreBar({ score, maxScore = 10, label, showValue = true, size = "md" }: ScoreBarProps) {
  const percentage = Math.min(100, (score / maxScore) * 100);
  
  const getColor = (score: number): string => {
    if (score >= 8) return "from-emerald-400 to-cyan-400";
    if (score >= 6) return "from-amber-300 to-orange-400";
    if (score >= 4) return "from-orange-400 to-amber-500";
    return "from-rose-400 to-red-500";
  };
  
  const heights = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3",
  };
  
  return (
    <div className="flex items-center gap-2">
      {label && <span className="w-16 text-xs text-slate-400">{label}</span>}
      <div className={`flex-1 overflow-hidden rounded-full bg-slate-950/80 ${heights[size]}`}>
        <div 
          className={`${heights[size]} rounded-full bg-gradient-to-r ${getColor(score)} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showValue && (
        <span className="w-8 text-right text-xs text-slate-300">{score.toFixed(1)}</span>
      )}
    </div>
  );
}

interface ScoreDetailProps {
  detail: {
    source_score: number;
    novelty_score: number;
    surprise_score: number;
    tradability_score: number;
    confidence_score: number;
    final_score: number;
    scoring_reason_zh?: string | null;
  };
}

export function ScoreDetailBar({ detail }: ScoreDetailProps) {
  const items = [
    { label: "来源", score: detail.source_score },
    { label: "新意", score: detail.novelty_score },
    { label: "意外", score: detail.surprise_score },
    { label: "可交易", score: detail.tradability_score },
    { label: "置信", score: detail.confidence_score },
  ];
  
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <ScoreBar key={item.label} score={item.score} label={item.label} />
      ))}
      <div className="border-t border-white/10 pt-2">
        <ScoreBar score={detail.final_score} label="综合" size="lg" />
      </div>
      {detail.scoring_reason_zh && (
        <p className="mt-2 text-xs leading-6 text-slate-400">{detail.scoring_reason_zh}</p>
      )}
    </div>
  );
}
