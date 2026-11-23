// Inline the partner logos into dist-demo/index.html so the demo is one self-contained file.
import { readFileSync, writeFileSync } from "node:fs";

const out = "dist-demo/index.html";
let html = readFileSync(out, "utf8");
for (const name of ["adpolice.png", "42-abudhabi.png"]) {
  const data = readFileSync(`public/partners/${name}`).toString("base64");
  html = html.replaceAll(`/partners/${name}`, `data:image/png;base64,${data}`);
}
writeFileSync(out, html);
