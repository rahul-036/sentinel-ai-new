import type { RiskLevel, InfrastructureRating, CrimeLocationDetail } from "./risk";

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
  geometry?: {
    coordinates: { lon: number; lat: number }[];
  };
  crime_locations: CrimeLocationDetail[];
}

export interface RouteOptimizationResponse {
  source: string;
  destination: string;
  routes: RouteOption[];
  recommended_index: number;
}
