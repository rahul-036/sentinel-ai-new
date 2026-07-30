"use client";

import { useState } from "react";
import LocationInput from "./LocationInput";

interface RouteFormProps {
  onSubmit: (source: string, destination: string, travelTime: string) => void;
  loading: boolean;
}

export default function RouteForm({ onSubmit, loading }: RouteFormProps) {
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [travelTime, setTravelTime] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!source.trim()) { setError("Source location is required."); return; }
    if (!destination.trim()) { setError("Destination is required."); return; }
    onSubmit(source.trim(), destination.trim(), travelTime.trim());
  }

  return (
    <div className="animate-fade-in-up delay-400 mx-auto w-full max-w-xl">
      <form
        onSubmit={handleSubmit}
        className="glass rounded-2xl p-6 shadow-2xl shadow-black/50"
      >
        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Route Analysis</h2>
            <p className="text-[11px] text-slate-500">Enter your journey details below</p>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <LocationInput
            id="source"
            label="Origin"
            placeholder="Enter source (city, landmark, street or address)"
            value={source}
            accentColor="bg-blue-400"
            icon={
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
              </svg>
            }
            onChange={setSource}
            disabled={loading}
          />

          {/* Route connector */}
          <div className="flex items-center gap-3 px-1">
            <div className="flex flex-col items-center gap-1">
              <div className="h-1 w-1 rounded-full bg-slate-700" />
              <div className="h-1 w-1 rounded-full bg-slate-700" />
              <div className="h-1 w-1 rounded-full bg-slate-700" />
            </div>
            <div className="h-px flex-1 bg-gradient-to-r from-blue-500/20 via-violet-500/20 to-transparent" />
          </div>

          <LocationInput
            id="destination"
            label="Destination"
            placeholder="Enter destination (city, landmark, street or address)"
            value={destination}
            accentColor="bg-violet-400"
            icon={
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v1.5M3 21v-6m0 0l2.77-.693a9 9 0 016.208.682l.108.054a9 9 0 006.086.71l3.114-.732a48.524 48.524 0 01-.005-10.499l-3.11.732a9 9 0 01-6.085-.711l-.108-.054a9 9 0 00-6.208-.682L3 4.5M3 15V4.5" />
              </svg>
            }
            onChange={setDestination}
            disabled={loading}
          />

          <LocationInput
            id="travel-time"
            label="Travel Time (optional)"
            placeholder="e.g. 10:30 PM"
            value={travelTime}
            accentColor="bg-slate-600"
            icon={
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            onChange={setTravelTime}
            disabled={loading}
          />

          {error && (
            <p className="flex items-center gap-1.5 text-xs font-medium text-red-400">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="group relative mt-1 flex w-full items-center justify-center gap-2.5 overflow-hidden rounded-xl bg-gradient-to-r from-blue-600 to-violet-600 py-3.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:shadow-blue-500/40 hover:brightness-110 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {/* Shimmer sweep on hover */}
            <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent transition-transform duration-500 group-hover:translate-x-full" />

            {loading ? (
              <>
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Running Analysis…
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
                Analyze Route
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
