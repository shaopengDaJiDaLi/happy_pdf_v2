from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from app.api.routes import router
from app.utils.config import ensure_data_dirs, settings

load_dotenv()
ensure_data_dirs()

app = FastAPI(
    title="happy_pdf",
    description="扫描件 PDF 局部智能编辑工具",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/data", StaticFiles(directory=settings.DATA_DIR), name="data")


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "message": message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": True, "message": "请求参数无效", "details": exc.errors()},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if settings.FRONTEND_DIST_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=settings.FRONTEND_DIST_DIR, html=True),
        name="frontend",
    )
