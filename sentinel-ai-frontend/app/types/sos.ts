import type { RiskLevel } from "@/app/types/risk";

// ── Request (unchanged) ───────────────────────────────────────────────────────

export interface SOSRequest {
  user_name: string;
  phone: string;
  latitude: number;
  longitude: number;
  safety_score: number;
  risk_level: RiskLevel;
}

// ── Location sub-model (unchanged) ───────────────────────────────────────────

export interface SOSLocation {
  latitude: number;
  longitude: number;
}

// ── Original response (unchanged) ────────────────────────────────────────────

export interface SOSResponse {
  status: string;
  alert_id: string;
  timestamp: string;
  message: string;
  user_name: string;
  risk_level: RiskLevel;
  safety_score: number;
  location: SOSLocation;
}

// ── New: per-guardian notification result ─────────────────────────────────────

export interface NotifiedGuardian {
  id: string;
  name: string;
  phone: string;
  relation: string;
  notification_status: string;
}

// ── New: extended SOS response ────────────────────────────────────────────────

export interface SOSResponseV2 {
  status: string;
  alert_id: string;
  timestamp: string;
  message: string;
  user_name: string;
  risk_level: RiskLevel;
  safety_score: number;
  location: SOSLocation;
  guardian_count: number;
  guardians_notified: NotifiedGuardian[];
}

// ── New: SOS history item ─────────────────────────────────────────────────────

export interface SOSHistoryItem {
  alert_id: string;
  timestamp: string;
  user_name: string;
  latitude: number;
  longitude: number;
  risk_level: string;
  safety_score: number;
  guardian_count: number;
  guardians_notified: NotifiedGuardian[];
  status: string;
}
