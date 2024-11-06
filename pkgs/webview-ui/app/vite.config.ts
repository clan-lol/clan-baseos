import { defineConfig } from "vite";
import solidPlugin from "vite-plugin-solid";
import solidSvg from "vite-plugin-solid-svg";
import devtools from "solid-devtools/vite";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./"), // Adjust the path as needed
    },
  },
  plugins: [
    /*
    Uncomment the following line to enable solid-devtools.
    For more info see https://github.com/thetarnav/solid-devtools/tree/main/packages/extension#readme
    */
    devtools(),
    solidPlugin(),
    solidSvg(),
  ],
  server: {
    port: 3000,
  },
  build: {
    target: "safari11",
    //  assetsDi
    manifest: true,
  },
});
