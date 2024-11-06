#!/usr/bin/env -S deno run --allow-env --allow-net --allow-read --allow-write
import "jsr:@std/dotenv/load";
import type { FigmaNodeFile } from "./figma.types.ts";
import { optimize } from "svgo";

const FIGMA_ICON_FILE_ID = Deno.env.get("FIGMA_ICON_FILE_ID");
const FIGMA_TOKEN = Deno.env.get("FIGMA_TOKEN");
const FRAME_ID = Deno.env.get("FRAME_ID");
const OUT_DIR = Deno.env.get("OUT_DIR");

if (!FIGMA_ICON_FILE_ID) {
  console.error("env: FIGMA_ICON_FILE_ID is not set.");
  Deno.exit(2);
}
if (!FRAME_ID) {
  console.error("env: FRAME_ID is not set.");
  Deno.exit(2);
}
if (!FIGMA_TOKEN) {
  console.error("env: FIGMA_TOKEN is not set.");
  Deno.exit(2);
}

const raw = await fetch(
  `https://api.figma.com/v1/files/${FIGMA_ICON_FILE_ID}/nodes?ids=${FRAME_ID}`,
  {
    headers: {
      "X-FIGMA-TOKEN": FIGMA_TOKEN,
    },
  },
);

const figmaFile: FigmaNodeFile = await raw.json();

// @ts-ignore: could be an error response
if (figmaFile.status) {
  console.error(`Failed to fetch`, { figmaFile });
  Deno.exit();
}

const nodeId = FRAME_ID.replace("-", ":");
const iconComponentIds = Object.keys(figmaFile.nodes[nodeId].components);

const images = await fetch(
  `https://api.figma.com/v1/images/${FIGMA_ICON_FILE_ID}?ids=${iconComponentIds.join(
    ",",
  )}&format=svg`,
  {
    headers: {
      "X-FIGMA-TOKEN": FIGMA_TOKEN,
    },
  },
);

type ImageResonse =
  | {
      err: null;
      images: {
        [id: string]: string | null;
      };
    }
  | {
      err: string;
    };
const urlSet: ImageResonse = await images.json();

if (urlSet.err !== null) {
  console.error("Could not get image paths", { urlSet });
  Deno.exit(1);
}

const getNamefromType = (str: string) => {
  const [_type, name] = str.split("=");
  if (!name) {
    console.error("Icon doesnt have name", str);
    Deno.exit(1);
  }
  return name;
};

const final = await Promise.all(
  Object.entries(urlSet.images)
    .filter(([, url]) => url !== null)
    .map(async ([id, url]) => {
      const entry = figmaFile.nodes[nodeId].components[id];
      const rawSvg = await fetch(url as string);
      let svgText = await rawSvg.text();
      const replace = /fill=["']#?[0-9a-fA-F]{3,6}["']|fill=["'][a-zA-Z]+["']/g;
      svgText = svgText.replaceAll(replace, 'fill="currentColor"');

      const optimizedSvg = optimize(svgText, {}).data;
      return {
        name: getNamefromType(entry.name),
        file: optimizedSvg,
      };
    }),
);

const path = OUT_DIR;
if (!path) {
  console.error("OUT_DIR is not set");
  Deno.exit(1);
}

console.log(`Will write icons to: ${path}/*`);

final.filter(Boolean).forEach((i) => {
  const icon = i!;
  Deno.mkdirSync(path, { recursive: true });
  Deno.writeTextFileSync(`${path}/${icon.name}.svg`, icon.file);
  console.log(`Wrote: ${path}/${icon.name}.svg`);
});

console.info("All icons up to date");

export {};
