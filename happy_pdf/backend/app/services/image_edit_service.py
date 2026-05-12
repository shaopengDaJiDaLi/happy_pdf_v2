import base64
import re
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageFont, ImageStat

from app.services.image_service import image_service
from app.utils.config import settings


IMAGE_STYLE_LOCK_PROMPT = (
    "FINAL STYLE LOCK: replace only the requested text. Copy the original target text's "
    "font/handwriting, font size, character height/width, spacing, baseline, slant, "
    "stroke thickness, color/gray value, opacity, blur, antialiasing, scan noise and "
    "compression artifacts exactly. Keep the new text in the same bounds and position. "
    "It must not be larger, smaller, bolder, thinner, darker, lighter, sharper, cleaner, "
    "more regular or shifted. Do not use a default font, redraw the area, improve "
    "legibility, change layout, background, table lines, brightness, contrast, resolution "
    "or crop size."
)


class ImageEditService:
    def edit_image(
        self,
        crop_before_path: Path,
        enhanced_prompt: str,
        crop_after_path: Path,
        edit_spec: dict[str, Any] | None = None,
        user_instruction: str | None = None,
    ) -> dict[str, str]:
        crop_after_path.parent.mkdir(parents=True, exist_ok=True)
        target_size = Image.open(crop_before_path).size

        if (
            settings.IMAGE_OPENAI_API_KEY
            and not settings.IMAGE_OPENAI_DISABLE
        ):
            try:
                final_prompt = self._style_locked_prompt(enhanced_prompt, edit_spec)
                self._openai_edit(crop_before_path, final_prompt, crop_after_path)
                image_service.normalize_size(crop_after_path, target_size)
                return {"mode": f"image_api:{settings.IMAGE_OPENAI_MODEL}"}
            except Exception as exc:
                if settings.IMAGE_FALLBACK_ON_ERROR:
                    self._local_fallback(
                        crop_before_path,
                        crop_after_path,
                        edit_spec,
                        user_instruction,
                    )
                    return {"mode": f"image_api_failed_fallback:{exc}"}
                raise RuntimeError(f"IMAGE API 图像编辑失败：{exc}") from exc

        self._local_fallback(crop_before_path, crop_after_path, edit_spec, user_instruction)
        return {"mode": "local_fallback"}

    def _openai_edit(self, crop_before_path: Path, prompt: str, crop_after_path: Path) -> None:
        from openai import OpenAI

        http_client = None
        if settings.IMAGE_PROXY_URL:
            http_client = httpx.Client(
                proxy=settings.IMAGE_PROXY_URL,
                timeout=settings.IMAGE_TIMEOUT_SECONDS,
            )
        client = OpenAI(
            api_key=settings.IMAGE_OPENAI_API_KEY,
            base_url=settings.IMAGE_OPENAI_BASE_URL,
            http_client=http_client,
            timeout=settings.IMAGE_TIMEOUT_SECONDS,
            max_retries=settings.IMAGE_MAX_RETRIES,
        )
        with crop_before_path.open("rb") as image_file:
            result = client.images.edit(
                model=settings.IMAGE_OPENAI_MODEL,
                image=image_file,
                prompt=prompt,
                quality="high",
                input_fidelity="high",
                output_format="png",
            )

        item = result.data[0]
        b64_json = getattr(item, "b64_json", None)
        url = getattr(item, "url", None)
        if b64_json:
            crop_after_path.write_bytes(base64.b64decode(b64_json))
            return
        if url:
            response = httpx.get(
                url,
                proxy=settings.IMAGE_PROXY_URL,
                timeout=settings.IMAGE_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            crop_after_path.write_bytes(response.content)
            return
        raise RuntimeError("image edit response did not include b64_json or url")

    def _local_fallback(
        self,
        crop_before_path: Path,
        crop_after_path: Path,
        edit_spec: dict[str, Any] | None,
        user_instruction: str | None,
    ) -> None:
        with Image.open(crop_before_path).convert("RGB") as image:
            output = image.copy()
            draw = ImageDraw.Draw(output, "RGBA")
            text = self._replacement_text(edit_spec, user_instruction or "")
            if not text:
                text = "edited"

            width, height = output.size
            ink_color = self._ink_color(output)
            font = self._fit_font(text, width, height, output)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = max(4, (width - text_w) // 2)
            y = max(4, (height - text_h) // 2)

            bg = self._paper_color(output)
            pad_x = max(8, int(width * 0.03))
            pad_y = max(4, int(height * 0.08))
            rect = (
                max(0, x - pad_x),
                max(0, y - pad_y),
                min(width, x + text_w + pad_x),
                min(height, y + text_h + pad_y),
            )
            draw.rectangle(rect, fill=(*bg, 214))
            draw.text((x, y), text, fill=(*ink_color, 235), font=font)
            output.save(crop_after_path)

    def _replacement_text(
        self, edit_spec: dict[str, Any] | None, user_instruction: str
    ) -> str:
        if edit_spec and edit_spec.get("replacement_text"):
            return str(edit_spec["replacement_text"])
        match = re.search(r"改成\s*(.+)", user_instruction)
        return match.group(1).strip() if match else ""

    def _style_locked_prompt(
        self,
        enhanced_prompt: str,
        edit_spec: dict[str, Any] | None,
    ) -> str:
        target = str((edit_spec or {}).get("target_text") or "").strip()
        replacement = str((edit_spec or {}).get("replacement_text") or "").strip()
        target_line = ""
        if target or replacement:
            target_line = (
                f"\nTarget replacement: replace {target or 'the requested target text'} "
                f"with {replacement or 'the requested new text'} while copying the original target text style exactly."
            )
        if "FINAL NON-NEGOTIABLE STYLE MATCHING RULES" in enhanced_prompt:
            return enhanced_prompt
        return f"{enhanced_prompt}{target_line}\n\n{IMAGE_STYLE_LOCK_PROMPT}"

    def _fit_font(
        self,
        text: str,
        width: int,
        height: int,
        source_image: Image.Image,
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        font_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        estimated_text_height = self._estimated_ink_height(source_image)
        max_size = max(12, int(min(height * 0.58, estimated_text_height * 1.18)))
        min_size = 10
        for size in range(max_size, min_size - 1, -2):
            font = self._load_font(font_paths, size)
            box = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), text, font=font)
            font_height = box[3] - box[1]
            if (
                box[2] - box[0] <= width * 0.88
                and font_height <= height * 0.8
                and font_height <= estimated_text_height * 1.2
            ):
                return font
        return self._load_font(font_paths, min_size)

    def _load_font(self, font_paths: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for path in font_paths:
            if Path(path).exists():
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _paper_color(self, image: Image.Image) -> tuple[int, int, int]:
        thumb = image.resize((1, 1))
        mean = ImageStat.Stat(thumb).mean
        return tuple(int(max(210, min(255, value))) for value in mean)

    def _ink_color(self, image: Image.Image) -> tuple[int, int, int]:
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        threshold = max(35, min(210, int(stat.mean[0] - max(18, stat.stddev[0] * 0.45))))
        pixels = [
            pixel
            for pixel, gray_value in zip(image.getdata(), gray.getdata(), strict=False)
            if gray_value <= threshold
        ]
        if not pixels:
            return (35, 38, 42)
        channels = list(zip(*pixels[:4000], strict=False))
        return tuple(int(sum(channel) / len(channel)) for channel in channels[:3])

    def _estimated_ink_height(self, image: Image.Image) -> int:
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        threshold = max(35, min(210, int(stat.mean[0] - max(18, stat.stddev[0] * 0.45))))
        rows = [
            y
            for y in range(gray.height)
            if sum(1 for x in range(gray.width) if gray.getpixel((x, y)) <= threshold)
            >= max(2, int(gray.width * 0.01))
        ]
        if not rows:
            return max(10, int(image.height * 0.42))
        return max(10, min(image.height, max(rows) - min(rows) + 1))


image_edit_service = ImageEditService()
