import plugin from "tailwindcss/plugin";
import { typography } from "./typography";
// @ts-expect-error: lib of tailwind has no types
import { parseColor } from "tailwindcss/lib/util/color";

/* Converts HEX color to RGB */
const toRGB = (value: string) =>
  "rgb(" + parseColor(value).color.join(" ") + ")";

export default plugin.withOptions(
  (_options = {}) =>
    ({ addUtilities, theme }) => {
      addUtilities({
        // Background colors
        ".bg-def-1": {
          backgroundColor: theme("colors.white"),
        },
        ".bg-def-2": {
          backgroundColor: theme("colors.secondary.50"),
        },
        ".bg-def-3": {
          backgroundColor: theme("colors.secondary.100"),
        },
        ".bg-def-4": {
          backgroundColor: theme("colors.secondary.200"),
        },
        ".bg-def-5": {
          backgroundColor: theme("colors.secondary.300"),
        },
        // bg inverse
        ".bg-inv-1": {
          backgroundColor: theme("colors.primary.600"),
        },
        ".bg-inv-2": {
          backgroundColor: theme("colors.primary.700"),
        },
        ".bg-inv-3": {
          backgroundColor: theme("colors.primary.800"),
        },
        ".bg-inv-4": {
          backgroundColor: theme("colors.primary.900"),
        },
        ".bg-inv-5": {
          backgroundColor: theme("colors.primary.950"),
        },
        // bg inverse accent
        ".bg-inv-acc-1": {
          backgroundColor: theme("colors.secondary.500"),
        },
        ".bg-inv-acc-2": {
          backgroundColor: theme("colors.secondary.600"),
        },
        ".bg-inv-acc-3": {
          backgroundColor: theme("colors.secondary.700"),
        },

        // Text colors
        ".fg-def-1": {
          color: theme("colors.secondary.950"),
        },
        ".fg-def-2": {
          color: theme("colors.secondary.900"),
        },
        ".fg-def-3": {
          color: theme("colors.secondary.700"),
        },
        ".fg-def-4": {
          color: theme("colors.secondary.500"),
        },
        // fg inverse
        ".fg-inv-1": {
          color: theme("colors.white"),
        },
        ".fg-inv-2": {
          color: theme("colors.secondary.100"),
        },
        ".fg-inv-3": {
          color: theme("colors.secondary.300"),
        },
        ".fg-inv-4": {
          color: theme("colors.secondary.400"),
        },

        // Border colors
        ".border-def-1": {
          borderColor: theme("colors.secondary.50"),
        },
        ".border-def-2": {
          borderColor: theme("colors.secondary.100"),
        },
        ".border-def-3": {
          borderColor: theme("colors.secondary.200"),
        },
        ".border-def-4": {
          borderColor: theme("colors.secondary.300"),
        },
        ".border-def-5": {
          borderColor: theme("colors.secondary.400"),
        },
        // border inverse
        ".border-inv-1": {
          borderColor: theme("colors.secondary.800"),
        },
        ".border-inv-2": {
          borderColor: theme("colors.secondary.900"),
        },
        ".border-inv-3": {
          borderColor: theme("colors.secondary.900"),
        },
        ".border-inv-4": {
          borderColor: theme("colors.secondary.950"),
        },
        ".border-inv-5": {
          borderColor: theme("colors.black"),
        },

        // Example: dark mode utilities (all elements within <html class="dark"> )
        // ".dark .bg-def-1": {
        //   backgroundColor: theme("colors.black"),
        // },
        // ".dark .bg-def-2": {
        //   backgroundColor: theme("colors.primary.900"),
        // },
        // ".dark .bg-def-3": {
        //   backgroundColor: theme("colors.primary.800"),
        // },
        // ".dark .bg-def-4": {
        //   backgroundColor: theme("colors.primary.700"),
        // },
        // ".dark .bg-def-5": {
        //   backgroundColor: theme("colors.primary.600"),
        // },
      });
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
        boxShadow: {
          "inner-primary":
            "2px 2px 0px 0px var(--clr-bg-inv-acc-3, #415E63) inset",
          "inner-primary-active":
            "0px 0px 0px 1px #FFF, 0px 0px 0px 2px var(--clr-bg-inv-acc-4, #203637), -2px -2px 0px 0px var(--clr-bg-inv-acc-1, #7B9B9F) inset",
          "inner-secondary":
            "-2px -2px 0px 0px #CEDFE2 inset, 2px 2px 0px 0px white inset",
          "inner-secondary-active":
            "0px 0px 0px 1px white, 0px 0px 0px 2px var(--clr-bg-inv-acc-4, #203637), 2px 2px 0px 0px var(--clr-bg-inv-acc-2, #4F747A) inset",
        },
      },
      ...typography,
    },
  }),
);
