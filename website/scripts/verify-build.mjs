import { access, readFile, readdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const requiredFiles = [
  "dist/index.html",
  "dist/en/index.html",
  "dist/og.png",
  "dist/monitor.png",
  "dist/robots.txt",
  "dist/sitemap-index.xml",
  "dist/sitemap-0.xml"
];

await Promise.all(requiredFiles.map((file) => access(resolve(root, file))));

const pages = [
  { file: "dist/index.html", lang: "pt-BR", alternate: "/rdp-session-manager/en/" },
  { file: "dist/en/index.html", lang: "en", alternate: "/rdp-session-manager/" }
];

const requiredFragments = [
  'id="main"',
  'id="story"',
  'id="features"',
  'id="compatibility"',
  'id="install"',
  'data-demo-mode="desktop"',
  'data-demo-mode="linux"',
  'data-demo-mode="windows"',
  'data-experience-tab="desktop"',
  'data-experience-tab="cli"',
  'data-experience-panel="desktop"',
  'data-experience-panel="cli"',
  'data-cli-source=',
  'data-copy',
  'application/ld+json'
];

for (const page of pages) {
  const html = await readFile(resolve(root, page.file), "utf8");
  if (!html.includes(`<html lang="${page.lang}">`)) throw new Error(`${page.file}: language metadata is missing`);
  if (!html.includes(`href="${page.alternate}"`)) throw new Error(`${page.file}: language switch is missing`);
  for (const fragment of requiredFragments) {
    if (!html.includes(fragment)) throw new Error(`${page.file}: required fragment ${fragment} is missing`);
  }
  const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((match) => match[1]);
  const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
  if (duplicates.length) throw new Error(`${page.file}: duplicate IDs: ${[...new Set(duplicates)].join(", ")}`);
}

const assetFiles = await readdir(resolve(root, "dist/_astro"));
const cssFiles = assetFiles.filter((file) => file.endsWith(".css"));
const css = (await Promise.all(cssFiles.map((file) => readFile(resolve(root, "dist/_astro", file), "utf8")))).join("\n");
if (!css.includes("prefers-reduced-motion")) throw new Error("Reduced-motion fallback is missing from the built CSS");

console.log("Static verification passed for PT-BR and EN pages.");
