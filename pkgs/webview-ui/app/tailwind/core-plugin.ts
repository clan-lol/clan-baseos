import plugin from "tailwindcss/plugin";
import { typography } from "./typography";
import theme from "tailwindcss/defaultTheme";

export default plugin.withOptions(
  (_options = {}) =>
    () => {
      // add more base styles
    },
  // add configuration which is merged with the final config
  () => ({
    theme: {
      ...typography,
    },
  }),
);
