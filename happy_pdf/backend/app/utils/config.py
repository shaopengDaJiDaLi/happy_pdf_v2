import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_PROJECT_DIR = _BACKEND_DIR.parent

load_dotenv(_PROJECT_DIR / ".env")
load_dotenv(_BACKEND_DIR / ".env", override=True)


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def _env_optional(name: str) -> str | None:
    value = os.getenv(name)
    return value or None


def _project_path(project_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project_dir / path
    return path.resolve()


class Settings:
    BACKEND_DIR = _BACKEND_DIR
    PROJECT_DIR = _PROJECT_DIR
    DATA_DIR = _project_path(
        PROJECT_DIR,
        os.getenv("HAPPY_PDF_DATA_DIR", BACKEND_DIR / "data"),
    )
    FRONTEND_DIST_DIR = _project_path(
        PROJECT_DIR,
        os.getenv("HAPPY_PDF_FRONTEND_DIST", PROJECT_DIR / "frontend" / "dist"),
    )

    UPLOAD_DIR = DATA_DIR / "uploads"
    DOCUMENT_DIR = DATA_DIR / "documents"
    RENDER_DIR = DATA_DIR / "renders"
    CROP_DIR = DATA_DIR / "crops"
    EDIT_DIR = DATA_DIR / "edits"
    OUTPUT_DIR = DATA_DIR / "outputs"
    LOG_DIR = DATA_DIR / "logs"

    RENDER_SCALE = float(os.getenv("PDF_RENDER_SCALE", os.getenv("RENDER_SCALE", "3")))

    # Legacy OPENAI_* values are kept as a compatibility fallback, but the
    # application services use the TEXT_* and IMAGE_* settings independently.
    LEGACY_OPENAI_API_KEY = _env_optional("OPENAI_API_KEY")
    LEGACY_OPENAI_BASE_URL = _env_optional("OPENAI_BASE_URL")
    OPENAI_DISABLE = _env_bool("OPENAI_DISABLE")

    TEXT_OPENAI_API_KEY = _env_optional("TEXT_OPENAI_API_KEY") or LEGACY_OPENAI_API_KEY
    TEXT_OPENAI_BASE_URL = _env_optional("TEXT_OPENAI_BASE_URL") or LEGACY_OPENAI_BASE_URL
    TEXT_OPENAI_MODEL = os.getenv(
        "TEXT_OPENAI_MODEL", os.getenv("OPENAI_TEXT_MODEL", "gpt-5.5")
    )
    TEXT_HTTP_PROXY = _env_optional("TEXT_HTTP_PROXY")
    TEXT_HTTPS_PROXY = _env_optional("TEXT_HTTPS_PROXY")
    TEXT_ALL_PROXY = _env_optional("TEXT_ALL_PROXY")
    TEXT_PROXY_URL = TEXT_ALL_PROXY or TEXT_HTTPS_PROXY or TEXT_HTTP_PROXY
    TEXT_OPENAI_DISABLE = OPENAI_DISABLE or _env_bool("TEXT_OPENAI_DISABLE")
    TEXT_FALLBACK_ON_ERROR = _env_bool("TEXT_FALLBACK_ON_ERROR")
    TEXT_TIMEOUT_SECONDS = float(os.getenv("TEXT_TIMEOUT_SECONDS", "120"))
    TEXT_MAX_RETRIES = int(os.getenv("TEXT_MAX_RETRIES", "1"))

    IMAGE_OPENAI_API_KEY = _env_optional("IMAGE_OPENAI_API_KEY") or LEGACY_OPENAI_API_KEY
    IMAGE_OPENAI_BASE_URL = _env_optional("IMAGE_OPENAI_BASE_URL") or LEGACY_OPENAI_BASE_URL
    IMAGE_OPENAI_MODEL = os.getenv(
        "IMAGE_OPENAI_MODEL", os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    )
    IMAGE_HTTP_PROXY = _env_optional("IMAGE_HTTP_PROXY")
    IMAGE_HTTPS_PROXY = _env_optional("IMAGE_HTTPS_PROXY")
    IMAGE_ALL_PROXY = _env_optional("IMAGE_ALL_PROXY")
    IMAGE_PROXY_URL = IMAGE_ALL_PROXY or IMAGE_HTTPS_PROXY or IMAGE_HTTP_PROXY
    IMAGE_OPENAI_DISABLE = (
        OPENAI_DISABLE
        or _env_bool("IMAGE_OPENAI_DISABLE")
        or _env_bool("OPENAI_IMAGE_DISABLE")
    )
    IMAGE_FALLBACK_ON_ERROR = _env_bool("IMAGE_FALLBACK_ON_ERROR")
    IMAGE_TIMEOUT_SECONDS = float(os.getenv("IMAGE_TIMEOUT_SECONDS", "120"))
    IMAGE_MAX_RETRIES = int(os.getenv("IMAGE_MAX_RETRIES", "0"))

    OCR_ENGINE = os.getenv("OCR_ENGINE", "auto").lower()
    OCR_LANG = os.getenv("OCR_LANG", "chi_sim+eng")


settings = Settings()


def ensure_data_dirs() -> None:
    for path in [
        settings.UPLOAD_DIR,
        settings.DOCUMENT_DIR,
        settings.RENDER_DIR,
        settings.CROP_DIR,
        settings.EDIT_DIR,
        settings.OUTPUT_DIR,
        settings.LOG_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def data_url(path: str | Path) -> str:
    file_path = Path(path).resolve()
    rel = file_path.relative_to(settings.DATA_DIR).as_posix()
    version = int(file_path.stat().st_mtime) if file_path.exists() else 0
    return f"/data/{rel}?v={version}"
