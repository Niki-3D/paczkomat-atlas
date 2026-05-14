export type CountryMeta = {
  code: string;
  name: string;
  flag: string;
  note?: string;
};

export const COUNTRY_META: Record<string, CountryMeta> = {
  PL: { code: "PL", name: "Poland", flag: "🇵🇱" },
  GB: { code: "GB", name: "United Kingdom", flag: "🇬🇧" },
  FR: { code: "FR", name: "France", flag: "🇫🇷" },
  DE: {
    code: "DE",
    name: "Germany",
    flag: "🇩🇪",
    note: "Mondial Relay network — machines pending",
  },
  ES: { code: "ES", name: "Spain", flag: "🇪🇸" },
  IT: { code: "IT", name: "Italy", flag: "🇮🇹" },
  AT: { code: "AT", name: "Austria", flag: "🇦🇹" },
  HU: { code: "HU", name: "Hungary", flag: "🇭🇺" },
  PT: { code: "PT", name: "Portugal", flag: "🇵🇹" },
  BE: { code: "BE", name: "Belgium", flag: "🇧🇪" },
  NL: { code: "NL", name: "Netherlands", flag: "🇳🇱" },
  SE: { code: "SE", name: "Sweden", flag: "🇸🇪" },
  DK: { code: "DK", name: "Denmark", flag: "🇩🇰" },
  FI: { code: "FI", name: "Finland", flag: "🇫🇮" },
};

export const PRE_LAUNCH = ["SE", "DK", "FI"] as const;

export function isPreLaunch(country: string): boolean {
  return (PRE_LAUNCH as readonly string[]).includes(country);
}

// Per-country identity color used to track countries across stacked bars.
// Hex values are registered as --country-{locker,pudo}-{cc} tokens in
// globals.css — this map references them as CSS var() expressions so
// changing the palette in one place updates every consumer.
export const COUNTRY_LOCKER_COLOR: Record<string, string> = {
  PL: "var(--country-locker-pl)",
  GB: "var(--country-locker-gb)",
  FR: "var(--country-locker-fr)",
  DE: "var(--country-locker-de)",
  IT: "var(--country-locker-it)",
  ES: "var(--country-locker-es)",
  AT: "var(--country-locker-at)",
  HU: "var(--country-locker-hu)",
  PT: "var(--country-locker-pt)",
  BE: "var(--country-locker-be)",
  NL: "var(--country-locker-nl)",
};

export const COUNTRY_PUDO_COLOR: Record<string, string> = {
  DE: "var(--country-pudo-de)",
  GB: "var(--country-pudo-gb)",
  FR: "var(--country-pudo-fr)",
  ES: "var(--country-pudo-es)",
  IT: "var(--country-pudo-it)",
  BE: "var(--country-pudo-be)",
  PT: "var(--country-pudo-pt)",
  AT: "var(--country-pudo-at)",
  HU: "var(--country-pudo-hu)",
  PL: "var(--border-default)",
  NL: "var(--country-pudo-nl)",
};
