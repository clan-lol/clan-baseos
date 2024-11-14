import defaultTheme from "tailwindcss/defaultTheme";
import type { Config } from "tailwindcss";

export const typography: Partial<Config["theme"]> = {
  fontFamily: {
    sans: ["Archivo", ...defaultTheme.fontFamily.sans],
  },
  fontSize: {
    ...defaultTheme.fontSize,
    title: ["1.125rem", { lineHeight: "124%" }],
    "title-m": ["1.25rem", { lineHeight: "124%" }],
    "title-l": ["1.375rem", { lineHeight: "124%" }],
  },
  // textColor: {
  //   ...defaultTheme.textColor,
  //   primary: "#0D1416",
  //   secondary: "#2C4347",
  // },
} as const;
