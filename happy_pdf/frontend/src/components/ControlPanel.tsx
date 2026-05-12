import { Check, Download, Wand2 } from "lucide-react";
import { applyEdit, assetUrl, exportPdf, getJob, getPage, startEdit } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { JobResponse, StepInfo } from "../types/api";

export function ControlPanel() {
  const {
    document,
    page,
    pageNumber,
    selection,
    displaySize,
    instruction,
    job,
    busy,
    error,
    downloadUrl,
    setBusy,
    setError,
    setInstruction,
    setJob,
    setPage,
    setDownloadUrl
  } = useAppStore();

  async function handleStart() {
    if (!document || !page || !selection || !displaySize || !instruction.trim()) {
      setError("请先上传 PDF、框选区域，并输入修改指令。");
      return;
    }
    setBusy(true);
    setError(undefined);
    setDownloadUrl(undefined);
    try {
      const result = await startEdit({
        document_id: document.document_id,
        page_number: pageNumber,
        display_bbox: selection,
        display_size: displaySize,
        instruction: instruction.trim()
      });
      setJob({
        job_id: result.job_id,
        status: "pending",
        document_id: document.document_id,
        steps: [],
        logs: [{ time: new Date().toLocaleTimeString(), message: "编辑任务已提交" }],
        artifacts: {}
      });
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleApply() {
    if (!document || !job) return;
    setBusy(true);
    setError(undefined);
    try {
      const result = await applyEdit(document.document_id, job.job_id);
      const refreshedPage = await getPage(document.document_id, pageNumber);
      setPage({ ...refreshedPage, page_image_url: result.page_preview_url });
      const updatedJob = await getJob(job.job_id);
      setJob(updatedJob);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleExport() {
    if (!document) return;
    setBusy(true);
    setError(undefined);
    try {
      const result = await exportPdf(document.document_id, job?.job_id);
      setDownloadUrl(assetUrl(result.download_url));
      if (job?.job_id) {
        const updatedJob = await getJob(job.job_id);
        setJob(updatedJob);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  const bboxText = selection
    ? `x=${selection.x.toFixed(0)}, y=${selection.y.toFixed(0)}, w=${selection.width.toFixed(0)}, h=${selection.height.toFixed(0)}`
    : "暂无选区";
  const imageBBox = job?.artifacts?.bbox as
    | { x?: number; y?: number; width?: number; height?: number }
    | undefined;
  const imageBBoxText =
    imageBBox?.width && imageBBox?.height
      ? `x=${imageBBox.x ?? 0}, y=${imageBBox.y ?? 0}, w=${imageBBox.width}, h=${imageBBox.height}`
      : "-";

  return (
    <aside className="sidePanel">
      <section className="panelBlock">
        <div className="panelTitle">选区信息</div>
        <dl className="infoGrid">
          <dt>文档</dt>
          <dd>{document?.filename ?? "未上传"}</dd>
          <dt>页码</dt>
          <dd>{document ? pageNumber : "-"}</dd>
          <dt>前端坐标</dt>
          <dd>{bboxText}</dd>
          <dt>图像坐标</dt>
          <dd>{imageBBoxText}</dd>
          <dt>裁剪尺寸</dt>
          <dd>
            {imageBBox?.width && imageBBox?.height ? `${imageBBox.width} x ${imageBBox.height}` : "-"}
          </dd>
        </dl>
      </section>

      <section className="panelBlock">
        <div className="panelTitle">修改指令</div>
        <textarea
          value={instruction}
          onChange={(event) => setInstruction(event.target.value)}
          placeholder="例如：日期改成 2026.12.11"
          rows={3}
        />
        <button className="primaryButton" onClick={handleStart} disabled={busy}>
          <Wand2 size={18} />
          生成修改
        </button>
        <div className="buttonRow">
          <button onClick={handleApply} disabled={busy || job?.status !== "awaiting_apply"}>
            <Check size={17} />
            应用到 PDF
          </button>
          <button onClick={handleExport} disabled={busy || !document}>
            <Download size={17} />
            导出 PDF
          </button>
        </div>
        {downloadUrl && (
          <a className="downloadLink" href={downloadUrl} download>
            <Download size={16} />
            下载 edited.pdf
          </a>
        )}
        {error && <div className="errorBox">{error}</div>}
      </section>

      <PreviewPanel job={job} />
      <StepPanel steps={job?.steps ?? []} />
    </aside>
  );
}

function PreviewPanel({ job }: { job?: JobResponse }) {
  const cropBefore = assetUrl(job?.artifacts?.crop_before_url);
  const cropAfter = assetUrl(job?.artifacts?.crop_after_url);
  const pagePreview = assetUrl(job?.artifacts?.page_preview_url);

  return (
    <section className="panelBlock">
      <div className="panelTitle">结果预览</div>
      <div className="cropGrid">
        <PreviewImage title="原始选区" url={cropBefore} />
        <PreviewImage title="编辑后选区" url={cropAfter} />
      </div>
      <PreviewImage title="回贴整页预览" url={pagePreview} wide />
    </section>
  );
}

function PreviewImage({ title, url, wide = false }: { title: string; url: string; wide?: boolean }) {
  return (
    <div className={wide ? "previewBox wide" : "previewBox"}>
      <div className="previewTitle">{title}</div>
      {url ? <img src={url} alt={title} /> : <div className="previewEmpty">等待生成</div>}
    </div>
  );
}

function StepPanel({ steps }: { steps: StepInfo[] }) {
  return (
    <section className="panelBlock">
      <div className="panelTitle">当前步骤状态</div>
      <div className="stepList">
        {steps.length === 0 && <div className="muted">任务开始后显示步骤状态</div>}
        {steps.map((step, index) => (
          <div className="stepItem" key={step.key}>
            <span className={`statusDot ${step.status}`} />
            <span className="stepName">
              {index + 1}. {step.name}
            </span>
            <span className={`statusText ${step.status}`}>{statusLabel(step.status)}</span>
            {step.error && <div className="stepError">{step.error}</div>}
          </div>
        ))}
      </div>
    </section>
  );
}

function statusLabel(status: StepInfo["status"]) {
  return {
    pending: "pending",
    running: "running",
    success: "success",
    failed: "failed"
  }[status];
}
