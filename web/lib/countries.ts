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

// Per-country accent identity color used to track countries across stacked bars.
export const COUNTRY_LOCKER_COLOR: Record<string, string> = {
  PL: "#F5C04E",
  GB: "#E0A82E",
  FR: "#C29612",
  DE: "#9E7414",
  IT: "#A85A2E",
  ES: "#7A3D1E",
  AT: "#5C2D18",
  HU: "#8B4A18",
  PT: "#704514",
  BE: "#3F3F46",
  NL: "#27272A",
};

export const COUNTRY_PUDO_COLOR: Record<string, string> = {
  DE: "#A1A1A6",
  GB: "#8B8B90",
  FR: "#7A7A80",
  ES: "#6B6B70",
  IT: "#5C5C61",
  BE: "#4F4F55",
  PT: "#3F3F46",
  AT: "#34343A",
  HU: "#2F2F35",
  PL: "#27272A",
  NL: "#1F1F23",
};
