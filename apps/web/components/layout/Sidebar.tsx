const navigation = [
  { label: "Research", href: "/research" },
  { label: "Search", href: "/search" },
  { label: "Evidence", href: "/evidence" },
  { label: "Experiments", href: "/experiments" },
  { label: "Analysis", href: "/analysis" },
  { label: "History", href: "/history" },
  { label: "System Status", href: "/status" },
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-64 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 px-6 py-5">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-zinc-500">
          NASA Space Apps
        </p>

        <h1 className="mt-2 text-lg font-semibold text-white">
          Flame in Freefall
        </h1>
      </div>

      <nav className="flex-1 px-3 py-4">
        <div className="space-y-1">
          {navigation.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="block rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-900 hover:text-white"
            >
              {item.label}
            </a>
          ))}
        </div>
      </nav>

      <div className="border-t border-zinc-800 px-6 py-4">
        <p className="text-xs text-zinc-500">
          Scientific Research Platform
        </p>
      </div>
    </aside>
  );
}
