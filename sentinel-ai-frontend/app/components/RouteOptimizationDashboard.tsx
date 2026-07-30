"use client";

import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import type { RouteOptimizationResponse, RouteOption } from "@/app/types/route_optimization";
import type { FacilityDetail } from "@/app/types/risk";
import { riskColors, infraColors, scoreGradient, RiskBadge } from "@/app/lib/colors";

const RouteMap = dynamic(() => import("@/app/components/RouteMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[360px] items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.02]">
      <span className="text-[11px] text-slate-600">Loading map…</span>
    </div>
  ),
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function trafficBadgeClass(traffic: string): string {
  if (traffic === "Light")    return "border-emerald-500/20 bg-emerald-500/10 text-emerald-400";
  if (traffic === "Moderate") return "border-yellow-500/20 bg-yellow-500/10 text-yellow-400";
  if (traffic === "Heavy")    return "border-orange-500/20 bg-orange-500/10 text-orange-400";
  if (traffic === "Severe")   return "border-red-500/20 bg-red-500/10 text-red-400";
  return "border-slate-700 bg-slate-800 text-slate-400";
}

function preferenceLabel(p: string): string {
  if (p === "recommended") return "Balanced";
  if (p === "fastest")     return "Fastest";
  if (p === "shortest")    return "Shortest";
  return p;
}

// ── Route selector tab ────────────────────────────────────────────────────────

function RouteTab({
  route,
  active,
  onClick,
}: {
  route: RouteOption;
  active: boolean;
  onClick: () => void;
}) {
  const grad = scoreGradient(route.safety_score);
  return (
    <button
      onClick={onClick}
      className={`relative flex flex-col gap-1 rounded-xl border px-4 py-3 text-left transition-all ${
        active
          ? "border-blue-500/40 bg-blue-500/10"
          : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]"
      }`}
    >
      {route.recommended && (
        <span className="absolute -top-2 left-3 inline-flex items-center gap-1 rounded-full border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 text-[9px] font-bold text-yellow-400">
          ⭐ Recommended
        </span>
      )}
      <span className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {preferenceLabel(route.preference)}
      </span>
      <span className={`text-xl font-extrabold bg-gradient-to-r ${grad.css} bg-clip-text text-transparent`}>
        {route.safety_score}
        <span className="ml-1 text-xs font-normal text-slate-500">/ 100</span>
      </span>
      <span className="text-[10px] text-slate-500">
        {route.distance_km} km · {Math.round(route.duration_min)} min
      </span>
    </button>
  );
}

// ── Route detail card ─────────────────────────────────────────────────────────

function RouteDetailCard({ route }: { route: RouteOption }) {
  const c = riskColors(route.risk_level);

  return (
    <div className={`glass rounded-2xl border p-5 shadow-xl shadow-black/40 ${c.subtle}`}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {preferenceLabel(route.preference)} Route
          </p>
          <p className={`text-2xl font-extrabold ${c.text}`}>
            Safety Score: {route.safety_score}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <RiskBadge level={route.risk_level} />
          {route.recommended && (
            <span className="inline-flex items-center gap-1 rounded-full border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 text-[10px] font-bold text-yellow-400">
              ⭐ Safest Route
            </span>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Distance</p>
          <p className="text-base font-bold text-white">{route.distance_km}<span className="ml-1 text-xs text-slate-500">km</span></p>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Duration</p>
          <p className="text-base font-bold text-white">{Math.round(route.duration_min)}<span className="ml-1 text-xs text-slate-500">min</span></p>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Crime Risk</p>
          <RiskBadge level={route.crime_risk} />
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Weather</p>
          <p className="text-sm font-semibold text-sky-300">{route.weather}</p>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Infrastructure</p>
          <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${infraColors(route.infrastructure)}`}>
            {route.infrastructure}
          </span>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Traffic</p>
          <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${trafficBadgeClass(route.traffic)}`}>
            {route.traffic}
          </span>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Congestion</p>
          <p className="text-base font-bold text-white">{route.congestion_percentage}<span className="ml-1 text-xs text-slate-500">%</span></p>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Delay</p>
          <p className="text-base font-bold text-white">{route.delay_minutes}<span className="ml-1 text-xs text-slate-500">min</span></p>
        </div>
        <div className="glass-highlight rounded-xl p-3">
          <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Traffic Score</p>
          <p className="text-base font-bold text-white">{route.traffic_score}<span className="ml-1 text-xs text-slate-500">/ 100</span></p>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  data: RouteOptimizationResponse;
}

export default function RouteOptimizationDashboard({ data }: Props) {
  const [activeIdx, setActiveIdx] = useState(data.recommended_index);
  const activeRoute = data.routes[activeIdx];

  const mapCoords = useMemo(
    () => activeRoute?.geometry?.coordinates ?? [],
    [activeRoute],
  );

  if (!data.routes.length) {
    return (
      <div className="glass rounded-2xl p-8 text-center text-slate-500">
        No routes could be fetched. Check your ORS API key and try again.
      </div>
    );
  }

  return (
    <div className="animate-scale-in mx-auto w-full max-w-4xl space-y-4">

      {/* Header */}
      <div className="glass rounded-2xl p-5 shadow-xl shadow-black/40">
        <div className="mb-1 flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
            </svg>
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Route Optimization</p>
        </div>
        <p className="text-sm text-slate-400">
          <span className="font-semibold text-white">{data.source}</span>
          <span className="mx-2 text-slate-600">→</span>
          <span className="font-semibold text-white">{data.destination}</span>
          <span className="ml-3 text-slate-600">· {data.routes.length} routes analysed</span>
        </p>
      </div>

      {/* Route selector tabs */}
      <div className={`grid gap-3 ${data.routes.length === 1 ? "grid-cols-1" : data.routes.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
        {data.routes.map((r) => (
          <RouteTab
            key={r.route_index}
            route={r}
            active={r.route_index === activeIdx}
            onClick={() => setActiveIdx(r.route_index)}
          />
        ))}
      </div>

      {/* Active route detail */}
      {activeRoute && <RouteDetailCard route={activeRoute} />}

      {/* Map for active route */}
      {mapCoords.length > 0 && (
        <div className="animate-fade-in-up glass rounded-2xl overflow-hidden shadow-xl shadow-black/40">
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                </svg>
              </div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {preferenceLabel(activeRoute.preference)} Route Map
              </p>
            </div>
            {activeRoute.recommended && (
              <span className="text-[10px] font-bold text-yellow-400">⭐ Recommended</span>
            )}
          </div>
          <div className="h-[360px] w-full">
            <RouteMap
              coordinates={mapCoords}
              source={data.source}
              destination={data.destination}
              crimeLocations={activeRoute.crime_locations}
              facilities={[]}
            />
          </div>
        </div>
      )}

      <p className="animate-fade-in pb-2 text-center text-[11px] text-slate-700">
        Route Optimization by Sentinel AI · Scores based on Crime, Weather, Infrastructure & Traffic
      </p>
    </div>
  );
}
