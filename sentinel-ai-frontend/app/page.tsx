"use client";

import { useState } from "react";
import { analyzeRoute, ApiError } from "@/app/lib/api";
import type { RiskAnalysisResponse } from "@/app/types/risk";
import HeroSection from "@/app/components/HeroSection";
import RouteForm from "@/app/components/RouteForm";
import AnalysisLoader from "@/app/components/AnalysisLoader";
import ResultDashboard from "@/app/components/ResultDashboard";
import ErrorBanner from "@/app/components/ErrorBanner";
import SOSButton from "@/app/components/SOSButton";

type PageState = "idle" | "loading" | "result" | "error";

export default function HomePage() {
  const [pageState, setPageState] = useState<PageState>("idle");
  const [riskResult, setRiskResult] = useState<RiskAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [route, setRoute] = useState({ source: "", destination: "", travelTime: "" });

  async function handleAnalyze(source: string, destination: string, travelTime: string) {
    setRoute({ source, destination, travelTime });
    setPageState("loading");
    setError(null);
    setRiskResult(null);

    try {
      const data = await analyzeRoute({ source, destination, travel_time: travelTime || undefined });
      await new Promise((r) => setTimeout(r, 400));
      setRiskResult(data);
      setPageState("result");
    } catch (err) {
      let msg = "An unexpected error occurred. Please try again.";
      if (err instanceof ApiError) {
        msg = `Server error (${err.status}): ${err.message}`;
      } else if (err instanceof TypeError) {
        msg = "Cannot reach the backend. Make sure the API server is running on http://127.0.0.1:8000";
      }
      setError(msg);
      setPageState("error");
    }
  }

  function handleReset() {
    setPageState("idle");
    setRiskResult(null);
    setError(null);
  }

  return (
    <main className="min-h-screen pb-24">
      <HeroSection />
      <SOSButton riskResult={riskResult} />
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-6 px-4">
        {(pageState === "idle" || pageState === "error") && (
          <>
            <RouteForm onSubmit={handleAnalyze} loading={false} />
            {pageState === "error" && error && (
              <div className="w-full max-w-xl">
                <ErrorBanner message={error} onDismiss={handleReset} />
              </div>
            )}
          </>
        )}
        {pageState === "loading" && (
          <AnalysisLoader source={route.source} destination={route.destination} />
        )}
        {pageState === "result" && riskResult && (
          <>
            <ResultDashboard
              data={riskResult}
              source={route.source}
              destination={route.destination}
            />
            <button onClick={handleReset} className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.03] px-5 py-2.5 text-sm font-medium text-slate-400 transition hover:border-white/[0.15] hover:text-white">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
              Analyze Another Route
            </button>
          </>
        )}
      </div>
    </main>
  );
}