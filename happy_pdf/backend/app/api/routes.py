import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.schemas.api import (
    ApplyEditRequest,
    ApplyEditResponse,
    EditStartRequest,
    EditStartResponse,
    ExportResponse,
    JobResponse,
    PageResponse,
    UploadResponse,
)
from app.services.coord_service import coord_service
from app.services.image_edit_service import image_edit_service
from app.services.image_service import image_service
from app.services.instruction_service import instruction_service
from app.services.job_service import job_service
from app.services.ocr_service import ocr_service
from app.services.pdf_service import pdf_service
from app.utils.config import data_url, settings

router = APIRouter(prefix="/api")


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        metadata = pdf_service.save_upload(file.filename, content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {exc}") from exc
    return UploadResponse(
        document_id=metadata["document_id"],
        filename=metadata["filename"],
        total_pages=metadata["total_pages"],
    )


@router.get("/document/{document_id}/page/{page_number}", response_model=PageResponse)
async def get_page(document_id: str, page_number: int) -> PageResponse:
    try:
        page = pdf_service.get_page(document_id, page_number)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PageResponse(
        document_id=document_id,
        page_number=page_number,
        page_image_url=page["url"],
        width=page["width"],
        height=page["height"],
    )


@router.post("/edit/start", response_model=EditStartResponse)
async def start_edit(
    request: EditStartRequest, background_tasks: BackgroundTasks
) -> EditStartResponse:
    try:
        pdf_service.get_metadata(request.document_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    job_id = job_service.create_job(request.document_id)
    background_tasks.add_task(run_edit_pipeline, job_id, request)
    return EditStartResponse(job_id=job_id)


@router.get("/edit/job/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    try:
        return JobResponse(**job_service.snapshot(job_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/edit/job/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    async def event_stream():
        last_payload = ""
        while True:
            try:
                snapshot = job_service.snapshot(job_id)
            except KeyError:
                yield "event: error\ndata: {\"message\":\"job not found\"}\n\n"
                return
            payload = json.dumps(snapshot, ensure_ascii=False)
            if payload != last_payload:
                yield f"data: {payload}\n\n"
                last_payload = payload
            if snapshot["status"] in {"awaiting_apply", "success", "failed"}:
                yield f"event: done\ndata: {payload}\n\n"
                return
            await asyncio.sleep(0.8)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/edit/apply", response_model=ApplyEditResponse)
async def apply_edit(request: ApplyEditRequest) -> ApplyEditResponse:
    try:
        job = job_service.snapshot(request.job_id)
        if job["document_id"] != request.document_id:
            raise ValueError("job does not belong to document")
        composed_path = Path(job["artifacts"]["page_preview_path"])
        page_number = int(job["artifacts"]["page_number"])
        job_service.set_step(request.job_id, "apply_edit", "running")
        job_service.add_log(request.job_id, "用户确认应用修改，正在更新当前页面")
        current_path = pdf_service.set_current_page(
            request.document_id, page_number, composed_path
        )
        job_service.set_artifact(request.job_id, "applied_page_url", data_url(current_path))
        job_service.succeed_step(request.job_id, "apply_edit")
        job_service.add_log(request.job_id, "局部修改已应用到 PDF 当前页面")
        job_service.set_status(request.job_id, "success")
        return ApplyEditResponse(success=True, page_preview_url=data_url(current_path))
    except Exception as exc:
        try:
            job_service.fail_step(request.job_id, "apply_edit", str(exc))
            job_service.add_log(request.job_id, f"应用修改失败：{exc}")
        finally:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/document/{document_id}/export", response_model=ExportResponse)
async def export_document(
    document_id: str, job_id: str | None = Query(default=None)
) -> ExportResponse:
    try:
        if job_id:
            job_service.set_step(job_id, "export_pdf", "running")
            job_service.add_log(job_id, "正在导出新 PDF")
        output_path = pdf_service.export_pdf(document_id)
        if job_id:
            job_service.set_artifact(job_id, "download_url", data_url(output_path))
            job_service.succeed_step(job_id, "export_pdf")
            job_service.add_log(job_id, "PDF 导出完成")
    except Exception as exc:
        if job_id:
            job_service.fail_step(job_id, "export_pdf", str(exc))
            job_service.add_log(job_id, f"PDF 导出失败：{exc}")
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {exc}") from exc
    return ExportResponse(download_url=data_url(output_path))


def run_edit_pipeline(job_id: str, request: EditStartRequest) -> None:
    step = "render_page"
    try:
        job_service.set_status(job_id, "running")
        job_service.succeed_step(job_id, "upload_pdf")
        job_service.add_log(job_id, "开始编辑任务")

        job_service.set_step(job_id, "render_page", "running")
        page = pdf_service.get_page(request.document_id, request.page_number)
        page_image_path = Path(page["image_path"])
        job_service.set_artifact(job_id, "page_number", request.page_number)
        job_service.set_artifact(job_id, "page_image_url", page["url"])
        job_service.succeed_step(job_id, "render_page")
        job_service.add_log(
            job_id,
            f"页面渲染完成：第 {request.page_number} 页，原始图像 {page['width']}x{page['height']}",
        )

        step = "map_coordinates"
        job_service.set_step(job_id, step, "running")
        bbox = coord_service.map_display_to_image(
            request.display_bbox,
            request.display_size,
            page["width"],
            page["height"],
        )
        job_service.set_artifact(job_id, "display_bbox", request.display_bbox.model_dump())
        job_service.set_artifact(job_id, "display_size", request.display_size.model_dump())
        job_service.set_artifact(job_id, "bbox", bbox)
        job_service.succeed_step(job_id, step)
        job_service.add_log(
            job_id,
            f"坐标映射完成：display_bbox=({request.display_bbox.x:.0f}, "
            f"{request.display_bbox.y:.0f}, {request.display_bbox.width:.0f}, "
            f"{request.display_bbox.height:.0f}) -> image_bbox=({bbox['x']}, "
            f"{bbox['y']}, {bbox['width']}, {bbox['height']})",
        )

        step = "crop_region"
        job_service.set_step(job_id, step, "running")
        crop_dir = settings.CROP_DIR / job_id
        crop_before_path = crop_dir / "crop_before.png"
        image_service.crop_region(page_image_path, bbox, crop_before_path)
        crop_before_url = data_url(crop_before_path)
        job_service.set_artifact(job_id, "crop_before_path", str(crop_before_path))
        job_service.set_artifact(job_id, "crop_before_url", crop_before_url)
        job_service.succeed_step(job_id, step)
        job_service.add_log(
            job_id,
            f"局部裁剪完成：x={bbox['x']}, y={bbox['y']}, width={bbox['width']}, height={bbox['height']}",
        )

        step = "ocr"
        job_service.set_step(job_id, step, "running")
        ocr_result = ocr_service.extract_text(crop_before_path)
        ocr_text = ocr_result["text"]
        job_service.set_artifact(job_id, "ocr", ocr_result)
        job_service.succeed_step(job_id, step)
        job_service.add_log(
            job_id,
            f"OCR 完成（{ocr_result['engine']}）：{ocr_text or '未识别到可靠文本'}",
        )

        step = "expand_instruction"
        job_service.set_step(job_id, step, "running")
        job_service.add_log(job_id, f"正在调用 TEXT API 生成增强编辑指令：{settings.TEXT_OPENAI_MODEL}")
        instruction_result = instruction_service.enhance(request.instruction, ocr_text)
        job_service.set_artifact(job_id, "edit_spec", instruction_result.edit_spec)
        job_service.set_artifact(
            job_id, "enhanced_edit_prompt", instruction_result.enhanced_edit_prompt
        )
        job_service.set_artifact(job_id, "instruction_mode", instruction_result.mode)
        job_service.succeed_step(job_id, step)
        job_service.add_log(job_id, f"增强编辑指令已生成（{instruction_result.mode}）")

        step = "image_edit"
        job_service.set_step(job_id, step, "running")
        job_service.add_log(job_id, f"正在调用 IMAGE API：{settings.IMAGE_OPENAI_MODEL}")
        edit_dir = settings.EDIT_DIR / job_id
        crop_after_path = edit_dir / "crop_after.png"
        edit_result = image_edit_service.edit_image(
            crop_before_path,
            instruction_result.enhanced_edit_prompt,
            crop_after_path,
            instruction_result.edit_spec,
            request.instruction,
        )
        job_service.set_artifact(job_id, "crop_after_path", str(crop_after_path))
        job_service.set_artifact(job_id, "crop_after_url", data_url(crop_after_path))
        job_service.set_artifact(job_id, "image_edit_mode", edit_result["mode"])
        job_service.succeed_step(job_id, step)
        job_service.add_log(job_id, f"图像编辑完成（{edit_result['mode']}）")

        step = "compose_preview"
        job_service.set_step(job_id, step, "running")
        page_preview_path = edit_dir / "page_preview.png"
        image_service.compose_preview(page_image_path, crop_after_path, bbox, page_preview_path)
        job_service.set_artifact(job_id, "page_preview_path", str(page_preview_path))
        job_service.set_artifact(job_id, "page_preview_url", data_url(page_preview_path))
        job_service.succeed_step(job_id, step)
        job_service.add_log(job_id, "整页回贴预览完成，等待用户确认应用")
        job_service.set_status(job_id, "awaiting_apply")
    except Exception as exc:
        job_service.fail_step(job_id, step, str(exc))
        job_service.add_log(job_id, f"任务失败：{exc}")
