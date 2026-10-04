interface StateCardProps {
  title: string;
  message: string;
  status?: "success" | "warning" | "error" | "neutral";
}

const statusStyles = {
  success: "border-emerald-500/20 bg-emerald-500/5",
  warning: "border-amber-500/20 bg-amber-500/5",
  error: "border-red-500/20 bg-red-500/5",
  neutral: "border-zinc-800 bg-zinc-950",
};

export function StateCard({
  title,
  message,
  status = "neutral",
}: StateCardProps) {
  return (
    <section
      className={`rounded-xl border p-5 ${statusStyles[status]}`}
    >
      <h3 className="text-sm font-medium text-white">{title}</h3>

      <p className="mt-2 text-sm text-zinc-400">
        {message}
      </p>
    </section>
  );
}
