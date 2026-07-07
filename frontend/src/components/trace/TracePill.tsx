"use client";

type TraceTone = "ocean" | "amber" | "ember" | "sky" | "stone";

const TONE_CLASS: Record<TraceTone, string> = {
  ocean: "bg-[rgba(15,139,141,0.12)] text-[var(--color-ocean)]",
  amber: "bg-[rgba(219,158,54,0.16)] text-[rgb(145,95,19)]",
  ember: "bg-[rgba(212,106,74,0.14)] text-[var(--color-ember)]",
  sky: "bg-[rgba(69,123,157,0.14)] text-[rgb(53,96,125)]",
  stone: "bg-[rgba(13,37,48,0.08)] text-[var(--color-ink-soft)]"
};

export function TracePill({
  label,
  value,
  tone = "stone"
}: {
  label: string;
  value: string;
  tone?: TraceTone;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-medium ${TONE_CLASS[tone]}`}
    >
      <span className="uppercase tracking-[0.18em] opacity-70">{label}</span>
      <span>{value}</span>
    </span>
  );
}
