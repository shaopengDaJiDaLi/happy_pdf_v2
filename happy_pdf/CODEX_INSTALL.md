# 使用 Codex 安装 happy_pdf

这份说明面向已经安装 Codex 的用户。用户只需要把下面的提示词复制给 Codex，并把 GitHub 仓库地址改成当前仓库地址，Codex 就可以按步骤完成安装、启动和验证。

## 推荐提示词

```text
请帮我把 happy_pdf 安装到我的电脑并启动到可访问状态。

GitHub 仓库地址：
https://github.com/shaopengDaJiDaLi/happy_pdf_v2

安装目录：
~/apps/happy_pdf

安装策略：
1. 首要步骤是先购买/开通并配置 .env 里的模型 API，然后再安装和启动。
2. 真实编辑必须同时配置两类模型 API：
   - TEXT API 使用 gpt-5.5。
   - IMAGE API 使用 gpt-image-2。
   - 如果同一个 API Key 同时支持 gpt-5.5 和 gpt-image-2，就把 TEXT_OPENAI_API_KEY 和 IMAGE_OPENAI_API_KEY 填成同一个 Key。
   - 如果购买的 gpt-5.5 API 不支持 gpt-image-2，就必须单独购买或开通 gpt-image-2 API，并把它填到 IMAGE_OPENAI_API_KEY。
   - 如果两个 API 来自不同供应商或不同网关，要分别配置 TEXT_OPENAI_BASE_URL 和 IMAGE_OPENAI_BASE_URL。
3. 如果我没有提供真实 Key，只复制 .env.example 为 .env，并提醒我填写；不要编造 Key。
4. 然后检查系统环境：git、Python3、pip、Node.js、npm。Docker 不是必须项。
5. 默认使用本地 Python + npm 方式安装，不要优先使用 Docker。
6. Ubuntu 使用项目已有的 start.sh；macOS 和 Windows 使用跨平台补丁脚本。
7. 安装过程中不要删除我电脑上的其他文件。
8. 不要覆盖已有 .env。
9. 不要写入真实 API Key，除非我明确提供。

具体步骤：
1. 如果安装目录不存在，请创建父目录并克隆仓库。
2. 如果安装目录已经存在并且是这个仓库，请拉取或提示我是否更新。
3. 进入项目目录：
   - 如果仓库根目录下面有 happy_pdf 子目录，就进入 happy_pdf。
   - 如果仓库根目录本身就是项目目录，就留在当前目录。
4. 如果没有 .env，就复制 .env.example 为 .env。
5. 在启动前检查 .env 是否包含下面的真实模型配置：
   - TEXT_OPENAI_API_KEY、TEXT_OPENAI_BASE_URL、TEXT_OPENAI_MODEL=gpt-5.5。
   - IMAGE_OPENAI_API_KEY、IMAGE_OPENAI_BASE_URL、IMAGE_OPENAI_MODEL=gpt-image-2。
   - 如果 TEXT 和 IMAGE 使用同一个 API Key，要明确告诉我。
   - 如果 IMAGE_OPENAI_API_KEY 为空，要提醒我：有些 gpt-5.5 API 不支持 gpt-image-2，需要单独购买或开通 gpt-image-2 API。
6. 按当前系统选择本地安装和启动：
   - Ubuntu/Linux：
     1. 进入 backend，创建 Python 虚拟环境 .venv。
     2. 安装 backend/requirements.txt。
     3. 进入 frontend，执行 npm install 和 npm run build。
     4. 回到项目目录，执行 ./start.sh。
   - macOS：
     1. 确认已安装 Python 3.10+ 和 Node.js 20+。
     2. 执行 python3 scripts/setup_local.py。
     3. 执行 python3 scripts/start_local.py。
   - Windows：
     1. 确认已安装 Python 3.10+ 和 Node.js 20+。
     2. 在 PowerShell 执行 .\setup.ps1。
     3. 在 PowerShell 执行 .\start.ps1。
7. 不要强制安装 Docker。只有我明确要求 Docker 时，才使用 docker compose up --build。
8. 启动后检查：
   - http://localhost:8000/api/health
   - http://localhost:8000/docs
9. 如果 8000 端口被占用，请使用可用端口，并告诉我最终端口。

安装完成后请输出：
1. 安装目录。
2. 使用的是哪个系统的本地启动方式。
3. 启动命令。
4. 访问地址。
5. API 文档地址。
6. 停止服务的方法。
7. 重新启动服务的方法。
```

## 本项目依赖

默认本地安装，不强制使用 Docker。需要本机具备：

- Python 3.10+
- Node.js 20+
- npm
- git
- 可选：Tesseract OCR

Ubuntu 使用现有 `start.sh`；macOS 可使用 `python3 scripts/setup_local.py` 和 `python3 scripts/start_local.py`；Windows 可使用 `setup.ps1` 和 `start.ps1`。Docker 只作为可选部署方式保留。

## API Key 配置

项目可以在没有 API Key 的情况下启动，但真实图像编辑效果必须同时配置 `gpt-5.5` 和 `gpt-image-2` 的模型 API Key。

本地验证流程可以在 `.env` 中设置：

```bash
OPENAI_DISABLE=1
```

使用真实模型时，先确认你的 API 是否同时支持 `gpt-5.5` 和 `gpt-image-2`：

- `gpt-5.5` 用于 TEXT API，负责理解用户短指令并生成稳定的图像编辑提示词。
- `gpt-image-2` 用于 IMAGE API，负责真正编辑框选出来的局部图片。
- 有些购买的 `gpt-5.5` API 不支持 `gpt-image-2`，这种情况下需要单独购买或开通 `gpt-image-2` API。
- 如果同一个 API Key 已经支持两个模型，就不需要单独购买图像 API，TEXT 和 IMAGE 填同一个 Key。

同一个 API Key 同时支持两个模型时，`.env` 示例：

```bash
TEXT_OPENAI_API_KEY=sk-your-one-api-key
TEXT_OPENAI_BASE_URL=https://api.openai.com/v1
TEXT_OPENAI_MODEL=gpt-5.5

IMAGE_OPENAI_API_KEY=sk-your-one-api-key
IMAGE_OPENAI_BASE_URL=https://api.openai.com/v1
IMAGE_OPENAI_MODEL=gpt-image-2
```

`gpt-5.5` API 不支持 `gpt-image-2`，需要单独图像 API 时，`.env` 示例：

```bash
TEXT_OPENAI_API_KEY=sk-your-gpt55-api-key
TEXT_OPENAI_BASE_URL=https://api.openai.com/v1
TEXT_OPENAI_MODEL=gpt-5.5

IMAGE_OPENAI_API_KEY=sk-your-gpt-image-2-api-key
IMAGE_OPENAI_BASE_URL=https://api.openai.com/v1
IMAGE_OPENAI_MODEL=gpt-image-2
```

如果两个 API 来自不同供应商或不同网关，把各自提供的地址分别填到 `TEXT_OPENAI_BASE_URL` 和 `IMAGE_OPENAI_BASE_URL`。

不要把 `.env` 提交到 GitHub。
