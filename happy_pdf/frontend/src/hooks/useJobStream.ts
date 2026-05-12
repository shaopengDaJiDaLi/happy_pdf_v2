import { useEffect } from "react";
import { createJobEventSource, getJob } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { JobResponse } from "../types/api";

export function useJobStream(jobId?: string) {
  const setJob = useAppStore((state) => state.setJob);
  const setError = useAppStore((state) => state.setError);

  useEffect(() => {
    if (!jobId) return undefined;
    let closed = false;
    const source = createJobEventSource(jobId);

    source.onmessage = (event) => {
      if (closed) return;
      const job = JSON.parse(event.data) as JobResponse;
      setJob(job);
    };

    source.addEventListener("done", (event) => {
      if (closed) return;
      const job = JSON.parse((event as MessageEvent).data) as JobResponse;
      setJob(job);
      source.close();
    });

    source.onerror = async () => {
      if (closed) return;
      source.close();
      try {
        const job = await getJob(jobId);
        setJob(job);
      } catch (error) {
        setError(error instanceof Error ? error.message : String(error));
      }
    };

    return () => {
      closed = true;
      source.close();
    };
  }, [jobId, setError, setJob]);
}
