"use client";

import { useEffect, useId, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { RiskAnalysisResponse, RiskLevel, InfrastructureRating, FacilityDetail, RouteOption, PredictionLevel, PredictionResponse, EmergencyFacilityInfo, EmergencyResponseResult } from "@/app/types/risk";
import { riskColors, infraColors, scoreGradient, RiskBadge } from "@/app/lib/colors";

// Dynamically imported with ssr:false — Leaflet requires window/document.
const RouteMap = dynamic(() => import("@/app/components/RouteMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[360px] items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.02]">
      <span className="text-[11px] text-slate-600">Loading map…</span>
    </div>
  ),
});

// ── Route switcher ──────────────────────────────────────────────────────────────────

function preferenceLabel(p: string) {
  if (p === "recommended") return "Balanced";
  if (p === "fastest")     return "Fastest";
  if (p === "shortest")    return "Shortest";
  return p;
}

function RouteSwitcher({
  routes, activeIndex, onSelect,
}: { routes: RouteOption[]; activeIndex: number; onSelect: (i: number) => void }) {
  if (!routes || routes.length <= 1) return null;
  return (
    <div className="glass rounded-2xl p-5 shadow-xl shadow-black/40">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Route Comparison · {routes.length} routes analysed
      </p>
      <div className={`grid gap-3 ${routes.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
        {routes.map((r) => {
          const grad = scoreGradient(r.safety_score);
          const active = r.route_index === activeIndex;
          return (
            <button
              key={r.route_index}
              onClick={() => onSelect(r.route_index)}
              className={`relative flex flex-col gap-1 rounded-xl border px-4 py-3 text-left transition-all ${
                active ? "border-blue-500/40 bg-blue-500/10" : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]"
              }`}
            >
              {r.recommended && (
                <span className="absolute -top-2.5 left-3 inline-flex items-center gap-1 rounded-full border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 text-[9px] font-bold text-yellow-400">
                  ⭐ Recommended
                </span>
              )}
              <span className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                {preferenceLabel(r.preference)}
              </span>
              <span className={`text-xl font-extrabold bg-gradient-to-r ${grad.css} bg-clip-text text-transparent`}>
                {r.safety_score}<span className="ml-1 text-xs font-normal text-slate-500">/ 100</span>
              </span>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-slate-500">
                <span>{r.distance_km} km</span>
                <span>{Math.round(r.duration_min)} min</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Map legend entry ──────────────────────────────────────────────────────────

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      <span className="text-[10px] text-slate-500">{label}</span>
    </span>
  );
}

// ── Animated counter ──────────────────────────────────────────────────────────

function useCountUp(target: number, duration = 1400) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let rafId: number;
    let start: number | null = null;
    const step = (ts: number) => {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [target, duration]);
  return value;
}

// ── SVG score ring ────────────────────────────────────────────────────────────

function ScoreRing({ score, riskLevel }: { score: number; riskLevel: RiskLevel }) {
  const gradId = useId();
  const animated = useCountUp(score);
  const grad = scoreGradient(score);
  const r = 54;
  const circ = 2 * Math.PI * r;
  const offset = circ - (animated / 100) * circ;

  return (
    <div className="relative flex h-40 w-40 items-center justify-center">
      <svg className="-rotate-90" width="160" height="160" viewBox="0 0 160 160">
        <circle cx="80" cy="80" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={grad.from} />
            <stop offset="100%" stopColor={grad.to} />
          </linearGradient>
        </defs>
        <circle
          cx="80" cy="80" r={r}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.05s linear" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-4xl font-extrabold bg-gradient-to-b ${grad.css} bg-clip-text text-transparent`}>
          {animated}
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">/ 100</span>
      </div>
    </div>
  );
}

// ── Confidence meter ──────────────────────────────────────────────────────────

function ConfidenceMeter({ score }: { score: number }) {
  const confidence = useMemo(
    () => Math.round(72 + (Math.abs(score - 50) / 50) * 20),
    [score]
  );
  const animated = useCountUp(confidence, 1200);
  return (
    <div className="glass-highlight rounded-xl p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">AI Confidence</span>
        <span className="text-sm font-bold text-white">{animated}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className="animate-bar-fill h-full rounded-full bg-gradient-to-r from-blue-500 to-violet-500"
          style={{ width: `${confidence}%` }}
        />
      </div>
      <p className="mt-1.5 text-[10px] text-slate-600">
        Based on {score >= 75 || score <= 25 ? "strong" : "moderate"} signal convergence across all dimensions
      </p>
    </div>
  );
}

// ── Generic breakdown card ────────────────────────────────────────────────────

interface BreakdownCardProps {
  label: string;
  icon: React.ReactNode;
  iconBg: string;
  value: React.ReactNode;
  barPercent?: number;
  barColor?: string;
  delay: string;
}

function BreakdownCard({ label, icon, iconBg, value, barPercent, barColor, delay }: BreakdownCardProps) {
  return (
    <div className={`animate-fade-in-up glass-highlight rounded-xl p-4 ${delay}`}>
      <div className="mb-3 flex items-center gap-2.5">
        <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${iconBg}`}>{icon}</div>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      </div>
      <div className="text-sm font-semibold text-white">{value}</div>
      {barPercent !== undefined && barColor && (
        <div className="mt-2.5 h-1 overflow-hidden rounded-full bg-white/[0.05]">
          <div className={`animate-bar-fill h-full rounded-full ${barColor}`} style={{ width: `${barPercent}%` }} />
        </div>
      )}
    </div>
  );
}

// ── Route Information card ────────────────────────────────────────────────────

function RouteInfoCard({ data }: { data: RiskAnalysisResponse }) {
  const hasRoute = data.route_live && data.distance_km != null && data.duration_min != null;

  return (
    <div className="animate-fade-in-up delay-100 glass rounded-2xl p-5 shadow-xl shadow-black/40">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
            </svg>
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Route Information</p>
        </div>
        {hasRoute && (
          <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold text-blue-400">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
            Live
          </span>
        )}
      </div>

      {/* Route path */}
      <div className="mb-4 flex items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3.5 py-2.5">
        <span className="max-w-[38%] truncate text-sm font-semibold text-white">{data.source}</span>
        <svg className="mx-1 h-3.5 w-3.5 shrink-0 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
        </svg>
        <span className="max-w-[38%] truncate text-sm font-semibold text-white">{data.destination}</span>
      </div>

      {/* Distance + Duration */}
      <div className="grid grid-cols-2 gap-3">
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Distance</p>
          {hasRoute ? (
            <p className="text-xl font-extrabold text-white">
              {data.distance_km!.toFixed(1)}
              <span className="ml-1 text-xs font-medium text-slate-500">km</span>
            </p>
          ) : (
            <p className="text-sm text-slate-600">Unavailable</p>
          )}
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Est. Travel Time</p>
          {hasRoute ? (
            <p className="text-xl font-extrabold text-white">
              {Math.round(data.duration_min!)}
              <span className="ml-1 text-xs font-medium text-slate-500">min</span>
            </p>
          ) : (
            <p className="text-sm text-slate-600">Unavailable</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Weather card ──────────────────────────────────────────────────────────────

function WeatherCard({ data }: { data: RiskAnalysisResponse }) {
  const isLive = data.weather_live;

  return (
    <div className="animate-fade-in-up delay-200 glass rounded-2xl p-5 shadow-xl shadow-black/40">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-500/10 text-sky-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
            </svg>
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Weather Conditions</p>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${isLive ? "border-sky-500/20 bg-sky-500/10 text-sky-400" : "border-slate-700 bg-slate-800 text-slate-500"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${isLive ? "bg-sky-400" : "bg-slate-500"}`} />
          {isLive ? "Live" : "Mock"}
        </span>
      </div>

      {/* Condition headline */}
      <p className="mb-4 text-lg font-bold text-sky-300">{data.weather}</p>

      {/* Detail grid — only rendered when live data is present */}
      {isLive && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {data.temperature_c != null && (
            <div className="glass-highlight rounded-xl p-3">
              <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Temperature</p>
              <p className="text-base font-bold text-white">{data.temperature_c.toFixed(1)}<span className="ml-0.5 text-xs text-slate-500">°C</span></p>
            </div>
          )}
          {data.feels_like_c != null && (
            <div className="glass-highlight rounded-xl p-3">
              <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Feels Like</p>
              <p className="text-base font-bold text-white">{data.feels_like_c.toFixed(1)}<span className="ml-0.5 text-xs text-slate-500">°C</span></p>
            </div>
          )}
          {data.humidity_pct != null && (
            <div className="glass-highlight rounded-xl p-3">
              <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Humidity</p>
              <p className="text-base font-bold text-white">{data.humidity_pct}<span className="ml-0.5 text-xs text-slate-500">%</span></p>
            </div>
          )}
          {data.wind_kph != null && (
            <div className="glass-highlight rounded-xl p-3">
              <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Wind Speed</p>
              <p className="text-base font-bold text-white">{data.wind_kph.toFixed(1)}<span className="ml-0.5 text-xs text-slate-500">km/h</span></p>
            </div>
          )}
          {data.visibility_km != null && (
            <div className="glass-highlight rounded-xl p-3">
              <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Visibility</p>
              <p className="text-base font-bold text-white">{data.visibility_km.toFixed(1)}<span className="ml-0.5 text-xs text-slate-500">km</span></p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Traffic card ─────────────────────────────────────────────────────────────

function trafficBadgeClass(traffic: string): string {
  if (traffic === "Light")    return "border-emerald-500/20 bg-emerald-500/10 text-emerald-400";
  if (traffic === "Moderate") return "border-yellow-500/20 bg-yellow-500/10 text-yellow-400";
  if (traffic === "Heavy")    return "border-orange-500/20 bg-orange-500/10 text-orange-400";
  if (traffic === "Severe")   return "border-red-500/20 bg-red-500/10 text-red-400";
  return "border-slate-700 bg-slate-800 text-slate-400";
}

function trafficBarColor(traffic: string): string {
  if (traffic === "Light")    return "bg-emerald-500";
  if (traffic === "Moderate") return "bg-yellow-500";
  if (traffic === "Heavy")    return "bg-orange-500";
  if (traffic === "Severe")   return "bg-red-500";
  return "bg-slate-500";
}

function TrafficCard({ data }: { data: RiskAnalysisResponse }) {
  const isLive = data.traffic_live;
  const badgeClass = trafficBadgeClass(data.traffic ?? "Unknown");
  const barColor   = trafficBarColor(data.traffic ?? "Unknown");
  const congestion = data.congestion_percentage ?? 0;

  return (
    <div className="animate-fade-in-up delay-300 glass rounded-2xl p-5 shadow-xl shadow-black/40">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
            </svg>
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Traffic Conditions</p>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${isLive ? "border-amber-500/20 bg-amber-500/10 text-amber-400" : "border-slate-700 bg-slate-800 text-slate-500"}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${isLive ? "bg-amber-400" : "bg-slate-500"}`} />
          {isLive ? "Live" : "Mock"}
        </span>
      </div>

      {/* Status + score row */}
      <div className="mb-4 flex items-center justify-between">
        <span className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-bold ${badgeClass}`}>
          {data.traffic ?? "Unknown"}
        </span>
        <div className="text-right">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Traffic Score</p>
          <p className="text-xl font-extrabold text-white">{data.traffic_score ?? 50}<span className="ml-1 text-xs text-slate-500">/ 100</span></p>
        </div>
      </div>

      {/* Congestion bar */}
      <div className="mb-4">
        <div className="mb-1 flex items-center justify-between">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Congestion</span>
          <span className="text-xs font-bold text-white">{congestion}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
          <div className={`animate-bar-fill h-full rounded-full ${barColor}`} style={{ width: `${congestion}%` }} />
        </div>
      </div>

      {/* Detail grid */}
      <div className="grid grid-cols-3 gap-2">
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Avg Speed</p>
          <p className="text-base font-bold text-white">{data.average_speed_kph ?? 0}<span className="ml-0.5 text-xs text-slate-500">km/h</span></p>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Delay</p>
          <p className="text-base font-bold text-white">{data.delay_minutes ?? 0}<span className="ml-0.5 text-xs text-slate-500">min</span></p>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Incidents</p>
          <p className="text-base font-bold text-white">{data.traffic_incidents ?? 0}</p>
        </div>
      </div>
    </div>
  );
}

// ── Incident Prediction card ─────────────────────────────────────────────────

function predBadge(level: PredictionLevel): string {
  if (level === "Low")      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
  if (level === "Moderate") return "border-yellow-500/30 bg-yellow-500/10 text-yellow-400";
  if (level === "Medium")   return "border-yellow-500/30 bg-yellow-500/10 text-yellow-400";
  return "border-red-500/30 bg-red-500/10 text-red-400";
}

function PredBadge({ level }: { level: PredictionLevel }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-bold ${predBadge(level)}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${
        level === "Low" ? "bg-emerald-400" : level === "High" ? "bg-red-400" : "bg-yellow-400"
      }`} />
      {level}
    </span>
  );
}

function IncidentPredictionCard({ prediction }: { prediction: PredictionResponse }) {
  return (
    <div className="animate-fade-in-up delay-200 glass rounded-2xl p-5 shadow-xl shadow-black/40">
      <div className="mb-5 flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-violet-500/10 text-violet-400">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">AI Incident Prediction</p>
          <p className="text-xs text-slate-600">Forward-looking analysis based on current conditions</p>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Accident Risk</p>
          <PredBadge level={prediction.accident_probability} />
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Traffic Delay</p>
          <PredBadge level={prediction.traffic_delay_probability} />
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Crime Probability</p>
          <PredBadge level={prediction.crime_probability} />
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Weather Impact</p>
          <PredBadge level={prediction.weather_impact} />
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Overall Future Risk</p>
          <PredBadge level={prediction.overall_future_risk} />
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Recommended Departure</p>
          <p className="text-xs font-semibold text-white">{prediction.recommended_departure}</p>
        </div>
      </div>

      <div className="rounded-xl border border-violet-500/10 bg-violet-500/5 p-3.5">
        <div className="mb-1.5 flex items-center gap-1.5">
          <svg className="h-3.5 w-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-400">Prediction</span>
        </div>
        <p className="text-sm leading-relaxed text-slate-400">{prediction.ai_recommendation}</p>
      </div>
    </div>
  );
}

// ── Emergency Response card ─────────────────────────────────────────────────

function EmergencyFacilityRow({
  icon, iconBg, label, facility,
}: {
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  facility: EmergencyFacilityInfo;
}) {
  return (
    <div className="glass-highlight rounded-xl p-3.5">
      <div className="mb-2 flex items-center gap-2">
        <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg ${iconBg}`}>{icon}</div>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      </div>
      {facility.available ? (
        <>
          <p className="truncate text-sm font-semibold text-white">{facility.name || label}</p>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-slate-500">
            {facility.distance_km != null && (
              <span>{facility.distance_km.toFixed(1)} km away</span>
            )}
            {facility.eta_minutes != null && (
              <span className="font-semibold text-amber-400">ETA {facility.eta_minutes} min</span>
            )}
          </div>
        </>
      ) : (
        <p className="text-xs text-slate-600">Not found nearby</p>
      )}
    </div>
  );
}

function EmergencyResponseCard({ er }: { er: EmergencyResponseResult }) {
  return (
    <div className="animate-fade-in-up delay-200 glass rounded-2xl border border-red-500/20 p-5 shadow-xl shadow-black/40">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-red-500/10 text-red-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0M3.124 7.5A8.969 8.969 0 015.292 3m13.416 0a8.969 8.969 0 012.168 4.5" />
            </svg>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Emergency Response</p>
            <p className="text-xs text-red-400/80">{er.trigger_reason}</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-0.5 text-[10px] font-bold text-red-400">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />
          {er.status}
        </span>
      </div>

      {/* Nearest facilities */}
      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <EmergencyFacilityRow
          label="Police Station"
          iconBg="bg-blue-500/10 text-blue-400"
          facility={er.nearest_police}
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            </svg>
          }
        />
        <EmergencyFacilityRow
          label="Hospital"
          iconBg="bg-emerald-500/10 text-emerald-400"
          facility={er.nearest_hospital}
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <EmergencyFacilityRow
          label="Fire Station"
          iconBg="bg-orange-500/10 text-orange-400"
          facility={er.nearest_fire_station}
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" />
            </svg>
          }
        />
      </div>

      {/* Emergency contact numbers */}
      <div className="rounded-xl border border-red-500/10 bg-red-500/5 p-3.5">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-red-400">Emergency Contacts</p>
        <div className="flex flex-wrap gap-3">
          {Object.entries(er.emergency_contacts).map(([service, number]) => (
            <a
              key={service}
              href={`tel:${number}`}
              className="flex items-center gap-1.5 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-xs font-bold text-red-300 transition hover:bg-red-500/20"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              {service}: {number}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── AI Recommendation panel ───────────────────────────────────────────────────

function RecommendationPanel({ data }: { data: RiskAnalysisResponse }) {
  const c = riskColors(data.risk_level);
  return (
    <div className={`animate-fade-in-up delay-500 glass rounded-2xl border p-5 ${c.subtle}`}>
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 text-blue-400">
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">AI Recommendation</p>
          <p className={`text-base font-bold ${c.text}`}>{data.recommendation}</p>
        </div>
      </div>
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
        <div className="mb-1.5 flex items-center gap-1.5">
          <svg className="h-3.5 w-3.5 text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
          </svg>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-400">Analysis</span>
        </div>
        <p className="text-sm leading-relaxed text-slate-400">{data.reason}</p>
      </div>
    </div>
  );
}

// ── Risk factor row ───────────────────────────────────────────────────────────

function RiskFactorRow({ label, level, delay }: { label: string; level: RiskLevel; delay: string }) {
  const c = riskColors(level);
  const pct = level === "Low" ? 25 : level === "Medium" ? 55 : level === "High" ? 78 : 95;
  return (
    <div className={`animate-fade-in ${delay}`}>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs text-slate-500">{label}</span>
        <RiskBadge level={level} />
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-white/[0.05]">
        <div className={`animate-bar-fill h-full rounded-full ${c.bar}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Main dashboard ────────────────────────────────────────────────────────────

interface ResultDashboardProps {
  data: RiskAnalysisResponse;
  source: string;
  destination: string;
}

function deriveInfraRating(data: RiskAnalysisResponse): InfrastructureRating {
  if (data.infrastructure && data.infrastructure !== "Unknown") return data.infrastructure;
  // Derive from available facility counts when backend returns Unknown
  const score = Math.min(data.nearby_police * 20 + data.nearby_hospitals * 20, 100);
  if (score >= 80) return "Excellent";
  if (score >= 60) return "Good";
  if (score >= 20) return "Fair";
  return "Poor";
}

export default function ResultDashboard({ data, source, destination }: ResultDashboardProps) {
  const [activeRouteIdx, setActiveRouteIdx] = useState(data.recommended_index ?? 0);

  const activeRoute = data.routes?.[activeRouteIdx];
  const mapCoords = activeRoute?.geometry?.coordinates ?? data.geometry?.coordinates ?? [];
  const mapCrimeLocations = activeRoute?.crime_locations ?? data.crime_locations;

  const policeBar   = Math.min(100, data.nearby_police   * 20);
  const hospitalBar = Math.min(100, data.nearby_hospitals * 16);
  const infraRating = useMemo(() => deriveInfraRating(data), [data]);

  const displaySource      = data.source      || source;
  const displayDestination = data.destination || destination;

  const allFacilities = useMemo<FacilityDetail[]>(
    () => [
      ...(data.facility_police         ?? []),
      ...(data.facility_hospitals       ?? []),
      ...(data.facility_fire_stations   ?? []),
      ...(data.facility_petrol_pumps    ?? []),
      ...(data.facility_pharmacies      ?? []),
      ...(data.facility_metro_stations  ?? []),
    ],
    [data],
  );

  return (
    <div className="animate-scale-in mx-auto w-full max-w-4xl space-y-4">

      {/* ── Route Switcher (only when multiple routes) ── */}
      {data.routes && data.routes.length > 1 && (
        <RouteSwitcher
          routes={data.routes}
          activeIndex={activeRouteIdx}
          onSelect={setActiveRouteIdx}
        />
      )}

      {/* ── Row 1: Safety score + Risk breakdown ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {/* Score card */}
        <div className="glass rounded-2xl p-6 shadow-xl shadow-black/40 sm:col-span-1">
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Safety Score</p>
          <div className="flex flex-col items-center gap-3">
            <ScoreRing score={data.safety_score} riskLevel={data.risk_level} />
            <div className="text-center">
              <RiskBadge level={data.risk_level} />
              <p className="mt-1.5 text-[11px] text-slate-600">
                {displaySource} → {displayDestination}
              </p>
            </div>
          </div>
        </div>

        {/* Risk factors + confidence */}
        <div className="glass rounded-2xl p-5 shadow-xl shadow-black/40 sm:col-span-2">
          <p className="mb-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Risk Factor Breakdown
          </p>
          <div className="flex flex-col gap-3">
            <RiskFactorRow label="Crime Risk"   level={data.crime_risk}  delay="delay-100" />
            <RiskFactorRow label="Overall Risk" level={data.risk_level}  delay="delay-200" />
          </div>
          <div className="my-4 h-px bg-white/[0.05]" />
          <ConfidenceMeter score={data.safety_score} />
        </div>
      </div>

      {/* ── Row 2: Route Information + Weather ── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <RouteInfoCard data={data} />
        <WeatherCard   data={data} />
      </div>

      {/* ── Row 3: Traffic Analysis ── */}
      <TrafficCard data={data} />

      {/* ── Row 3b: AI Incident Prediction ── */}
      {data.prediction && <IncidentPredictionCard prediction={data.prediction} />}

      {/* ── Row 3c: Emergency Response (High/Critical risk or SOS) ── */}
      {data.emergency_response?.activated && (
        <EmergencyResponseCard er={data.emergency_response} />
      )}

      {/* ── Row 4: Interactive Route Map ── */}
      <div className="animate-fade-in-up delay-300 glass rounded-2xl shadow-xl shadow-black/40 overflow-hidden">
        {/* Card header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
              </svg>
            </div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Route Map</p>
          </div>
          <span className="text-[10px] text-slate-600">
            {displaySource} → {displayDestination}
          </span>
        </div>
        {/* Map legend */}
        <div className="flex flex-wrap gap-3 px-5 pb-3">
          <LegendDot color="bg-blue-500"   label="Route" />
          <LegendDot color="bg-red-500"    label="Critical crime" />
          <LegendDot color="bg-orange-500" label="High crime" />
          <LegendDot color="bg-yellow-400" label="Medium/Low crime" />
          <LegendDot color="bg-blue-400"   label="Police" />
          <LegendDot color="bg-emerald-500" label="Hospital" />
          <LegendDot color="bg-violet-500" label="Pharmacy" />
          <LegendDot color="bg-slate-400"  label="Other facility" />
        </div>
        {/* Map */}
        <div className="h-[360px] w-full">
          {mapCoords.length > 0 ? (
            <RouteMap
              coordinates={mapCoords}
              source={displaySource}
              destination={displayDestination}
              crimeLocations={mapCrimeLocations}
              facilities={allFacilities}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              {data.routes && data.routes.length === 1 ? "Only one route available." : "No route available."}
            </div>
          )}
        </div>
      </div>

      {/* ── Row 5: Emergency services + Infrastructure ── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <BreakdownCard
          label="Infrastructure"
          delay="delay-100"
          iconBg="bg-violet-500/10 text-violet-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21" />
            </svg>
          }
          value={
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${infraColors(infraRating)}`}>
              {infraRating}
            </span>
          }
        />

        <BreakdownCard
          label="Police Stations"
          delay="delay-200"
          iconBg="bg-blue-500/10 text-blue-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            </svg>
          }
          value={
            <span className="flex items-baseline gap-1">
              <span className="text-2xl font-extrabold text-white">{data.nearby_police}</span>
              <span className="text-xs text-slate-600">nearby</span>
            </span>
          }
          barPercent={policeBar}
          barColor="bg-blue-500"
        />

        <BreakdownCard
          label="Hospitals"
          delay="delay-300"
          iconBg="bg-emerald-500/10 text-emerald-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          value={
            <span className="flex items-baseline gap-1">
              <span className="text-2xl font-extrabold text-white">{data.nearby_hospitals}</span>
              <span className="text-xs text-slate-600">nearby</span>
            </span>
          }
          barPercent={hospitalBar}
          barColor="bg-emerald-500"
        />

        <BreakdownCard
          label="Crime Risk"
          delay="delay-400"
          iconBg="bg-rose-500/10 text-rose-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          }
          value={<RiskBadge level={data.crime_risk} />}
        />
      </div>

      {/* ── Row 6: Crime + Extended infrastructure counts ── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <BreakdownCard
          label="Crime Hotspots"
          delay="delay-100"
          iconBg="bg-rose-500/10 text-rose-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
            </svg>
          }
          value={
            <span className="flex items-baseline gap-1">
              <span className="text-2xl font-extrabold text-white">{data.nearby_crimes ?? 0}</span>
              <span className="text-xs text-slate-600">areas</span>
            </span>
          }
          barPercent={Math.min(100, (data.nearby_crimes ?? 0) * 10)}
          barColor="bg-rose-500"
        />

        <BreakdownCard
          label="Fire Stations"
          delay="delay-200"
          iconBg="bg-orange-500/10 text-orange-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-2.133-1A3.75 3.75 0 0012 18z" />
            </svg>
          }
          value={
            <span className="flex items-baseline gap-1">
              <span className="text-2xl font-extrabold text-white">{data.nearby_fire_stations ?? 0}</span>
              <span className="text-xs text-slate-600">nearby</span>
            </span>
          }
          barPercent={Math.min(100, (data.nearby_fire_stations ?? 0) * 20)}
          barColor="bg-orange-500"
        />

        <BreakdownCard
          label="Petrol Pumps"
          delay="delay-300"
          iconBg="bg-yellow-500/10 text-yellow-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
            </svg>
          }
          value={
            <span className="flex items-baseline gap-1">
              <span className="text-2xl font-extrabold text-white">{data.nearby_petrol_pumps ?? 0}</span>
              <span className="text-xs text-slate-600">nearby</span>
            </span>
          }
          barPercent={Math.min(100, (data.nearby_petrol_pumps ?? 0) * 10)}
          barColor="bg-yellow-500"
        />

        <BreakdownCard
          label="Pharmacies"
          delay="delay-400"
          iconBg="bg-violet-500/10 text-violet-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
          value={
            <span className="flex items-baseline gap-1">
              <span className="text-2xl font-extrabold text-white">{data.nearby_pharmacies ?? 0}</span>
              <span className="text-xs text-slate-600">nearby</span>
            </span>
          }
          barPercent={Math.min(100, (data.nearby_pharmacies ?? 0) * 10)}
          barColor="bg-violet-500"
        />

        <BreakdownCard
          label="Metro Stations"
          delay="delay-500"
          iconBg="bg-cyan-500/10 text-cyan-400"
          icon={
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
            </svg>
          }
          value={
            <span className="flex items-baseline gap-1">
              <span className="text-2xl font-extrabold text-white">{data.nearby_metro_stations ?? 0}</span>
              <span className="text-xs text-slate-600">nearby</span>
            </span>
          }
          barPercent={Math.min(100, (data.nearby_metro_stations ?? 0) * 20)}
          barColor="bg-cyan-500"
        />
      </div>

      {/* ── Row 7: AI Recommendation ── */}
      <RecommendationPanel data={data} />

      {/* ── Footer ── */}
      <p className="animate-fade-in delay-700 pb-2 text-center text-[11px] text-slate-700">
        Analysis generated by Sentinel AI Risk Assessment Agent · Results are indicative
      </p>
    </div>
  );
}
