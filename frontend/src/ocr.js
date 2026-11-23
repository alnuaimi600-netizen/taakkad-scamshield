// On-device OCR. The image is processed in a Web Worker in the browser and is
// never uploaded. Tesseract downloads its engine and language files (ara+eng) once.
import { createWorker } from "tesseract.js";

let workerPromise = null;

function getWorker() {
  if (!workerPromise) workerPromise = createWorker(["ara", "eng"]);
  return workerPromise;
}

export async function readImage(file) {
  const worker = await getWorker();
  const { data } = await worker.recognize(file);
  return (data.text || "").replace(/\n{3,}/g, "\n\n").trim();
}
