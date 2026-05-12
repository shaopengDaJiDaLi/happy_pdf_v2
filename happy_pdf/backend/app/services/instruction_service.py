import json
import re
from dataclasses import dataclass
from typing import Any

from app.utils.config import settings


EDIT_SPEC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "task_type": {
            "type": "string",
            "description": "Short task category, for example replace_text, replace_date, replace_number.",
        },
        "target_text": {
            "type": "string",
            "description": "The text likely being replaced. Empty when unknown.",
        },
        "replacement_text": {
            "type": "string",
            "description": "The new text that should appear in the edited crop.",
        },
        "keep_text": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Visible text that should be preserved when known.",
        },
        "preserve_requirements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Visual properties that must remain consistent.",
        },
        "enhanced_edit_prompt": {
            "type": "string",
            "description": "Prompt to send to the image editing model.",
        },
    },
    "required": [
        "task_type",
        "target_text",
        "replacement_text",
        "keep_text",
        "preserve_requirements",
        "enhanced_edit_prompt",
    ],
    "additionalProperties": False,
}


STYLE_LOCK_REQUIREMENTS = [
    "替换后的新内容必须复用原目标文本的字体或手写笔迹、字号、字符高度、字符宽度、字距、基线、倾斜角度、颜色、灰度、透明度、笔画粗细、边缘模糊和抗锯齿效果",
    "新内容必须放在原目标文本所在的同一文字框内，视觉高度、宽度、颜色深浅和笔画粗细不得变大、变小、变粗、变细、变浅或变深",
    "如果无法精确识别字体名称，必须以选区内被替换目标文本的可见外观作为唯一样式参考，不使用默认字体、艺术字或更清晰的新字体",
]

STYLE_LOCK_PROMPT = (
    "\n\n样式锁定要求（最高优先级）："
    "替换后的新内容必须严格复刻原目标文本的视觉风格，包括字体或手写笔迹、字号、"
    "字符高度、字符宽度、字距、基线、倾斜角度、颜色、灰度、透明度、笔画粗细、"
    "边缘模糊、抗锯齿、扫描噪声和压缩痕迹。新内容必须落在原目标文本的同一位置和"
    "同一文字框内，不能变大、变小、变粗、变细、变浅、变深、变清晰或移动。"
    "不要使用默认字体，不要重新排版，不要美化文字，不要提高文字清晰度。"
    "如果原图中文字略模糊、偏灰、偏斜或带扫描噪声，新文字也必须保持相同效果。"
)


@dataclass
class InstructionResult:
    edit_spec: dict[str, Any]
    enhanced_edit_prompt: str
    mode: str


class InstructionService:
    def enhance(self, user_instruction: str, ocr_text: str) -> InstructionResult:
        if settings.TEXT_OPENAI_DISABLE or not settings.TEXT_OPENAI_API_KEY:
            return self._heuristic_enhance(user_instruction, ocr_text, "local_fallback")

        try:
            import httpx
            from openai import OpenAI

            http_client = None
            if settings.TEXT_PROXY_URL:
                http_client = httpx.Client(
                    proxy=settings.TEXT_PROXY_URL,
                    timeout=settings.TEXT_TIMEOUT_SECONDS,
                )
            client = OpenAI(
                api_key=settings.TEXT_OPENAI_API_KEY,
                base_url=settings.TEXT_OPENAI_BASE_URL,
                http_client=http_client,
                timeout=settings.TEXT_TIMEOUT_SECONDS,
                max_retries=settings.TEXT_MAX_RETRIES,
            )
            response = client.responses.create(
                model=settings.TEXT_OPENAI_MODEL,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You convert short Chinese PDF scan edit instructions into "
                            "strict local image editing tasks. Return JSON only. The crop is "
                            "a scanned document fragment, not editable PDF text."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "用户原始指令：\n"
                            f"{user_instruction}\n\n"
                            "选区 OCR 文本（可能为空或不准确）：\n"
                            f"{ocr_text or '(empty)'}\n\n"
                            "任务上下文：扫描件 PDF 的局部裁剪图像。请生成 edit_spec 和 image edit prompt。"
                            "必须自动补全：只修改目标内容；保留其他内容、表格线、纸张纹理、扫描噪声、"
                            "模糊程度、亮度、位置、字号、字距、基线、笔迹/字体风格、颜色和粗细；不要重绘整张图；"
                            "替换后的新内容必须以原目标文本为唯一样式参考，严格保持字体大小、颜色、"
                            "笔画粗细、字符高度、字符宽度和边缘模糊一致，不能使用默认字体或更清晰的新字体；"
                            "输出必须与输入裁剪图像同尺寸。"
                        ),
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "happy_pdf_edit_spec",
                        "schema": EDIT_SPEC_SCHEMA,
                        "strict": True,
                    }
                },
            )
            raw = response.output_text
            spec = json.loads(raw)
            spec = self._apply_style_lock(spec)
            return InstructionResult(
                edit_spec=spec,
                enhanced_edit_prompt=spec["enhanced_edit_prompt"],
                mode=f"text_api:{settings.TEXT_OPENAI_MODEL}",
            )
        except Exception as exc:
            if settings.TEXT_FALLBACK_ON_ERROR:
                return self._heuristic_enhance(
                    user_instruction,
                    ocr_text,
                    f"text_api_failed_fallback:{exc}",
                )
            raise RuntimeError(f"TEXT API 指令增强失败：{exc}") from exc

    def _heuristic_enhance(
        self, user_instruction: str, ocr_text: str, mode: str
    ) -> InstructionResult:
        target_text = ""
        replacement_text = ""
        task_type = "replace_text"

        match = re.search(r"把\s*(.+?)\s*改成\s*(.+)", user_instruction)
        if match:
            target_text = match.group(1).strip()
            replacement_text = match.group(2).strip()
            if re.fullmatch(r"[\d.]+", replacement_text):
                task_type = "replace_number"
        else:
            match = re.search(r"(.+?)改成\s*(.+)", user_instruction)
            if match:
                possible_target = match.group(1).strip()
                replacement_text = match.group(2).strip()
                if "日期" in possible_target:
                    task_type = "replace_date"
                    target_text = "日期字段"
                else:
                    target_text = possible_target

        if not replacement_text:
            replacement_text = user_instruction.strip()

        keep_text: list[str] = []
        if "日期" in user_instruction or "日期" in ocr_text:
            keep_text.append("日期：")

        preserve_requirements = [
            "只修改选中裁剪图像中的目标文字或数字",
            "保留其他文字、线条、印章、签字、背景和边缘不变",
            "保留纸张纹理、扫描噪声、压缩痕迹、模糊程度、亮度和色偏",
            "新内容严格匹配原字体或手写风格、字号、字符高度、字符宽度、字距、颜色、灰度、透明度、笔画粗细、倾斜角度、基线和位置",
            "新内容不得变大、变小、变粗、变细、变浅、变深、变清晰或移动",
            "不要扩展画布，不要改变裁剪范围，输出必须与输入同尺寸",
        ]
        prompt = (
            "请对这张扫描件 PDF 的局部裁剪图像做局部编辑。"
            f"用户的短指令是：{user_instruction}。"
            f"OCR 辅助文本是：{ocr_text or '无可靠 OCR 文本'}。"
            f"请将目标内容{('“' + target_text + '”') if target_text else ''}替换为“{replacement_text}”。"
            "只修改必要的目标内容；如果存在标签、表格线或其他文字，请保持不变。"
            "保留原图纸张纹理、扫描噪声、压缩痕迹、边缘阴影、模糊程度、亮度和色偏。"
            "新内容必须严格匹配原字体或手写笔迹风格、字号、字符高度、字符宽度、字距、颜色、灰度、透明度、笔画粗细、倾斜程度、基线和位置。"
            "新内容不能变大、变小、变粗、变细、变浅、变深、变清晰或移动。"
            "不要重新生成整张图，不要改变画布大小、比例或裁剪范围。"
            "输出与输入裁剪区域同尺寸的编辑后图像。"
        )
        spec = {
            "task_type": task_type,
            "target_text": target_text,
            "replacement_text": replacement_text,
            "keep_text": keep_text,
            "preserve_requirements": preserve_requirements,
            "enhanced_edit_prompt": prompt,
        }
        spec = self._apply_style_lock(spec)
        return InstructionResult(
            edit_spec=spec,
            enhanced_edit_prompt=spec["enhanced_edit_prompt"],
            mode=mode,
        )

    def _apply_style_lock(self, spec: dict[str, Any]) -> dict[str, Any]:
        requirements = spec.get("preserve_requirements")
        if not isinstance(requirements, list):
            requirements = []
        for requirement in STYLE_LOCK_REQUIREMENTS:
            if requirement not in requirements:
                requirements.append(requirement)
        prompt = str(spec.get("enhanced_edit_prompt") or "")
        if "样式锁定要求" not in prompt:
            prompt = f"{prompt}{STYLE_LOCK_PROMPT}"
        spec["preserve_requirements"] = requirements
        spec["enhanced_edit_prompt"] = prompt
        return spec


instruction_service = InstructionService()
