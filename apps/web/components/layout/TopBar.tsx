export function TopBar() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-6">
      <div>
        <p className="text-sm font-medium text-white">
          Scientific Dashboard
        </p>

        <p className="text-xs text-zinc-500">
          Flame in Freefall
        </p>
      </div>

      <div className="flex items-center gap-3">
        <span className="h-2 w-2 rounded-full bg-zinc-500" />

        <span className="text-xs text-zinc-400">
          Unknown
        </span>
      </div>
    </header>
  );
}
