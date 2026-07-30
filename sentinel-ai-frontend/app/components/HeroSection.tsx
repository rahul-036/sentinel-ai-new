export default function HeroSection() {
  return (
    <section className="relative flex flex-col items-center pb-10 pt-32 text-center">
      {/* Grid background */}
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-grid opacity-60" />

      {/* Ambient glows */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 left-1/2 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-blue-600/[0.12] blur-[100px]" />
        <div className="absolute top-0 left-[15%] h-72 w-72 rounded-full bg-violet-600/[0.10] blur-[80px]" />
        <div className="absolute top-0 right-[15%] h-72 w-72 rounded-full bg-cyan-500/[0.08] blur-[80px]" />
      </div>

      <div className="relative z-10 flex flex-col items-center gap-5 px-4">
        <div className="animate-fade-in inline-flex items-center gap-2.5 rounded-full border border-blue-500/25 bg-blue-500/[0.08] px-5 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-blue-400">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-50" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-400" />
          </span>
          AI-Powered · Real-Time · Risk Intelligence
        </div>

        <h1 className="animate-fade-in delay-100 max-w-4xl text-4xl font-extrabold leading-[1.1] tracking-tight text-white sm:text-5xl lg:text-[3.75rem]">
          AI-Powered Personal Safety
          <br />
          <span className="shimmer-text">&amp; Risk Navigation</span>
        </h1>

        <p className="animate-fade-in delay-200 max-w-lg text-base leading-relaxed text-slate-400 sm:text-lg">
          Multi-dimensional route analysis across crime, weather, emergency
          services, and infrastructure — delivered in seconds.
        </p>

        {/* Stat pills */}
        <div className="animate-fade-in delay-300 mt-1 flex flex-wrap justify-center gap-3">
          {[
            { label: "Analysis Dimensions", value: "5" },
            { label: "Response Time", value: "<1s" },
            { label: "Confidence Model", value: "AI" },
          ].map((s) => (
            <div
              key={s.label}
              className="glass-highlight flex items-center gap-2 rounded-full px-4 py-1.5"
            >
              <span className="text-sm font-bold text-white">{s.value}</span>
              <span className="text-xs text-slate-500">{s.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
