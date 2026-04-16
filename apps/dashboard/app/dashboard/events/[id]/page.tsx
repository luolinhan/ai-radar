"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/src/lib/api";
import { ScoreDetailBar } from "@/src/components/ScoreBar";
import { TargetCard } from "@/src/components/TargetCard";

interface EventDetail {
  event_id: string;
  entity_id: string;
  title: string | null;
  content_zh: string | null;
  content_raw: string;
  url: string;
  source: string;
  alert_level: string;
  published_at: string;
  why_it_matters_zh?: string | null;
  topics?: string[];
  targets?: Array<{symbol: string; relation_type: string; confidence?: number; market?: string; name?: string}>;
  impacts?: Array<{symbol: string; direction: string; impact_type: string; confidence: number; hypothesis_text_zh: string}>;
  risks?: Array<{risk_type: string; risk_level: string; risk_text_zh: string; action_suggestion?: string}>;
  score_detail?: {
    final_score: number;
    source_score: number;
    novelty_score: number;
    surprise_score: number;
    tradability_score: number;
    confidence_score: number;
    scoring_reason_zh: string;
    is_actionable: boolean;
  };
}

export default function EventDetailPage() {
  const params = useParams();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadEvent() {
      setLoading(true);
      setError(null);
      try {
        const detail = await api.getEventFull(String(params.id));
        setEvent(detail);
      } catch (err) {
        console.error(err);
        setError("事件详情加载失败。");
      } finally {
        setLoading(false);
      }
    }

    loadEvent();
  }, [params.id]);

  if (loading) return <div className="p-8 text-gray-400">加载中...</div>;
  if (error) return <div className="p-8 text-red-200">{error}</div>;
  if (!event) return <div className="p-8 text-gray-400">事件不存在</div>;

  return (
    <div className="space-y-6">
      <Link href="/dashboard/events" className="text-blue-400 text-sm">返回列表</Link>

      <section className="rounded-2xl border border-blue-500/20 bg-[linear-gradient(135deg,rgba(20,26,44,.95),rgba(15,19,28,.98))] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
              <span className="rounded-full bg-blue-500/15 px-2.5 py-1 text-blue-200 ring-1 ring-blue-400/20">{event.alert_level}</span>
              <span className="rounded-full bg-slate-900/70 px-2.5 py-1">{event.source}</span>
              <span className="rounded-full bg-slate-900/70 px-2.5 py-1">{event.entity_id}</span>
              <span>{new Date(event.published_at).toLocaleString("zh-CN")}</span>
            </div>
            <h1 className="mt-3 text-2xl font-bold text-white">{event.title || "无标题"}</h1>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-300">
              {event.content_zh || event.content_raw}
            </p>
          </div>
          {event.score_detail && (
            <div className="min-w-[220px] rounded-xl border border-yellow-500/20 bg-yellow-500/10 p-4">
              <div className="text-xs text-yellow-200/80">综合评分</div>
              <div className="mt-2 text-4xl font-semibold text-yellow-300">
                {event.score_detail.final_score}
              </div>
              <div className="mt-2 text-xs text-yellow-100/80">
                {event.score_detail.scoring_reason_zh}
              </div>
            </div>
          )}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {event.url && (
            <a
              href={event.url}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 transition hover:border-slate-500 hover:bg-slate-800"
            >
              查看原文
            </a>
          )}
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="space-y-6">
          {event.why_it_matters_zh && (
            <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
              <h2 className="mb-3 text-lg font-semibold text-white">为什么重要</h2>
              <p className="text-sm leading-7 text-slate-300">{event.why_it_matters_zh}</p>
            </div>
          )}

          {event.impacts && event.impacts.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
              <h2 className="mb-3 text-lg font-semibold text-white">影响假设</h2>
              <div className="space-y-3">
                {event.impacts.map((impact, index) => (
                  <div key={`${impact.symbol}-${index}`} className="rounded-lg border border-slate-800 bg-[#0f1117] p-4">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span className="rounded bg-slate-800 px-2 py-1 text-slate-200">{impact.symbol}</span>
                      <span>{impact.direction}</span>
                      <span>{impact.impact_type}</span>
                      <span>置信度 {Math.round(impact.confidence * 100)}%</span>
                    </div>
                    <p className="mt-3 text-sm text-slate-300">{impact.hypothesis_text_zh}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {event.risks && event.risks.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
              <h2 className="mb-3 text-lg font-semibold text-white">风险提示</h2>
              <div className="space-y-3">
                {event.risks.map((risk, index) => (
                  <div key={`${risk.risk_type}-${index}`} className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
                    <div className="text-sm font-medium text-red-100">
                      {risk.risk_type} / {risk.risk_level}
                    </div>
                    <p className="mt-2 text-sm text-red-50/90">{risk.risk_text_zh}</p>
                    {risk.action_suggestion && (
                      <div className="mt-2 text-xs text-red-100/80">建议动作：{risk.action_suggestion}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <aside className="space-y-6">
          {event.targets && event.targets.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
              <h2 className="mb-3 text-lg font-semibold text-white">相关标的</h2>
              <div className="grid gap-3">
                {event.targets.map((target) => (
                  <TargetCard key={target.symbol} target={target} />
                ))}
              </div>
            </div>
          )}

          {event.score_detail && (
            <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
              <h2 className="mb-3 text-lg font-semibold text-white">评分拆解</h2>
              <ScoreDetailBar detail={event.score_detail} />
              <div className="mt-4 text-xs text-slate-400">
                {event.score_detail.is_actionable ? "当前建议可操作。" : "当前建议以观察为主。"}
              </div>
            </div>
          )}

          {event.topics && event.topics.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-[#11131a] p-5">
              <h2 className="mb-3 text-lg font-semibold text-white">主题标签</h2>
              <div className="flex flex-wrap gap-2">
                {event.topics.map((topic) => (
                  <span key={topic} className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
