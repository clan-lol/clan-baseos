import { For } from "solid-js";

function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), 1 | t);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function calculateCellColor(
  x: number,
  y: number,
  grid: number[][],
  rand: () => number,
) {
  const rows = grid.length;
  const cols = grid[0].length;

  // Get the values of neighboring cells
  const neighbors = [
    grid[y][(x - 1 + cols) % cols], // Left
    grid[y][(x + 1) % cols], // Right
    grid[(y - 1 + rows) % rows][x], // Top
    grid[(y + 1) % rows][x], // Bottom
  ];

  const makeValue = (threshold: number, wanted: number) =>
    rand() > threshold ? Math.floor(rand() * 50) : wanted;

  // Calculate the sum of neighbors
  const neighborSum = neighbors.reduce((sum, val) => sum + val, 0);
  // Introduce a hard cutoff for fewer intermediate values
  if (neighborSum < 1) {
    // Mostly dark squares
    // return Math.floor(rand() * 50); // Darker square
    return makeValue(0.9, Math.floor(rand() * 50));
  } else if (neighborSum >= 3) {
    // Mostly bright squares
    // return Math.floor(200 + rand() * 55); // Bright square
    return makeValue(0.9, Math.floor(200 + rand() * 55));
  } else {
    // Rare intermediate values
    return makeValue(0.4, Math.floor(100 + rand() * 50));
  }
}

function generatePatternedImage(seed: number, width = 300, height = 150) {
  const rand = mulberry32(seed);
  const rowSize = 1 + Math.floor((rand() * width) / 10);
  const colSize = 1 + Math.floor((rand() * height) / 10);
  const cols = Math.floor(width / colSize);
  const rows = Math.floor(height / rowSize);

  // Initialize a 2D grid with random values (0 or 1)
  const grid = Array.from({ length: rows }, () =>
    Array.from({ length: cols }, () => (rand() > 0.5 ? 1 : 0)),
  );

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  if (!ctx) {
    throw new Error("Could not get 2d context");
  }

  const centerX = width / 2;
  const centerY = height / 2;
  const totalCells = rows * cols;
  for (let i = 0; i < totalCells; i++) {
    // Calculate polar coordinates
    const angle = (i / totalCells) * Math.PI * 2 * rand() * 360; // Increase the spiral's density
    const radius = Math.sqrt(i) * rand() * 4; // Controls how tightly the spiral is packed

    // Convert polar to Cartesian coordinates
    const x = Math.floor(centerX + radius * Math.cos(angle));
    const y = Math.floor(centerY + radius * Math.sin(angle));

    // Find grid coordinates
    const col = Math.floor(x / colSize);
    const row = Math.floor(y / rowSize);

    // Ensure the cell is within bounds
    if (col >= 0 && col < cols && row >= 0 && row < rows) {
      const colorValue = calculateCellColor(col, row, grid, rand);
      ctx.fillStyle = `rgb(${colorValue}, ${colorValue}, ${colorValue})`;
      ctx.fillRect(x, y, colSize, rowSize);
    }
  }

  return canvas.toDataURL();
}

interface RndThumbnailProps {
  name: string;
  width?: number;
  height?: number;
}
export const RndThumbnail = (props: RndThumbnailProps) => {
  const { name } = props;
  const seed = Array.from(name).reduce(
    (acc, char) => acc + char.charCodeAt(0),
    0,
  ); // Seed from name
  const imageSrc = generatePatternedImage(seed, props.width, props.height);
  return <img src={imageSrc} alt={name} />;
};

export const RndThumbnailShow = () => {
  const names = ["hsjobeki", "mic92", "lassulus", "D", "A", "D", "B", "C"];

  return (
    <div class="grid grid-cols-4">
      <For each={names}>{(name) => <RndThumbnail name={name} />}</For>
    </div>
  );
};
