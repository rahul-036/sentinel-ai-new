export default function Navbar() {
  return (
    <nav className="fixed inset-x-0 top-0 z-50 glass border-b border-white/[0.06]">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-6">
        {/* Logo */}
        <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 via-blue-600 to-violet-700 shadow-lg shadow-blue-500/40">
          <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
          </svg>
          {/* Live pulse */}
          <span className="absolute -right-0.5 -top-0.5 flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400" />
          </span>
        </div>

        <div className="flex flex-col leading-none">
          <span className="text-[15px] font-bold tracking-wide text-white">Sentinel AI</span>
          <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-blue-400/80">
            Safety Intelligence Platform
          </span>
        </div>

        {/* Centre — agent label */}
        <div className="mx-auto hidden items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-4 py-1.5 sm:flex">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-400" />
          <span className="text-xs font-medium text-gray-400">Risk Assessment Agent</span>
          <span className="rounded-sm bg-blue-500/20 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-400">
            Phase 1
          </span>
        </div>

        {/* Right — status */}
        <div className="ml-auto flex items-center gap-3">
          <div className="hidden items-center gap-1.5 sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            <span className="text-xs text-gray-500">Agent Online</span>
          </div>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-semibold text-gray-400">
            v0.1
          </span>
        </div>
      </div>
    </nav>
  );
}
