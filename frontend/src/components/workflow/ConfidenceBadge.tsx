"use client";

interface ConfidenceBadgeProps {
  score: number;
  label?: string;
  showBar?: boolean;
}

function normalizeScore(raw: number): number {
  return raw > 1 ? raw / 100 : raw;
}

function barColor(pct: number): string {
  if (pct >= 70) return "bg-green-500";
  if (pct >= 40) return "bg-amber-500";
  return "bg-red-500";
}

function badgeBg(pct: number): string {
  if (pct >= 70) return "bg-green-100 text-green-800 ring-green-600/20";
  if (pct >= 40) return "bg-amber-100 text-amber-800 ring-amber-600/20";
  return "bg-red-100 text-red-800 ring-red-600/20";
}

function labelText(pct: number, custom?: string): string {
  if (custom) return custom;
  if (pct >= 70) return "High";
  if (pct >= 40) return "Medium";
  return "Low";
}

export function ConfidenceBadge({
  score,
  label,
  showBar = true,
}: ConfidenceBadgeProps) {
  const normalized = normalizeScore(score);
  const pct = Math.round(normalized * 100);
  const barWidth = Math.min(100, Math.max(0, pct));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-3xl font-bold tabular-nums text-slate-900">
          {pct}%
        </span>
        <span
          className={`inline-flex items-center rounded-md px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${badgeBg(pct)}`}
        >
          {labelText(pct, label)} confidence
        </span>
      </div>
      {showBar && (
        <div className="h-2.5 w-full max-w-sm overflow-hidden rounded-full bg-slate-200">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor(pct)}`}
            style={{ width: `${barWidth}%` }}
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      )}
    </div>
  );
}
