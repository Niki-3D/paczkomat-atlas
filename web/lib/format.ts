/**
 * Number formatters — Intl-based, locale-stable.
 *
 * Centralized so every panel renders 31,687 instead of "31687" or "31 687",
 * and 8.5 instead of "8.500000000001". Use `fmtInt` for counts, `fmt1` for
 * 1-decimal floats (densities, percents), `fmt2` for 2-decimal floats
 * (precise density values shown in tooltips and the bar chart).
 */
const FMT_INT = new Intl.NumberFormat("en-US");

export function fmtInt(n: number): string {
  return FMT_INT.format(n);
}

export function fmt1(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(1);
}

export function fmt2(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toFixed(2);
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return `${n.toFixed(1)}%`;
}
