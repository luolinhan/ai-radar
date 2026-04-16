export interface Event {
  event_id: string;
  source: string;
  entity_id: string;
  title: string | null;
  content_zh: string | null;
  content_raw: string;
  url: string;
  published_at: string;
  alert_level: string;
  topics?: string[];
  companies?: string[];
  products?: string[];
  tickers?: string[];
}

export interface TargetMapping {
  symbol: string;
  name: string | null;
  market: string | null;
  relation_type: string;
  confidence: number;
  direction?: string;
  notes?: string;
}

export interface ImpactHypothesis {
  symbol: string;
  direction: string;
  impact_type: string;
  hypothesis_text_zh: string | null;
  confidence: number;
  time_horizon: string;
}

export interface ScoreDetail {
  source_score: number;
  novelty_score: number;
  surprise_score: number;
  tradability_score: number;
  confidence_score: number;
  final_score: number;
  scoring_reason_zh: string | null;
  is_high_priority: boolean;
  is_actionable: boolean;
}

export interface MarketContext {
  market_session: string | null;
  us_market_open: boolean;
  days_to_earnings: number | null;
  has_macro_event_nearby: boolean;
  macro_event_type: string | null;
  tradability_hint: string | null;
  context_summary_zh: string | null;
}

export interface RiskAlert {
  risk_type: string;
  risk_level: string;
  risk_text_zh: string | null;
  action_suggestion: string | null;
}

export interface EventFullDetail extends Event {
  targets: TargetMapping[];
  impacts: ImpactHypothesis[];
  market_context: MarketContext | null;
  score_detail: ScoreDetail | null;
  risks: RiskAlert[];
  backtest_results: any[];
}

export interface Theme {
  id: string;
  name_en: string;
  name_zh: string | null;
  description: string | null;
  related_symbols: string[];
  event_count_7d: number;
  event_count_30d: number;
  heat_trend: string | null;
  avg_score: number;
}

export interface DashboardOverview {
  top_events: any[];
  top_events_count: number;
  alert_stats: Record<string, number>;
  recent_alerts: any[];
  hot_themes: any[];
  backtest_summary: any;
  watching_events: any[];
  date_range: string;
  last_updated: string | null;
}
