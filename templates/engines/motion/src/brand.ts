import brandJson from "../../../brand.json";

export const brand = {
  ink: brandJson.colors.ink,
  muted: brandJson.colors.muted,
  cream: brandJson.colors.cream,
  creamAlt: brandJson.colors.cream_alt ?? brandJson.colors.cream,
  accent: brandJson.colors.accent,
  highlight: brandJson.colors.highlight ?? brandJson.colors.accent,
  success: (brandJson.colors as any).success ?? "#4c8f50",
  wordmark: brandJson.wordmark ?? brandJson.name ?? "",
  domain: brandJson.domain ?? "",
  card: "#fffcf5",
  border: "rgba(30,24,19,0.08)",
};
