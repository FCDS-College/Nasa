interface MetricCardProps {
  label: string;
  value: string | number;
  description?: string;
}

export function MetricCard({
  label,
  value,
  description,
}: MetricCardProps) {
  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-5">
      <p className="text-sm text-zinc-500">{label}</p>

      <p className="mt-2 text-3xl font-semibold text-white">
        {value}
      </p>

      {description && (
        <p className="mt-1 text-xs text-zinc-500">
          {description}
        </p>
      )}
    </section>
  );
}
