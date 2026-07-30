export interface RiskAnalysisRequest {
  source: string;
  destination: string;
  travel_time?: string;
}

export type RiskLevel = "Low" | "Medium" | "High" | "Critical";
export type InfrastructureRating = "Poor" | "Fair" | "Good" | "Excellent" | "Unknown";
export type PredictionLevel = "Low" | "Medium" | "High" | "Moderate";

export interface PredictionResponse {
  accident_probability: PredictionLevel;
  traffic_delay_probability: PredictionLevel;
  crime_probability: PredictionLevel;
  weather_impact: PredictionLevel;
  overall_future_risk: PredictionLevel;
  recommended_departure: string;
  ai_recommendation: string;
}

export interface EmergencyFacilityInfo {
  name: string;
  distance_km: number | null;
  eta_minutes: number | null;
  latitude: number | null;
  longitude: number | null;
  available: boolean;
}

export interface EmergencyResponseResult {
  activated: boolean;
  trigger_reason: string;
  nearest_police: EmergencyFacilityInfo;
  nearest_hospital: EmergencyFacilityInfo;
  nearest_fire_station: EmergencyFacilityInfo;
  emergency_contacts: Record<string, string>;
  status: string;
}

export interface CrimeLocationDetail {
  area: string;
  crime_index: number;
  risk_level: RiskLevel;
  latitude: number;
  longitude: number;
  dominant_crime_type: string;
  distance_m: number;
}

export interface FacilityDetail {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
}

export interface RiskAnalysisResponse {
  // ── Core ─────────────────────────────────────────────────────────────────
  safety_score: number;
  risk_level: RiskLevel;
  crime_risk: RiskLevel;
  weather: string;
  nearby_police: number;
  nearby_hospitals: number;
  infrastructure: InfrastructureRating;
  recommendation: string;
  reason: string;
  // ── Crime Intelligence ────────────────────────────────────────────────────
  nearby_crimes: number;
  crime_locations: CrimeLocationDetail[];
  // ── Route Agent ───────────────────────────────────────────────────────────
  source: string;
  destination: string;
  distance_km: number | null;
  duration_min: number | null;
  route_live: boolean;
  geometry?: {
    coordinates: { lon: number; lat: number }[];
  };
  // ── Weather Agent ─────────────────────────────────────────────────────────
  temperature_c: number | null;
  feels_like_c: number | null;
  humidity_pct: number | null;
  wind_kph: number | null;
  visibility_km: number | null;
  weather_live: boolean;
  // ── Infrastructure Agent ──────────────────────────────────────────────────
  nearby_fire_stations: number;
  nearby_petrol_pumps: number;
  nearby_pharmacies: number;
  nearby_metro_stations: number;
  infrastructure_live: boolean;
  facility_police: FacilityDetail[];
  facility_hospitals: FacilityDetail[];
  facility_fire_stations: FacilityDetail[];
  facility_petrol_pumps: FacilityDetail[];
  facility_pharmacies: FacilityDetail[];
  facility_metro_stations: FacilityDetail[];
  // ── Traffic Agent ─────────────────────────────────────────────────────
  traffic: string;
  traffic_score: number;
  traffic_rating: string;
  congestion_percentage: number;
  average_speed_kph: number;
  free_flow_speed_kph: number;
  delay_minutes: number;
  traffic_incidents: number;
  traffic_live: boolean;
  // ── Multi-route comparison ────────────────────────────────────────────────
  routes: RouteOption[];
  recommended_index: number;
  // ── Incident Prediction ───────────────────────────────────────────────────
  prediction?: PredictionResponse;
  // ── Emergency Response ────────────────────────────────────────────────────
  emergency_response?: EmergencyResponseResult;
}

export interface RouteOption {
  route_index: number;
  preference: string;
  safety_score: number;
  risk_level: RiskLevel;
  recommended: boolean;
  distance_km: number;
  duration_min: number;
  crime_risk: RiskLevel;
  weather: string;
  infrastructure: InfrastructureRating;
  traffic: string;
  traffic_score: number;
  congestion_percentage: number;
  delay_minutes: number;
  geometry?: { coordinates: { lon: number; lat: number }[] };
  crime_locations: CrimeLocationDetail[];
}
