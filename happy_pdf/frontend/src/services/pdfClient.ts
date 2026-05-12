import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

export async function inspectPdf(file: File): Promise<{ pages: number }> {
  const buffer = await file.arrayBuffer();
  const document = await pdfjsLib.getDocument({ data: buffer }).promise;
  return { pages: document.numPages };
}
