import { ChangeEvent, MouseEvent, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, FileUp, Minus, Plus } from "lucide-react";
import { inspectPdf } from "../services/pdfClient";
import { assetUrl, getPage, uploadPdf } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { BBox } from "../types/api";

interface DragState {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

export function PdfWorkspace() {
  const imageWrapRef = useRef<HTMLDivElement | null>(null);
  const [drag, setDrag] = useState<DragState | null>(null);
  const {
    document,
    page,
    pageNumber,
    zoom,
    selection,
    busy,
    setBusy,
    setDocument,
    setError,
    setPage,
    setPageNumber,
    setSelection,
    setZoom
  } = useAppStore();

  const displaySize = useMemo(() => {
    if (!page) return undefined;
    return {
      width: Math.round(page.width * zoom),
      height: Math.round(page.height * zoom)
    };
  }, [page, zoom]);

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(undefined);
    try {
      await inspectPdf(file);
      const uploaded = await uploadPdf(file);
      setDocument(uploaded);
      const firstPage = await getPage(uploaded.document_id, 1);
      setPage(firstPage);
      setPageNumber(1);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function changePage(nextPage: number) {
    if (!document || nextPage < 1 || nextPage > document.total_pages) return;
    setBusy(true);
    setError(undefined);
    try {
      const loaded = await getPage(document.document_id, nextPage);
      setPageNumber(nextPage);
      setPage(loaded);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  function localPoint(event: MouseEvent<HTMLDivElement>) {
    const rect = imageWrapRef.current?.getBoundingClientRect();
    if (!rect) return { x: 0, y: 0 };
    const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
    return { x, y };
  }

  function handleMouseDown(event: MouseEvent<HTMLDivElement>) {
    if (!page || !displaySize) return;
    const point = localPoint(event);
    setDrag({ startX: point.x, startY: point.y, currentX: point.x, currentY: point.y });
    setSelection(undefined);
  }

  function handleMouseMove(event: MouseEvent<HTMLDivElement>) {
    if (!drag) return;
    const point = localPoint(event);
    setDrag({ ...drag, currentX: point.x, currentY: point.y });
  }

  function finishDrag() {
    if (!drag || !displaySize) {
      setDrag(null);
      return;
    }
    const x = Math.min(drag.startX, drag.currentX);
    const y = Math.min(drag.startY, drag.currentY);
    const width = Math.abs(drag.currentX - drag.startX);
    const height = Math.abs(drag.currentY - drag.startY);
    setDrag(null);
    if (width >= 8 && height >= 8) {
      setSelection({ x, y, width, height }, displaySize);
    }
  }

  const liveSelection: BBox | undefined = drag
    ? {
        x: Math.min(drag.startX, drag.currentX),
        y: Math.min(drag.startY, drag.currentY),
        width: Math.abs(drag.currentX - drag.startX),
        height: Math.abs(drag.currentY - drag.startY)
      }
    : selection;

  return (
    <section className="workspace">
      <div className="topbar">
        <label className="uploadButton">
          <FileUp size={18} />
          <span>上传 PDF</span>
          <input type="file" accept="application/pdf" onChange={handleUpload} />
        </label>
        <div className="toolbarGroup">
          <button onClick={() => changePage(pageNumber - 1)} disabled={!document || pageNumber <= 1 || busy}>
            <ChevronLeft size={18} />
          </button>
          <span className="pageBadge">
            {document ? `${pageNumber} / ${document.total_pages}` : "未上传"}
          </span>
          <button
            onClick={() => changePage(pageNumber + 1)}
            disabled={!document || pageNumber >= (document?.total_pages ?? 1) || busy}
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <div className="toolbarGroup">
          <button onClick={() => setZoom(zoom - 0.06)} disabled={!page}>
            <Minus size={17} />
          </button>
          <span className="zoomBadge">{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom(zoom + 0.06)} disabled={!page}>
            <Plus size={17} />
          </button>
        </div>
      </div>

      <div className="documentStage">
        {!page && (
          <div className="emptyStage">
            <FileUp size={36} />
            <div>上传扫描版 PDF 后开始框选编辑区域</div>
          </div>
        )}
        {page && displaySize && (
          <div className="pageScroller">
            <div
              className="imageWrap"
              ref={imageWrapRef}
              style={{ width: displaySize.width, height: displaySize.height }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={finishDrag}
              onMouseLeave={finishDrag}
            >
              <img
                src={assetUrl(page.page_image_url)}
                alt={`第 ${page.page_number} 页`}
                draggable={false}
                style={{ width: displaySize.width, height: displaySize.height }}
              />
              {liveSelection && liveSelection.width > 0 && liveSelection.height > 0 && (
                <div
                  className="selectionBox"
                  style={{
                    left: liveSelection.x,
                    top: liveSelection.y,
                    width: liveSelection.width,
                    height: liveSelection.height
                  }}
                />
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
