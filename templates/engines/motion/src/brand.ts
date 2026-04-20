import { staticFile } from "remotion";
import brandJson from "../../../brand.json";

type FontsConfig = {
  dir?: string;
  serif_family?: string;
  sans_family?: string;
  mono_family?: string;
  serif_regular?: string;
  serif_italic?: string;
  mono_medium?: string;
  body_regular?: string;
  body_medium?: string;
  body_semibold?: string;
};

const fontsJson: FontsConfig = (brandJson as { fonts?: FontsConfig }).fonts ?? {};

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
  fonts: {
    serifFamily: fontsJson.serif_family ?? "Instrument Serif",
    sansFamily: fontsJson.sans_family ?? "Inter",
    monoFamily: fontsJson.mono_family ?? "JetBrains Mono",
  },
};

/**
 * CSS string of @font-face declarations for the TTFs listed in brand.json.fonts.
 * render.sh syncs the project's ./fonts/ into engines/motion/public/fonts/, so
 * staticFile("fonts/<name>.ttf") resolves correctly.
 *
 * Missing TTFs: the @font-face will 404 silently and the browser falls back to
 * the family's generic (serif/sans-serif/monospace). The static engine
 * (engines/static/shared.py::Brand.font) has its own graceful fallback.
 */
const face = (family: string | undefined, file: string | undefined, italic = false, weight = 400) => {
  if (!family || !file) return "";
  return `@font-face { font-family: "${family}"; src: url("${staticFile(
    `fonts/${file}`,
  )}") format("truetype"); font-style: ${italic ? "italic" : "normal"}; font-weight: ${weight}; font-display: block; }`;
};

export const fontFaceCss = [
  face(brand.fonts.serifFamily, fontsJson.serif_regular, false, 400),
  face(brand.fonts.serifFamily, fontsJson.serif_italic, true, 400),
  face(brand.fonts.sansFamily, fontsJson.body_regular, false, 400),
  face(brand.fonts.sansFamily, fontsJson.body_medium, false, 500),
  face(brand.fonts.sansFamily, fontsJson.body_semibold, false, 600),
  face(brand.fonts.monoFamily, fontsJson.mono_medium, false, 500),
]
  .filter(Boolean)
  .join("\n");
