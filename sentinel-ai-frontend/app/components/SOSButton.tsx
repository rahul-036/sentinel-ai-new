"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { sendSOS, ApiError } from "@/app/lib/api";
import type { RiskAnalysisResponse } from "@/app/types/risk";
import type { SOSResponse } from "@/app/types/sos";

// ── Constants ─────────────────────────────────────────────────────────────────

const DEMO_USER  = "Demo User";
const DEMO_PHONE = "9999999999";
const TOAST_DURATION_MS = 6000;

// ── Types ─────────────────────────────────────────────────────────────────────

type DialogState = "closed" | "confirm" | "locating" | "sending";

interface Toast {
  id: number;
  kind: "success" | "error";
  title: string;
  body?: string;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const isSuccess = toast.kind === "success";

  return (
    <div
      role="alert"
      className={`animate-fade-in-up flex w-80 items-start gap-3 rounded-xl border p-4 shadow-2xl shadow-black/60 backdrop-blur-xl ${
        isSuccess
          ? "border-emerald-500/25 bg-emerald-500/[0.08]"
          : "border-red-500/25 bg-red-500/[0.08]"
      }`}
    >
      {/* Icon */}
      <div
        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
          isSuccess ? "bg-emerald-500/15" : "bg-red-500/15"
        }`}
      >
        {isSuccess ? (
          <svg className="h-3.5 w-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        ) : (
          <svg className="h-3.5 w-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        )}
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold ${isSuccess ? "text-emerald-400" : "text-red-400"}`}>
          {toast.title}
        </p>
        {toast.body && (
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{toast.body}</p>
        )}
      </div>

      {/* Dismiss */}
      <button
        onClick={() => onDismiss(toast.id)}
        className={`mt-0.5 shrink-0 transition ${
          isSuccess ? "text-emerald-500/50 hover:text-emerald-400" : "text-red-500/50 hover:text-red-400"
        }`}
        aria-label="Dismiss notification"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface SOSButtonProps {
  riskResult: RiskAnalysisResponse | null;
}

export default function SOSButton({ riskResult }: SOSButtonProps) {
  const [dialog, setDialog]   = useState<DialogState>("closed");
  const [toasts, setToasts]   = useState<Toast[]>([]);
  const toastCounter          = useRef(0);
  const dialogRef             = useRef<HTMLDivElement>(null);

  // ── Toast helpers ──────────────────────────────────────────────────────────

  const addToast = useCallback((kind: Toast["kind"], title: string, body?: string) => {
    const id = ++toastCounter.current;
    setToasts((prev) => [...prev, { id, kind, title, body }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), TOAST_DURATION_MS);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // ── Close dialog on Escape ─────────────────────────────────────────────────

  useEffect(() => {
    if (dialog === "closed") return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && dialog === "confirm") setDialog("closed");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dialog]);

  // ── Focus trap: keep focus inside dialog ──────────────────────────────────

  useEffect(() => {
    if (dialog !== "closed") {
      dialogRef.current?.focus();
    }
  }, [dialog]);

  // ── Core SOS flow ──────────────────────────────────────────────────────────

  const handleConfirm = useCallback(async () => {
    // 1. Get live location
    setDialog("locating");

    let latitude: number;
    let longitude: number;

    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10_000,
        })
      );
      latitude  = position.coords.latitude;
      longitude = position.coords.longitude;
    } catch (err) {
      setDialog("closed");
      const isPermission = err instanceof GeolocationPositionError && err.code === err.PERMISSION_DENIED;
      addToast(
        "error",
        isPermission ? "Location Permission Denied" : "Location Unavailable",
        isPermission
          ? "Please allow location access in your browser settings and try again."
          : "Could not retrieve your location. Please try again.",
      );
      return;
    }

    // 2. Send SOS
    setDialog("sending");

    try {
      const response: SOSResponse = await sendSOS({
        user_name:    DEMO_USER,
        phone:        DEMO_PHONE,
        latitude,
        longitude,
        safety_score: riskResult?.safety_score ?? 50,
        risk_level:   riskResult?.risk_level   ?? "Medium",
      });

      setDialog("closed");
      addToast(
        "success",
        "SOS Alert Sent Successfully",
        `Alert ID: ${response.alert_id} · ${response.timestamp}`,
      );
    } catch (err) {
      setDialog("closed");
      const msg =
        err instanceof ApiError
          ? `Server error (${err.status}): ${err.message}`
          : "Failed to send SOS alert. Please try again.";
      addToast("error", "SOS Failed", msg);
    }
  }, [riskResult, addToast]);

  // ── Derived UI state ───────────────────────────────────────────────────────

  const isProcessing = dialog === "locating" || dialog === "sending";
  const processingLabel = dialog === "locating" ? "Getting location…" : "Sending SOS…";

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      {/* ── Floating SOS button ─────────────────────────────────────────────── */}
      <button
        onClick={() => setDialog("confirm")}
        aria-label="Send SOS emergency alert"
        className="group fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-red-500 to-rose-600 shadow-lg shadow-red-500/40 transition-all duration-200 hover:scale-110 hover:shadow-red-500/60 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-950"
      >
        {/* Pulse ring */}
        <span className="absolute inset-0 rounded-full bg-red-500 opacity-0 transition-opacity group-hover:animate-ping group-hover:opacity-30" />

        {/* SOS label */}
        <span className="relative text-[11px] font-black tracking-widest text-white select-none">
          SOS
        </span>
      </button>

      {/* ── Backdrop + Dialog ───────────────────────────────────────────────── */}
      {dialog !== "closed" && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="sos-dialog-title"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => { if (dialog === "confirm") setDialog("closed"); }}
          />

          {/* Panel */}
          <div
            ref={dialogRef}
            tabIndex={-1}
            className="animate-scale-in relative w-full max-w-sm rounded-2xl border border-white/[0.08] bg-gray-950/95 p-6 shadow-2xl shadow-black/80 backdrop-blur-xl focus:outline-none"
          >
            {/* Header icon */}
            <div className="mb-4 flex justify-center">
              <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-red-500/20 to-rose-600/20 ring-1 ring-red-500/30">
                {isProcessing ? (
                  <Spinner className="h-7 w-7 text-red-400" />
                ) : (
                  <svg className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0M3.124 7.5A8.969 8.969 0 015.292 3m13.416 0a8.969 8.969 0 012.168 4.5" />
                  </svg>
                )}
                {/* Outer pulse ring */}
                {!isProcessing && (
                  <span className="absolute inset-0 animate-ping rounded-full bg-red-500/20" />
                )}
              </div>
            </div>

            {/* Title */}
            <h2
              id="sos-dialog-title"
              className="mb-2 text-center text-base font-bold text-white"
            >
              {isProcessing ? processingLabel : "Send Emergency SOS?"}
            </h2>

            {/* Body */}
            <p className="mb-6 text-center text-sm leading-relaxed text-slate-400">
              {dialog === "confirm" && (
                <>
                  This will send an emergency alert with your{" "}
                  <span className="font-medium text-slate-300">live location</span>
                  {riskResult && (
                    <>
                      {" "}and current risk level{" "}
                      <span className="font-semibold text-red-400">{riskResult.risk_level}</span>
                      {" "}(score: <span className="font-semibold text-white">{riskResult.safety_score}</span>)
                    </>
                  )}
                  .
                </>
              )}
              {dialog === "locating" && "Requesting your GPS coordinates…"}
              {dialog === "sending"  && "Dispatching alert to Guardian Agent…"}
            </p>

            {/* Actions */}
            {dialog === "confirm" && (
              <div className="flex gap-3">
                <button
                  onClick={() => setDialog("closed")}
                  className="flex-1 rounded-xl border border-white/[0.08] bg-white/[0.03] py-2.5 text-sm font-medium text-slate-400 transition hover:border-white/[0.15] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  className="group relative flex-1 overflow-hidden rounded-xl bg-gradient-to-r from-red-600 to-rose-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-red-500/25 transition hover:shadow-red-500/40 hover:brightness-110 active:scale-[0.98]"
                >
                  <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent transition-transform duration-500 group-hover:translate-x-full" />
                  <span className="relative">Send SOS</span>
                </button>
              </div>
            )}

            {/* Processing state — no buttons, just spinner feedback */}
            {isProcessing && (
              <div className="flex justify-center">
                <div className="flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/10 px-4 py-2">
                  <Spinner className="h-3.5 w-3.5 text-red-400" />
                  <span className="text-xs font-medium text-red-400">{processingLabel}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Toast stack (bottom-right, above the SOS button) ────────────────── */}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="fixed bottom-24 right-6 z-50 flex flex-col gap-2"
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismissToast} />
        ))}
      </div>
    </>
  );
}
