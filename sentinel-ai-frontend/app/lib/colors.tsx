import type { RiskLevel, InfrastructureRating } from "@/app/types/risk";

export function riskColors(level: RiskLevel) {
  switch (level) {
    case "Low":
      return {
        badge:   "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
        dot:     "bg-emerald-400",
        bar:     "bg-emerald-500",
        glow:    "shadow-emerald-500/20",
        text:    "text-emerald-400",
        ring:    "stroke-emerald-500",
        subtle:  "bg-emerald-500/[0.07] border-emerald-500/20",
      };
    case "Medium":
      return {
        badge:   "border-amber-500/30 bg-amber-500/10 text-amber-400",
        dot:     "bg-amber-400",
        bar:     "bg-amber-500",
        glow:    "shadow-amber-500/20",
        text:    "text-amber-400",
        ring:    "stroke-amber-500",
        subtle:  "bg-amber-500/[0.07] border-amber-500/20",
      };
    case "High":
      return {
        badge:   "border-orange-500/30 bg-orange-500/10 text-orange-400",
        dot:     "bg-orange-400",
        bar:     "bg-orange-500",
        glow:    "shadow-orange-500/20",
        text:    "text-orange-400",
        ring:    "stroke-orange-500",
        subtle:  "bg-orange-500/[0.07] border-orange-500/20",
      };
    case "Critical":
      return {
        badge:   "border-red-500/30 bg-red-500/10 text-red-400",
        dot:     "bg-red-400",
        bar:     "bg-red-500",
        glow:    "shadow-red-500/20",
        text:    "text-red-400",
        ring:    "stroke-red-500",
        subtle:  "bg-red-500/[0.07] border-red-500/20",
      };
  }
}

export function infraColors(rating: InfrastructureRating) {
  switch (rating) {
    case "Excellent": return "border-emerald-500/30 bg-emerald-500/10 text-emerald-400";
    case "Good":      return "border-blue-500/30 bg-blue-500/10 text-blue-400";
    case "Fair":      return "border-amber-500/30 bg-amber-500/10 text-amber-400";
    case "Poor":      return "border-red-500/30 bg-red-500/10 text-red-400";
    default:          return "border-slate-500/30 bg-slate-500/10 text-slate-400";
  }
}

export function scoreGradient(score: number) {
  if (score >= 75) return { from: "#10b981", to: "#34d399", css: "from-emerald-500 to-teal-400" };
  if (score >= 50) return { from: "#f59e0b", to: "#fbbf24", css: "from-amber-500 to-yellow-400" };
  if (score >= 25) return { from: "#f97316", to: "#fb923c", css: "from-orange-500 to-amber-400" };
  return { from: "#ef4444", to: "#f87171", css: "from-red-600 to-red-400" };
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const c = riskColors(level);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${c.badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {level}
    </span>
  );
}
