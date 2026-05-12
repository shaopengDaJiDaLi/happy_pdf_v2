from pathlib import Path

from PIL import Image

from app.utils.config import settings


class OCRService:
    def extract_text(self, image_path: Path) -> dict[str, str]:
        engine = settings.OCR_ENGINE
        if engine in {"none", "off", "disabled"}:
            return {"engine": "none", "text": ""}

        if engine in {"auto", "tesseract"}:
            try:
                import pytesseract

                with Image.open(image_path) as image:
                    text = pytesseract.image_to_string(image, lang=settings.OCR_LANG)
                return {"engine": "tesseract", "text": text.strip()}
            except Exception as exc:
                if engine == "tesseract":
                    raise RuntimeError(f"Tesseract OCR failed: {exc}") from exc

        if engine in {"auto", "paddle", "paddleocr"}:
            try:
                from paddleocr import PaddleOCR

                ocr = PaddleOCR(use_angle_cls=True, lang="ch")
                result = ocr.ocr(str(image_path), cls=True)
                fragments: list[str] = []
                for page in result or []:
                    for line in page or []:
                        if len(line) >= 2 and line[1]:
                            fragments.append(str(line[1][0]))
                return {"engine": "paddleocr", "text": "\n".join(fragments).strip()}
            except Exception as exc:
                if engine in {"paddle", "paddleocr"}:
                    raise RuntimeError(f"PaddleOCR failed: {exc}") from exc

        return {"engine": "unavailable", "text": ""}


ocr_service = OCRService()
