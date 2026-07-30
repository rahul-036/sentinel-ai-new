import type { RiskAnalysisRequest, RiskAnalysisResponse } from "@/app/types/risk";
import type { SOSRequest, SOSResponseV2, SOSHistoryItem } from "@/app/types/sos";
import type { Guardian, GuardianCreate, GuardianUpdate } from "@/app/types/guardian";
import type { RouteOptimizationResponse } from "@/app/types/route_optimization";

const API_BASE = "/backend";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Shared fetch helper ───────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
  defaultError = "Request failed",
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let message = `${defaultError} (status ${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) message = body.detail;
      else if (body?.error?.message) message = body.error.message;
    } catch { /* keep default */ }
    throw new ApiError(res.status, message);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Risk Analysis (unchanged) ─────────────────────────────────────────────────

export async function analyzeRoute(
  payload: RiskAnalysisRequest,
): Promise<RiskAnalysisResponse> {
  const body: RiskAnalysisRequest = { source: payload.source, destination: payload.destination };
  if (payload.travel_time) body.travel_time = payload.travel_time;
  return apiFetch<RiskAnalysisResponse>("/api/v1/risk/analyze", {
    method: "POST",
    body: JSON.stringify(body),
  }, "Risk analysis failed");
}

// ── Route Optimization ───────────────────────────────────────────────────────────────────

export async function optimizeRoute(
  payload: RiskAnalysisRequest,
): Promise<RouteOptimizationResponse> {
  return apiFetch<RouteOptimizationResponse>("/api/v1/route-optimization/analyze", {
    method: "POST",
    body: JSON.stringify({ source: payload.source, destination: payload.destination }),
  }, "Route optimization failed");
}

// ── SOS ───────────────────────────────────────────────────────────────────────

export async function sendSOS(payload: SOSRequest): Promise<SOSResponseV2> {
  return apiFetch<SOSResponseV2>("/api/v1/sos/send", {
    method: "POST",
    body: JSON.stringify(payload),
  }, "SOS request failed");
}

export async function fetchSOSHistory(): Promise<SOSHistoryItem[]> {
  return apiFetch<SOSHistoryItem[]>("/api/v1/sos/history", {}, "Failed to fetch SOS history");
}

// ── Guardian CRUD ─────────────────────────────────────────────────────────────

export async function fetchGuardians(): Promise<Guardian[]> {
  return apiFetch<Guardian[]>("/api/v1/guardians", {}, "Failed to fetch guardians");
}

export async function createGuardian(payload: GuardianCreate): Promise<Guardian> {
  return apiFetch<Guardian>("/api/v1/guardians", {
    method: "POST",
    body: JSON.stringify(payload),
  }, "Failed to create guardian");
}

export async function updateGuardian(id: string, payload: GuardianUpdate): Promise<Guardian> {
  return apiFetch<Guardian>(`/api/v1/guardians/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  }, "Failed to update guardian");
}

export async function deleteGuardian(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/guardians/${id}`, {
    method: "DELETE",
  }, "Failed to delete guardian");
}
