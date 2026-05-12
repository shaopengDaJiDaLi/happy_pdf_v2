import json
import shutil
from pathlib import Path
from uuid import uuid4

import fitz
from PIL import Image

from app.utils.config import data_url, settings


class PDFService:
    def save_upload(self, filename: str, content: bytes) -> dict:
        document_id = f"doc_{uuid4().hex}"
        safe_name = Path(filename).name or "uploaded.pdf"
        upload_dir = settings.UPLOAD_DIR / document_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = upload_dir / safe_name
        pdf_path.write_bytes(content)
        metadata = self.render_document(document_id, pdf_path, safe_name)
        return metadata

    def render_document(self, document_id: str, pdf_path: Path, filename: str) -> dict:
        doc_dir = settings.DOCUMENT_DIR / document_id
        current_dir = doc_dir / "current"
        render_dir = settings.RENDER_DIR / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        current_dir.mkdir(parents=True, exist_ok=True)
        render_dir.mkdir(parents=True, exist_ok=True)

        pdf = fitz.open(pdf_path)
        pages = []
        matrix = fitz.Matrix(settings.RENDER_SCALE, settings.RENDER_SCALE)

        for index, page in enumerate(pdf, start=1):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            render_path = render_dir / f"page_{index}.png"
            current_path = current_dir / f"page_{index}.png"
            pix.save(render_path)
            shutil.copyfile(render_path, current_path)
            pages.append(
                {
                    "page_number": index,
                    "render_path": str(render_path),
                    "current_path": str(current_path),
                    "render_width": pix.width,
                    "render_height": pix.height,
                    "original_width": float(page.rect.width),
                    "original_height": float(page.rect.height),
                }
            )

        metadata = {
            "document_id": document_id,
            "filename": filename,
            "pdf_path": str(pdf_path),
            "total_pages": len(pages),
            "render_scale": settings.RENDER_SCALE,
            "pages": pages,
        }
        self._metadata_path(document_id).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), "utf-8"
        )
        return metadata

    def get_metadata(self, document_id: str) -> dict:
        path = self._metadata_path(document_id)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {document_id}")
        return json.loads(path.read_text("utf-8"))

    def save_metadata(self, metadata: dict) -> None:
        self._metadata_path(metadata["document_id"]).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), "utf-8"
        )

    def get_page(self, document_id: str, page_number: int) -> dict:
        metadata = self.get_metadata(document_id)
        if page_number < 1 or page_number > metadata["total_pages"]:
            raise ValueError("page_number out of range")
        page = metadata["pages"][page_number - 1]
        current_path = Path(page["current_path"])
        if not current_path.exists():
            current_path = Path(page["render_path"])
        with Image.open(current_path) as image:
            width, height = image.size
        return {
            **page,
            "image_path": str(current_path),
            "width": width,
            "height": height,
            "url": data_url(current_path),
        }

    def set_current_page(self, document_id: str, page_number: int, image_path: Path) -> Path:
        metadata = self.get_metadata(document_id)
        page = metadata["pages"][page_number - 1]
        current_path = Path(page["current_path"])
        current_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(image_path, current_path)
        self.save_metadata(metadata)
        return current_path

    def export_pdf(self, document_id: str) -> Path:
        metadata = self.get_metadata(document_id)
        output_dir = settings.OUTPUT_DIR / document_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "edited.pdf"

        pdf = fitz.open()
        for page in metadata["pages"]:
            image_path = Path(page["current_path"])
            if not image_path.exists():
                image_path = Path(page["render_path"])
            pdf_page = pdf.new_page(
                width=page["original_width"],
                height=page["original_height"],
            )
            pdf_page.insert_image(pdf_page.rect, filename=str(image_path))
        pdf.save(output_path, garbage=4, deflate=True)
        pdf.close()
        return output_path

    def _metadata_path(self, document_id: str) -> Path:
        path = settings.DOCUMENT_DIR / document_id
        path.mkdir(parents=True, exist_ok=True)
        return path / "metadata.json"


pdf_service = PDFService()
