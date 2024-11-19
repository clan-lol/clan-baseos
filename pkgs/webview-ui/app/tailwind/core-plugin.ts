import plugin from "tailwindcss/plugin";
import { typography } from "./typography";
// @ts-expect-error: lib of tailwind has no types
import { parseColor } from "tailwindcss/lib/util/color";

/* Converts HEX color to RGB */
const toRGB = (value: string) => parseColor(value).color.join(" ");

export default plugin.withOptions(
  (_options = {}) =>
    () => {
      // add more base styles
    },
  // add configuration which is merged with the final config
  () => ({
    theme: {
      extend: {
        colors: {
          white: toRGB("#ffffff"),
          black: toRGB("#000000"),
          primary: {
            50: toRGB("#f4f9f9"),
            100: toRGB("#dbeceb"),
            200: toRGB("#b6d9d6"),
            300: toRGB("#8abebc"),
            400: toRGB("#478585"),
            500: toRGB("#526f6f"),
            600: toRGB("#4b6667"),
            700: toRGB("#345253"),
            800: toRGB("#2a4647"),
            900: toRGB("#1f3536"),
            950: toRGB("#162324"),
          },
          secondary: {
            50: toRGB("#f7f9f9"),
            100: toRGB("#e7f2f4"),
            200: toRGB("#d7e8ea"),
            300: toRGB("#afc6ca"),
            400: toRGB("#8fb2b6"),
            500: toRGB("#7b9a9e"),
            600: toRGB("#4f747a"),
            700: toRGB("#415e63"),
            800: toRGB("#445f64"),
            900: toRGB("#2b4347"),
            950: toRGB("#0d1415"),
          },
          info: {
            50: toRGB("#eff9ff"),
            100: toRGB("#dff2ff"),
            200: toRGB("#b8e8ff"),
            300: toRGB("#78d6ff"),
            400: toRGB("#2cc0ff"),
            500: toRGB("#06aaf1"),
            600: toRGB("#006ca7"),
            700: toRGB("#006ca7"),
            800: toRGB("#025b8a"),
            900: toRGB("#084c72"),
            950: toRGB("#06304b"),
          },
          error: {
            50: toRGB("#fcf3f8"),
            100: toRGB("#f9eaf4"),
            200: toRGB("#f5d5e9"),
            300: toRGB("#ea9ecb"),
            400: toRGB("#e383ba"),
            500: toRGB("#d75d9f"),
            600: toRGB("#c43e81"),
            700: toRGB("#a82e67"),
            800: toRGB("#8c2855"),
            900: toRGB("#75264a"),
            950: toRGB("#461129"),
          },
        },
      },
      ...typography,
    },
  }),
);
