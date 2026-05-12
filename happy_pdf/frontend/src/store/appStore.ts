import { create } from "zustand";
import type { BBox, JobResponse, PageResponse, Size, UploadResponse } from "../types/api";

interface AppState {
  document?: UploadResponse;
  page?: PageResponse;
  pageNumber: number;
  zoom: number;
  selection?: BBox;
  displaySize?: Size;
  instruction: string;
  job?: JobResponse;
  busy: boolean;
  error?: string;
  downloadUrl?: string;
  setDocument: (document?: UploadResponse) => void;
  setPage: (page?: PageResponse) => void;
  setPageNumber: (pageNumber: number) => void;
  setZoom: (zoom: number) => void;
  setSelection: (selection?: BBox, displaySize?: Size) => void;
  setInstruction: (instruction: string) => void;
  setJob: (job?: JobResponse) => void;
  setBusy: (busy: boolean) => void;
  setError: (error?: string) => void;
  setDownloadUrl: (downloadUrl?: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  pageNumber: 1,
  zoom: 0.35,
  instruction: "",
  busy: false,
  setDocument: (document) => set({ document, pageNumber: 1, job: undefined, downloadUrl: undefined }),
  setPage: (page) => set({ page, selection: undefined, displaySize: undefined }),
  setPageNumber: (pageNumber) => set({ pageNumber, selection: undefined, displaySize: undefined }),
  setZoom: (zoom) => set({ zoom: Math.max(0.12, Math.min(1.2, zoom)) }),
  setSelection: (selection, displaySize) => set({ selection, displaySize }),
  setInstruction: (instruction) => set({ instruction }),
  setJob: (job) => set({ job }),
  setBusy: (busy) => set({ busy }),
  setError: (error) => set({ error }),
  setDownloadUrl: (downloadUrl) => set({ downloadUrl })
}));
