import json
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.utils.config import settings


DEFAULT_STEPS = [
    ("upload_pdf", "上传 PDF"),
    ("render_page", "页面渲染"),
    ("map_coordinates", "坐标映射"),
    ("crop_region", "区域裁剪"),
    ("ocr", "OCR"),
    ("expand_instruction", "指令增强"),
    ("image_edit", "图像编辑"),
    ("compose_preview", "页面回贴预览"),
    ("apply_edit", "应用修改"),
    ("export_pdf", "PDF 导出"),
]


class JobService:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def create_job(self, document_id: str) -> str:
        job_id = f"job_{uuid4().hex}"
        steps = [
            {"key": key, "name": name, "status": "pending", "error": None}
            for key, name in DEFAULT_STEPS
        ]
        job = {
            "job_id": job_id,
            "document_id": document_id,
            "status": "pending",
            "steps": steps,
            "logs": [],
            "artifacts": {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with self._lock:
            self._jobs[job_id] = job
            self._persist(job_id)
        return job_id

    def snapshot(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            if job_id not in self._jobs:
                self._load(job_id)
            if job_id not in self._jobs:
                raise KeyError(f"Job not found: {job_id}")
            return deepcopy(self._jobs[job_id])

    def set_status(self, job_id: str, status: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = status
            job["updated_at"] = datetime.now().isoformat()
            self._persist(job_id)

    def set_step(self, job_id: str, key: str, status: str, error: str | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for step in job["steps"]:
                if step["key"] == key:
                    step["status"] = status
                    step["error"] = error
                    break
            job["updated_at"] = datetime.now().isoformat()
            if status == "failed":
                job["status"] = "failed"
            elif job["status"] == "pending":
                job["status"] = "running"
            self._persist(job_id)

    def succeed_step(self, job_id: str, key: str) -> None:
        self.set_step(job_id, key, "success")

    def fail_step(self, job_id: str, key: str, error: str) -> None:
        self.set_step(job_id, key, "failed", error)

    def add_log(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["logs"].append(
                {"time": datetime.now().strftime("%H:%M:%S"), "message": message}
            )
            job["updated_at"] = datetime.now().isoformat()
            self._persist(job_id)

    def set_artifact(self, job_id: str, key: str, value: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["artifacts"][key] = value
            job["updated_at"] = datetime.now().isoformat()
            self._persist(job_id)

    def _job_path(self, job_id: str) -> Path:
        return settings.LOG_DIR / f"{job_id}.json"

    def _persist(self, job_id: str) -> None:
        path = self._job_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._jobs[job_id], ensure_ascii=False, indent=2), "utf-8")

    def _load(self, job_id: str) -> None:
        path = self._job_path(job_id)
        if path.exists():
            self._jobs[job_id] = json.loads(path.read_text("utf-8"))


job_service = JobService()
