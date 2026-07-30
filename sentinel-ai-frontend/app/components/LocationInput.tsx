"use client";

import { useEffect, useRef, useState } from "react";

interface Suggestion {
  place_id: number;
  display_name: string;
}

interface Props {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  accentColor: string;
  icon: React.ReactNode;
  onChange: (v: string) => void;
  disabled: boolean;
}

export default function LocationInput({
  id, label, placeholder, value, accentColor, icon, onChange, disabled,
}: Props) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length < 3) { setSuggestions([]); setOpen(false); return; }

    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/search?format=json&limit=6&q=${encodeURIComponent(value)}`,
          { headers: { "Accept-Language": "en" } }
        );
        const data: Suggestion[] = await res.json();
        setSuggestions(data);
        setOpen(data.length > 0);
      } catch {
        setSuggestions([]); setOpen(false);
      }
    }, 350);
  }, [value]);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function select(name: string) {
    onChange(name);
    setOpen(false);
    setSuggestions([]);
  }

  return (
    <div className="flex flex-col gap-1.5" ref={containerRef}>
      <label htmlFor={id} className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">
        <span className={`h-1 w-1 rounded-full ${accentColor}`} />
        {label}
      </label>
      <div className={`relative transition-all duration-200 ${value.length > 0 ? "drop-shadow-[0_0_8px_rgba(59,130,246,0.15)]" : ""}`}>
        <span className="pointer-events-none absolute inset-y-0 left-3.5 flex items-center text-slate-600">
          {icon}
        </span>
        <input
          id={id}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          className="w-full rounded-xl border border-white/[0.07] bg-slate-900/60 py-3.5 pl-10 pr-4 text-sm text-white placeholder-slate-700 outline-none backdrop-blur-sm transition-all duration-200 focus:border-blue-500/40 focus:bg-slate-900/80 focus:ring-1 focus:ring-blue-500/20 disabled:cursor-not-allowed disabled:opacity-40"
        />

        {open && (
          <ul className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl border border-white/[0.08] bg-slate-900 shadow-2xl shadow-black/60">
            {suggestions.map((s) => (
              <li
                key={s.place_id}
                onMouseDown={() => select(s.display_name)}
                className="cursor-pointer truncate px-4 py-2.5 text-sm text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
              >
                {s.display_name}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
