# happy_pdf

happy_pdf 是一个面向扫描件 PDF 的局部智能编辑工具。它会把 PDF 页面渲染成高清图片，用户在网页中框选需要修改的局部区域并输入简短指令，例如“日期改成 2026.12.11”，系统会自动完成指令增强、局部图像编辑、整页回贴预览，并导出新的 PDF。

下面的命令默认在当前 `happy_pdf/` 目录执行；如果你在外层仓库根目录，请先执行 `cd happy_pdf`。

## 使用 Codex 安装

如果你已经安装了 Codex，可以直接把下面这段提示词复制给 Codex，让它自动完成安装、依赖配置、启动和验证。

```text
请帮我把 happy_pdf 安装到我的电脑并启动到可访问状态。

GitHub 仓库地址：
https://github.com/shaopengDaJiDaLi/happy_pdf_v2

安装目录：
~/apps/happy_pdf

要求：
1. 克隆或更新这个 GitHub 仓库。
2. 进入项目目录。如果仓库根目录下面有 happy_pdf 子目录，就进入 happy_pdf；如果当前仓库根目录本身就是项目目录，就留在当前目录。
3. 如果没有 .env，就从 .env.example 复制一份；不要覆盖已有 .env。
4. 优先使用 Docker 安装和启动：
   docker compose up --build
5. 如果 Docker 不可用，则使用本地安装方式：
   - 创建 Python 虚拟环境
   - 安装 backend/requirements.txt
   - 安装 frontend/package.json 里的 npm 依赖
   - 构建前端
   - 使用 ./start.sh 启动服务
6. 启动后检查 http://localhost:8000/api/health 是否正常。
7. 最后告诉我：
   - 安装目录
   - 启动命令
   - 访问地址
   - API 文档地址
   - 如何停止服务

注意：
- 不要删除我电脑上的其他文件。
- 不要覆盖已有 .env。
- 不要提交或泄露 .env。
- 不要写入真实 API Key，除非我明确提供。
```

更完整的 Codex 安装说明见 [CODEX_INSTALL.md](./CODEX_INSTALL.md)。

## 功能特性

- 上传扫描版 PDF，并按页预览。
- 支持翻页、缩放和鼠标拖拽框选局部区域。
- 自动把前端显示坐标映射为后端高清页面图像坐标。
- 可选 OCR 识别选区文本，为修改指令提供上下文。
- 使用 TEXT API 将短指令扩写成更稳定的图像编辑提示词。
- 使用 IMAGE API 对选区图片进行局部编辑。
- 展示原始选区、编辑后选区、回贴整页预览和执行日志。
- 用户确认后将修改应用到当前 PDF 页面。
- 支持导出并下载 `edited.pdf`。
- 未配置模型 API Key 时支持本地 fallback，方便验证上传、框选、回贴和导出链路。

## 技术栈

前端：

- React 18
- TypeScript
- Vite
- Zustand
- pdfjs-dist
- lucide-react

后端：

- Python 3.10+
- FastAPI
- Uvicorn
- PyMuPDF
- Pillow
- pytesseract
- OpenAI Python SDK

系统依赖：

- Node.js 20+ 和 npm
- Tesseract OCR，可选；Docker 镜像中会自动安装
- Docker 和 Docker Compose，可选但推荐

## 目录结构

```text
happy_pdf/
  frontend/                 # React 前端
    src/
    package.json
    vite.config.ts
  backend/                  # FastAPI 后端
    app/
      api/
      schemas/
      services/
      utils/
      main.py
    requirements.txt
    data/                   # 运行时生成文件，不建议提交
  .env.example
  Dockerfile
  docker-compose.yml
  start.sh
```

## 快速启动：Docker

推荐用 Docker 启动，前端构建、后端依赖和 OCR 系统依赖都会在镜像中处理。

```bash
cp .env.example .env
docker compose up --build
```

启动后访问：

```text
http://localhost:8000
```

API 文档：

```text
http://localhost:8000/docs
```

## 本地启动

### 1. 配置环境变量

```bash
cp .env.example .env
```

如果只是本地验证流程，可以先关闭模型调用：

```bash
OPENAI_DISABLE=1
```

如果要使用真实模型能力，需要在 `.env` 中配置：

```bash
TEXT_OPENAI_API_KEY=sk-...
IMAGE_OPENAI_API_KEY=sk-...
```

### 2. 安装后端依赖

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

后端依赖来自 `backend/requirements.txt`，主要包括：

```text
fastapi
uvicorn[standard]
python-multipart
python-dotenv
pydantic
PyMuPDF
Pillow
openai
httpx[socks]
pytesseract
```

如果需要 OCR，在 Ubuntu/Debian 上安装：

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim fonts-noto-cjk
```

macOS 可以使用：

```bash
brew install tesseract
```

### 3. 安装前端依赖

```bash
cd ../frontend
npm install
```

前端依赖来自 `frontend/package.json`，主要包括：

```text
react
react-dom
vite
typescript
zustand
pdfjs-dist
lucide-react
```

### 4. 一键启动

项目提供了启动脚本，会在缺少前端构建产物时自动执行 `npm install` 和 `npm run build`，然后由 FastAPI 托管前端静态文件。

```bash
cd ..
chmod +x start.sh
./start.sh
```

默认访问：

```text
http://127.0.0.1:8000
```

指定端口：

```bash
PORT=8010 ./start.sh
```

### 5. 开发模式启动

如果需要前后端分开开发，开两个终端。

终端 1：后端

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

终端 2：前端

```bash
cd frontend
npm run dev
```

访问：

```text
http://localhost:5173
```

Vite 已配置代理，开发环境下 `/api` 和 `/data` 会转发到 `http://127.0.0.1:8000`。

## 使用方法

1. 打开网页，点击“上传 PDF”，选择扫描版 PDF。
2. 等待第一页渲染完成，可使用翻页和缩放按钮定位页面。
3. 在页面图片上拖拽框选需要修改的区域。
4. 在右侧输入修改指令，例如：

```text
日期改成 2026.12.11
把 300 改成 150
把姓名改成 张三
```

5. 点击“生成修改”，等待任务完成。
6. 查看原始选区、编辑后选区和回贴整页预览。
7. 结果满意后点击“应用到 PDF”。
8. 点击“导出 PDF”，下载 `edited.pdf`。

## 环境变量

`.env.example` 已包含完整模板。常用配置如下：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `HAPPY_PDF_DATA_DIR` | `backend/data` | 运行时文件目录，包括上传、渲染、裁剪、编辑结果和日志 |
| `PDF_RENDER_SCALE` | `3` | PDF 页面渲染倍率，越高越清晰，占用也越大 |
| `OCR_ENGINE` | `auto` | OCR 引擎，`auto` 会优先尝试可用 OCR |
| `OCR_LANG` | `chi_sim+eng` | OCR 语言 |
| `TEXT_OPENAI_API_KEY` | 空 | 文本理解和指令增强 API Key |
| `TEXT_OPENAI_BASE_URL` | `https://api.openai.com/v1` | 文本模型 API 地址 |
| `TEXT_OPENAI_MODEL` | `gpt-5.5` | 文本指令增强模型 |
| `TEXT_OPENAI_DISABLE` | `0` | 设为 `1` 时关闭文本模型调用 |
| `TEXT_FALLBACK_ON_ERROR` | `0` | 文本模型失败后是否使用本地 fallback |
| `IMAGE_OPENAI_API_KEY` | 空 | 局部图像编辑 API Key |
| `IMAGE_OPENAI_BASE_URL` | `https://api.openai.com/v1` | 图像模型 API 地址 |
| `IMAGE_OPENAI_MODEL` | `gpt-image-2` | 局部图像编辑模型 |
| `IMAGE_OPENAI_DISABLE` | `0` | 设为 `1` 时关闭图像模型调用 |
| `IMAGE_FALLBACK_ON_ERROR` | `0` | 图像模型失败后是否使用本地 fallback |
| `OPENAI_DISABLE` | `0` | 设为 `1` 时同时关闭文本和图像模型调用 |
| `VITE_API_BASE_URL` | 空 | 前端请求 API 的基础地址，默认同源 |

如果需要代理，可以配置：

```bash
TEXT_HTTP_PROXY=
TEXT_HTTPS_PROXY=
TEXT_ALL_PROXY=
IMAGE_HTTP_PROXY=
IMAGE_HTTPS_PROXY=
IMAGE_ALL_PROXY=
```

## API 接口

后端接口统一以 `/api` 开头：

- `GET /api/health`：健康检查。
- `POST /api/upload`：上传 PDF。
- `GET /api/document/{document_id}/page/{page_number}`：获取页面图片。
- `POST /api/edit/start`：开始局部编辑任务。
- `GET /api/edit/job/{job_id}`：查询任务状态。
- `GET /api/edit/job/{job_id}/stream`：SSE 实时任务日志。
- `POST /api/edit/apply`：确认并应用编辑结果。
- `POST /api/document/{document_id}/export?job_id={job_id}`：导出 PDF。

## 运行时数据

运行过程中会在 `backend/data/` 下生成文件：

```text
uploads/     # 上传的原始 PDF
documents/   # 文档元数据和当前页面状态
renders/     # 页面渲染图
crops/       # 选区裁剪图
edits/       # 编辑结果和整页预览
outputs/     # 导出的 edited.pdf
logs/        # 任务日志
```

这些文件是本地运行产物，通常不需要提交到 GitHub。

## 上传 GitHub 前建议

- 不要提交 `.env`，只提交 `.env.example`。
- 不要提交 `backend/data/` 下的运行产物。
- 不要提交 `frontend/node_modules/`。
- `frontend/dist/` 是构建产物，是否提交取决于部署方式；使用 Docker 或本地构建时可以不提交。
- 如果仓库还没有 `.gitignore`，建议把 `.env`、`node_modules/`、`backend/data/`、`__pycache__/` 等加入忽略列表。

## 常见问题

### 没有配置 API Key 能不能运行？

可以。设置 `OPENAI_DISABLE=1` 后会使用本地 fallback，适合验证上传、框选、日志、回贴和导出流程。但真实图像修改效果需要配置 `TEXT_OPENAI_API_KEY` 和 `IMAGE_OPENAI_API_KEY`。

### OCR 失败会不会导致任务失败？

通常不会。OCR 只是辅助上下文，识别失败时任务仍会继续执行。

### 导出的 PDF 是否保留原 PDF 文本层？

不会。当前实现适合扫描件场景，导出时会把页面作为整页图片写回 PDF。

### 端口被占用怎么办？

使用启动脚本时会自动寻找可用端口，也可以手动指定：

```bash
PORT=8010 ./start.sh
```

## 许可证

当前项目尚未指定开源许可证。如果准备公开发布，请根据需要补充 `LICENSE` 文件。
