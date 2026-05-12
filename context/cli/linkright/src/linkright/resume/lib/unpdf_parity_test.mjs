// Parity test: extract text via unpdf (prod library) and emit to stdout.
// Mirrors the exact call pattern from repo/website/src/app/api/onboarding/parse-resume/route.ts:137-149.
//
// Usage: node unpdf_parity_test.mjs <path-to-pdf>

import { readFile } from "node:fs/promises";
// Direct path into repo/website/node_modules to avoid local install.
import { extractText, getDocumentProxy } from "/Users/satvikjain/Documents/linkright_production/repo/website/node_modules/unpdf/dist/index.mjs";

const [, , pdfPath] = process.argv;
if (!pdfPath) {
  console.error("Usage: node unpdf_parity_test.mjs <path-to-pdf>");
  process.exit(2);
}

try {
  const buf = await readFile(pdfPath);
  const pdf = await getDocumentProxy(new Uint8Array(buf));
  const { text } = await extractText(pdf, { mergePages: true });
  const out = Array.isArray(text) ? text.join("\n") : text;
  process.stdout.write(out);
} catch (e) {
  console.error("unpdf error:", e);
  process.exit(1);
}
