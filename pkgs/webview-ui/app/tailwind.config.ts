import typography from "@tailwindcss/typography";
import daisyui from "daisyui";
import core from "./tailwind/core-plugin";

/** @type {import('tailwindcss').Config} */
const config = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    colors: {
      secondary: {
        50: "#f7f9f9",
        100: "#e7f2f4",
        200: "#d7e8ea",
        300: "#afc6ca",
        400: "#8fb2b6",
        500: "#7b9a9e",
        600: "#4f747a",
        700: "#415e63",
        800: "#445f64",
        900: "#2b4347",
        950: "#0d1415",
      },
    },
  },
  daisyui: {
    themes: [
      {
        light_clan: {
          primary: "#29b1eb",
          secondary: "#4d6a6b",
          accent: "#37cdbe",
          neutral: "#3d4451",
          error: "#ff2c78",
          success: "#0ae856",
          warning: "#ffdd2c",
          "base-100": "#F7F9FA",
          "base-content": "#0D1416",
        },
      },
    ],
  },
  plugins: [typography, core, daisyui],
};

export default config;
