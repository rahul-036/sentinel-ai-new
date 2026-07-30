"use client";

import { useEffect, useState } from "react";

interface Step {
  id: string;
  label: string;
  sublabel: string;
  icon: React.ReactNode;
  color: string;
  duration: number; // ms this step stays "active"
}

const STEPS: Step[] = [
  {
    id: "crime",
    label: "Crime Analysis",
    sublabel: "Scanning incident reports & historical data",
    color: "text-red-400",
    duration: 700,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.248-8.25-3.286z" />
      </svg>
    ),
  },
  {
    id: "weather",
    label: "Weather Conditions",
    sublabel: "Fetching real-time atmospheric data",
    color: "text-sky-400",
    duration: 600,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
      </svg>
    ),
  },
  {
    id: "traffic",
    label: "Traffic & Route",
    sublabel: "Evaluating congestion & road conditions",
    color: "text-amber-400",
    duration: 650,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
      </svg>
    ),
  },
  {
    id: "infrastructure",
    label: "Infrastructure",
    sublabel: "Assessing road quality & emergency access",
    color: "text-violet-400",
    duration: 600,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z" />
      </svg>
    ),
  },
  {
    id: "ai",
    label: "AI Decision Engine",
    sublabel: "Synthesising all signals into final score",
    color: "text-emerald-400",
    duration: 500,
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
    ),
  },
];

type StepStatus = "pending" | "active" | "done";

export default function AnalysisLoader({ source, destination }: { source: string; destination: string }) {
  const [statuses, setStatuses] = useState<StepStatus[]>(STEPS.map(() => "pending"));
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let elapsed = 0;
    const total = STEPS.reduce((s, st) => s + st.duration, 0);

    async function run() {
      for (let i = 0; i < STEPS.length; i++) {
        if (cancelled) return;
        // Mark current step active
        setStatuses((prev) => prev.map((s, idx) => idx === i ? "active" : s));

        const step = STEPS[i];
        const tickMs = 30;
        const ticks = Math.floor(step.duration / tickMs);
        for (let t = 0; t < ticks; t++) {
          if (cancelled) return;
          await new Promise((r) => setTimeout(r, tickMs));
          elapsed += tickMs;
          setProgress(Math.min(98, Math.round((elapsed / total) * 100)));
        }

        if (cancelled) return;
        setStatuses((prev) => prev.map((s, idx) => idx === i ? "done" : s));
      }
    }

    run();
    return () => { cancelled = true; };
  }, []);

  const activeIdx = statuses.findLastIndex((s) => s === "active");

  return (
    <div className="animate-scale-in mx-auto w-full max-w-xl">
      <div className="glass rounded-2xl p-6 shadow-2xl shadow-black/50">
        {/* Header */}
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h3 className="text-sm font-bold text-white">Analyzing Route</h3>
            <p className="mt-0.5 text-xs text-slate-500">
              <span className="text-blue-400">{source}</span>
              <span className="mx-1.5 text-slate-700">→</span>
              <span className="text-violet-400">{destination}</span>
            </p>
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-400" />
            <span className="text-xs font-semibold text-blue-400">{progress}%</span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-6 h-1 overflow-hidden rounded-full bg-white/[0.06]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-blue-500 via-violet-500 to-emerald-500 transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Steps */}
        <div className="flex flex-col gap-2">
          {STEPS.map((step, i) => {
            const status = statuses[i];
            const isActive = status === "active";
            const isDone = status === "done";
            const isPending = status === "pending";

            return (
              <div
                key={step.id}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition-all duration-300 ${
                  isActive
                    ? "border border-white/[0.08] bg-white/[0.04]"
                    : "border border-transparent"
                } ${isPending ? "opacity-30" : "opacity-100"}`}
              >
                {/* Icon / status indicator */}
                <div className={`relative flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-all duration-300 ${
                  isDone
                    ? "bg-emerald-500/15 text-emerald-400"
                    : isActive
                    ? `bg-white/[0.06] ${step.color}`
                    : "bg-white/[0.03] text-slate-700"
                }`}>
                  {isDone ? (
                    <svg className="animate-step-done h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : (
                    <>
                      {step.icon}
                      {isActive && (
                        <span className="absolute inset-0 animate-ping rounded-lg bg-current opacity-10" />
                      )}
                    </>
                  )}
                </div>

                {/* Labels */}
                <div className="flex-1 min-w-0">
                  <p className={`text-xs font-semibold transition-colors duration-200 ${
                    isDone ? "text-slate-400" : isActive ? "text-white" : "text-slate-600"
                  }`}>
                    {step.label}
                  </p>
                  {isActive && (
                    <p className="animate-fade-in truncate text-[11px] text-slate-500">
                      {step.sublabel}
                    </p>
                  )}
                </div>

                {/* Right status */}
                <div className="shrink-0">
                  {isDone && (
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-500">
                      Done
                    </span>
                  )}
                  {isActive && (
                    <div className="flex gap-0.5">
                      {[0, 1, 2].map((d) => (
                        <span
                          key={d}
                          className={`h-1 w-1 animate-bounce rounded-full ${step.color.replace("text-", "bg-")}`}
                          style={{ animationDelay: `${d * 0.15}s` }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer hint */}
        <p className="mt-4 text-center text-[11px] text-slate-700">
          AI agents processing {STEPS.length} risk dimensions simultaneously
        </p>
      </div>
    </div>
  );
}
