export function money(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 0,
  }).format(value);
}

export function ratio(value: number): string {
  if (!value) return "0";
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value);
}
