export type StepStatus = "pending" | "running" | "success" | "failed";
export type JobStatus = "pending" | "running" | "awaiting_apply" | "success" | "failed";

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  total_pages: number;
}

export interface PageResponse {
  document_id: string;
  page_number: number;
  page_image_url: string;
  width: number;
  height: number;
}

export interface StepInfo {
  key: string;
  name: string;
  status: StepStatus;
  error?: string | null;
}

export interface LogItem {
  time: string;
  message: string;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  document_id: string;
  steps: StepInfo[];
  logs: LogItem[];
  artifacts: Record<string, unknown>;
}

export interface EditStartRequest {
  document_id: string;
  page_number: number;
  display_bbox: BBox;
  display_size: Size;
  instruction: string;
}
