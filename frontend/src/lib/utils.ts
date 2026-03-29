export function formatDate(date: string | null | undefined): string {
  if (!date) return "—";
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatCurrency(amount: number | null | undefined): string {
  if (amount == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US").format(n);
}

export function categoryBadgeClass(category: string | null): string {
  if (!category) return "badge badge-other";
  const c = category.toLowerCase();
  if (c.includes("corrective")) return "badge badge-corrective";
  if (c.includes("preventive")) return "badge badge-preventive";
  if (c.includes("oil")) return "badge badge-oil";
  if (c.includes("emission")) return "badge badge-emissions";
  return "badge badge-other";
}

export function categoryLabel(category: string | null): string {
  if (!category) return "Unknown";
  return category
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function confidenceColor(score: number): string {
  if (score >= 0.7) return "text-green-600";
  if (score >= 0.4) return "text-amber-600";
  return "text-red-600";
}

export function confidenceLabel(score: number): string {
  if (score >= 0.7) return "High";
  if (score >= 0.4) return "Medium";
  return "Low";
}
