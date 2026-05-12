import type { EditStartRequest, JobResponse, PageResponse, UploadResponse } from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, init);
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json() as Promise<T>;
}

async function errorMessage(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) return response.statusText;
  try {
    const payload = JSON.parse(text) as { message?: string; detail?: string };
    return payload.message || payload.detail || text;
  } catch {
    return text;
  }
}

export function assetUrl(url?: unknown): string {
  if (!url || typeof url !== "string") return "";
  if (url.startsWith("http")) return url;
  return `${API_BASE}${url}`;
}

export async function uploadPdf(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return requestJson<UploadResponse>("/api/upload", {
    method: "POST",
    body: form
  });
}

export async function getPage(documentId: string, pageNumber: number): Promise<PageResponse> {
  return requestJson<PageResponse>(`/api/document/${documentId}/page/${pageNumber}`);
}

export async function startEdit(payload: EditStartRequest): Promise<{ job_id: string }> {
  return requestJson<{ job_id: string }>("/api/edit/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

export async function getJob(jobId: string): Promise<JobResponse> {
  return requestJson<JobResponse>(`/api/edit/job/${jobId}`);
}

export async function applyEdit(documentId: string, jobId: string): Promise<{ success: boolean; page_preview_url: string }> {
  return requestJson<{ success: boolean; page_preview_url: string }>("/api/edit/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, job_id: jobId })
  });
}

export async function exportPdf(documentId: string, jobId?: string): Promise<{ download_url: string }> {
  const suffix = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
  return requestJson<{ download_url: string }>(`/api/document/${documentId}/export${suffix}`, {
    method: "POST"
  });
}

export function createJobEventSource(jobId: string): EventSource {
  return new EventSource(`${API_BASE}/api/edit/job/${jobId}/stream`);
}
