from typing import Any, Literal

from pydantic import BaseModel, Field


StepStatus = Literal["pending", "running", "success", "failed"]


class BBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class Size(BaseModel):
    width: float
    height: float


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    total_pages: int


class PageResponse(BaseModel):
    document_id: str
    page_number: int
    page_image_url: str
    width: int
    height: int


class EditStartRequest(BaseModel):
    document_id: str
    page_number: int = Field(ge=1)
    display_bbox: BBox
    display_size: Size
    instruction: str = Field(min_length=1)


class EditStartResponse(BaseModel):
    job_id: str


class ApplyEditRequest(BaseModel):
    document_id: str
    job_id: str


class ApplyEditResponse(BaseModel):
    success: bool
    page_preview_url: str


class ExportResponse(BaseModel):
    download_url: str


class StepInfo(BaseModel):
    key: str
    name: str
    status: StepStatus
    error: str | None = None


class LogItem(BaseModel):
    time: str
    message: str


class JobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "awaiting_apply", "success", "failed"]
    document_id: str
    steps: list[StepInfo]
    logs: list[LogItem]
    artifacts: dict[str, Any]
