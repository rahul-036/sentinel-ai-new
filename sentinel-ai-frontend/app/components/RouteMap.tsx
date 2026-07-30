"use client";

import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { CrimeLocationDetail, FacilityDetail, RiskLevel } from "@/app/types/risk";

// ── Fix Leaflet's broken default icon paths under webpack / Next.js ───────────
L.Icon.Default.mergeOptions({
  iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// ── Coloured pin factory ──────────────────────────────────────────────────────

const SHADOW = "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png";
const PINS   = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img";

function pin(color: string) {
  return new L.Icon({
    iconUrl:     `${PINS}/marker-icon-2x-${color}.png`,
    shadowUrl:   SHADOW,
    iconSize:    [25, 41],
    iconAnchor:  [12, 41],
    popupAnchor: [1, -34],
    shadowSize:  [41, 41],
  });
}

const icons = {
  // route endpoints
  green:  pin("green"),
  red:    pin("red"),
  // crime severity
  crimeCritical: pin("red"),
  crimeHigh:     pin("orange"),
  crimeMedium:   pin("yellow"),
  crimeLow:      pin("gold"),
  // facilities
  police:   pin("blue"),
  hospital: pin("green"),
  fire:     pin("red"),
  petrol:   pin("orange"),
  pharmacy: pin("violet"),
  metro:    pin("grey"),
};

function crimeIcon(level: RiskLevel) {
  if (level === "Critical") return icons.crimeCritical;
  if (level === "High")     return icons.crimeHigh;
  if (level === "Medium")   return icons.crimeMedium;
  return icons.crimeLow;
}

function facilityIcon(type: string) {
  if (type === "police")        return icons.police;
  if (type === "hospital")      return icons.hospital;
  if (type === "fire_station")  return icons.fire;
  if (type === "petrol_pump")   return icons.petrol;
  if (type === "pharmacy")      return icons.pharmacy;
  if (type === "metro_station") return icons.metro;
  return icons.green;
}

function facilityLabel(type: string) {
  const map: Record<string, string> = {
    police:        "Police Station",
    hospital:      "Hospital",
    fire_station:  "Fire Station",
    petrol_pump:   "Petrol Pump",
    pharmacy:      "Pharmacy",
    metro_station: "Metro Station",
  };
  return map[type] ?? type;
}

// ── Auto-fit bounds ───────────────────────────────────────────────────────────

function FitBounds({ positions }: { positions: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 1) {
      map.fitBounds(L.latLngBounds(positions), { padding: [40, 40] });
    } else if (positions.length === 1) {
      map.setView(positions[0], 13);
    }
  }, [map, positions]);
  return null;
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface RouteMapProps {
  coordinates:    { lon: number; lat: number }[];
  source:         string;
  destination:    string;
  crimeLocations?: CrimeLocationDetail[];
  facilities?:     FacilityDetail[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function RouteMap({
  coordinates,
  source,
  destination,
  crimeLocations = [],
  facilities     = [],
}: RouteMapProps) {
  const positions = useMemo<[number, number][]>(
    () => coordinates.map((c) => [c.lat, c.lon]),
    [coordinates],
  );

  if (!coordinates || coordinates.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.02] text-sm text-slate-500">
        No route available.
      </div>
    );
  }

  const start = positions[0];
  const end   = positions[positions.length - 1];

  return (
    <MapContainer
      center={positions[Math.floor(positions.length / 2)]}
      zoom={13}
      zoomControl={true}
      scrollWheelZoom={true}
      className="h-full w-full rounded-2xl"
      style={{ minHeight: "360px" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Route polyline */}
      <Polyline positions={positions} pathOptions={{ color: "#3b82f6", weight: 4, opacity: 0.85 }} />

      {/* Source marker */}
      <Marker position={start} icon={icons.green}>
        <Popup><span className="font-semibold">Start:</span> {source}</Popup>
      </Marker>

      {/* Destination marker */}
      <Marker position={end} icon={icons.red}>
        <Popup><span className="font-semibold">End:</span> {destination}</Popup>
      </Marker>

      {/* Crime hotspot markers */}
      {crimeLocations.map((c, i) => (
        <Marker key={`crime-${i}`} position={[c.latitude, c.longitude]} icon={crimeIcon(c.risk_level)}>
          <Popup>
            <div className="text-sm">
              <p className="font-semibold">{c.area}</p>
              <p>Type: {c.dominant_crime_type}</p>
              <p>Severity: {c.risk_level}</p>
              <p>Crime Index: {c.crime_index}</p>
              <p>Distance: {Math.round(c.distance_m)} m from route</p>
            </div>
          </Popup>
        </Marker>
      ))}

      {/* Facility markers */}
      {facilities.map((f) => (
        <Marker key={f.id} position={[f.latitude, f.longitude]} icon={facilityIcon(f.type)}>
          <Popup>
            <div className="text-sm">
              <p className="font-semibold">{f.name || facilityLabel(f.type)}</p>
              <p>{facilityLabel(f.type)}</p>
            </div>
          </Popup>
        </Marker>
      ))}

      <FitBounds positions={positions} />
    </MapContainer>
  );
}
