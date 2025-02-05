import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import tailwind from "eslint-plugin-tailwindcss";
import pluginQuery from "@tanstack/eslint-plugin-query";

export default tseslint.config(
  eslint.configs.recommended,
  ...pluginQuery.configs["flat/recommended"],
  ...tseslint.configs.strict,
  ...tseslint.configs.stylistic,
  ...tailwind.configs["flat/recommended"],
  {
    rules: {
      "tailwindcss/no-contradicting-classname": [
        "error",
        {
          callees: ["cx"],
        },
      ],
      "tailwindcss/no-custom-classname": [
        "error",
        {
          callees: ["cx"],
          whitelist: ["material-icons"],
        },
      ],
      // TODO: make this more strict by removing later
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
);
