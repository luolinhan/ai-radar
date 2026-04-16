interface TargetCardProps {
  target: {
    symbol: string;
    name?: string | null;
    market?: string | null;
    relation_type: string;
    confidence?: number;
    direction?: string;
  };
}

const directionColors: Record<string, string> = {
  bullish: "text-green-400",
  bearish: "text-red-400",
  neutral: "text-gray-400",
  watch: "text-yellow-400",
};

const directionLabels: Record<string, string> = {
  bullish: "利多",
  bearish: "利空",
  neutral: "中性",
  watch: "观察",
};

const relationLabels: Record<string, string> = {
  direct: "直接",
  beneficiary: "受益",
  competitor: "竞品",
  upstream: "上游",
  downstream: "下游",
  thematic: "主题",
  mentioned: "提及",
};

export function TargetCard({ target }: TargetCardProps) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-white">{target.symbol}</span>
          {target.market && (
            <span className="rounded-full border border-white/10 bg-slate-900/70 px-2 py-0.5 text-[11px] text-slate-500">
              {target.market}
            </span>
          )}
        </div>
        {target.direction && (
          <span className={`text-sm font-medium ${directionColors[target.direction] || "text-gray-400"}`}>
            {directionLabels[target.direction] || target.direction}
          </span>
        )}
      </div>
      
      {target.name && (
        <p className="mb-3 text-xs text-slate-400">{target.name}</p>
      )}
      
      <div className="flex items-center gap-3 text-xs">
        <span className="rounded-full border border-white/10 bg-slate-900/70 px-2.5 py-1 text-slate-300">
          {relationLabels[target.relation_type] || target.relation_type}
        </span>
        {target.confidence !== undefined && (
          <span className="text-slate-500">
            置信度 {Math.round(target.confidence * 100)}%
          </span>
        )}
      </div>
    </div>
  );
}
