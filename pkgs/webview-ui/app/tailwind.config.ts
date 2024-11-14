import typography from "@tailwindcss/typography";
import daisyui from "daisyui";
import core from "./tailwind/core-plugin";

/** @type {import('tailwindcss').Config} */
const config = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {},
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
  plugins: [typography, daisyui, core],
};

export default config;
