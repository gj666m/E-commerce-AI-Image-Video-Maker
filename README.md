# AI 电商图像视频生成工具

> 自建内部 AI 做图/做视频工具，为跨境电商运营团队提供商品图与视频的 AI 生成能力。覆盖文生图、图生图、多图参考、视频生成、对话式 Agent、爆品复刻、分镜视频等全链路场景。

[English summary](#english-summary) · [功能特性](#功能特性) · [快速开始](#快速开始) · [文档](#学习资料) · [协议](#license)

---

## English summary

An internal, self-hosted AI image & video generation platform built for cross-border e-commerce operations. It integrates multiple image generation models (Seedream 4.5/5.0, GPT-Image-2, Nano Banana 2, etc.) and the Seedance video model behind a unified FastAPI backend, plus a LangGraph + Claude conversational Agent that can orchestrate tool calls to generate and quality-check images end-to-end. Supports multi-user isolation, asset library + ROI tracking, viral video replication, TikTok script extraction, storyboard video planning and more.

Tech stack: **FastAPI (Python 3.10+) · Vue 3 + Element Plus + TypeScript · SQLite · LangGraph**. MIT licensed.

---

## 功能特性

### 🎨 图片生成
- **多模型路由**：Seedream 4.5/5.0、GPT-Image-2 (All/VIP)、Nano Banana 2、OpenAI、fal、Mock，支持自动 fallback
- **快速生图**：参考图(0-6 张) + 描述 + 模型 + 比例 → 出图，prompt 透传不走模板
- **一键穿搭**：商品图 + 模特图 → 试穿展示，支持多张并行
- **模特生成**：文生图 / 多图参考两种模式，1-3 张参考图融合
- **种草图**：博主人设（标签 + 照片驱动）+ AI 策划方案 + 按方案批量生成
- **商品主图 / A+ 图**：白底主图、A+ 图文混排、AI 策划（英文 headline/body）
- **生成比例**：1:1 / 3:4 / 4:3 / 4:5 / 9:16 / 16:9
- **Pillow 后处理**：自动轻微颗粒 + 色调调整，提升真实感，零依赖

### 🎬 视频生成
- **Seedance 三通道**：官方 Seedance 2.0 / API易 中转（不限并发）/ Seedance Mini（半价）
- **双模式**：电商模式（商品图 + 模特图 + 描述）/ 自由创作模式
- **自定义时长**：4-15 秒滑块或自动（-1），支持 480p/720p/1080p
- **防重复扣费**：POST 不自动重试 + 取消按钮 + 360s 超时
- **prompt 智能扩写**：Gemini 3.5 Flash 中文输出 + 画面动态感规则
- **分镜视频**：AI 三段式叙事规划（Hook→Detail→Recall）+ 分镜可编辑 + 拼装提交
- **穿搭素材抓取**：TikTok/IG/YT/抖音链接或上传视频 → ffmpeg 抽关键帧 → 勾选送视频生成

### 🤖 对话式 AI Agent
- **LangGraph + Claude Sonnet 4.6**：自然语言调度图片生成能力
- **Gemini Flash 质检循环**：3 次重试 + 结构化评分
- **@ 引用语法**：在 prompt 里 `@图片N` 引用已上传/生成的图
- **多轮持久化**：AsyncSqliteSaver checkpoint，刷新页面恢复对话
- **SSE 流式响应**：实时返回思考 / 工具调用 / 质检状态

### 📦 资产与数据
- **素材资产库**：已生成图/视频沉淀池，按店铺/URL 标记应用场景
- **数据追踪**：三表模型（asset_library → asset_applications → asset_tracking_records），记录播放/点击/转化/GMV + 自定义指标，反推素材 ROI
- **历史记录**：图片 + 视频分层保留（文件 3 天 / 元数据 90 天），软删 + admin 硬删
- **Prompt 库**：保存常用 prompt，工坊双向恢复 8 要素

### 🧠 智能辅助
- **Prompt 工坊**：结构化 8 要素（主体/服装/场景/光影/镜头/节奏/风格/构图）AI 生成专业 prompt
- **AI 商品分析**：豆包视觉模型，结构化 JSON（类型/款式/颜色/卖点/场景）
- **爆品复刻**：3 步 AI 链路（骨架提取 → 商品理解 → 裂变 3 份变体 prompt）
- **TikTok 脚本提取**：yt-dlp 下载 + Gemini 转写 SRT 字幕
- **视频反推**：Gemini 视频理解，3 风格（Sora 结构化 / Seedance 散文 / 影视散文）
- **余额展示**：API易 账户余额 header 全员可见，颜色分级

### 🔐 平台能力
- **多用户支持**：SQLite + JWT 鉴权，admin/user 角色权限隔离，按 user_id 隔离数据
- **静态文件鉴权**：`/api/file/{kind}/{path}` 鉴权 endpoint + admin 旁路 + 路径穿越防护 + 越权统一返 404
- **Docker 友好**：无外部依赖（SQLite 内置，文件存本地磁盘）

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI (Python 3.10+) · async/await + httpx · Pydantic v2 |
| 前端 | Vue 3 · Element Plus · TypeScript · Vite · Pinia |
| 数据库 | SQLite (WAL 模式) |
| AI 编排 | LangGraph · langchain-anthropic · AsyncSqliteSaver |
| 图片模型 | Seedream 4.5/5.0 · GPT-Image-2 All/VIP · Nano Banana 2 · OpenAI · fal |
| 视频模型 | Seedance 2.0（官方 / API易中转 / Mini）|
| 文本/视觉分析 | 豆包 Seed-2.0-Lite（Responses API）· Gemini 3.5 Flash |
| 媒体处理 | Pillow · ffmpeg · yt-dlp · mediapipe（人脸检测） |
| 部署 | systemd · Nginx（可选） |

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 Vue 3 + Element Plus                  │
│  快速生图 / 视频生成 / 对话 Agent / 工坊 / 资产库 / 数据追踪 ...  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP + JWT
┌──────────────────────────▼──────────────────────────────────┐
│                      FastAPI 后端 (async)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ 图片路由  │  │ 视频路由  │  │ Agent    │  │  资产/追踪    │ │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └──────┬───────┘ │
│        │             │             │              │          │
│  ┌─────▼─────────────▼─────────────▼──────────────▼───────┐ │
│  │      Provider 层（图片 8 模型 / 视频 3 通道 / 分析）        │ │
│  └─────────────────────────────────────────────────────────┘ │
│        │             │                                         │
│  ┌─────▼────┐  ┌──────▼──────┐  ┌──────────────────────────┐ │
│  │  SQLite  │  │ 本地文件存储 │  │ 静态文件鉴权 endpoint     │ │
│  │ 用户/任务 │  │ 按 user_id  │  │ /api/file/{kind}/{path}  │ │
│  └──────────┘  └─────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- **Python 3.10+**（推荐 3.12）
- **Node.js 18+**
- **[uv](https://docs.astral.sh/uv/)**：Python 包管理器
- **ffmpeg**：视频缩略图 / 关键帧抽取（可选，仅穿搭素材抓取 + 视频缩略图功能需要）

### 后端

```bash
cd backend
uv sync                                # 安装依赖
cp .env.example .env                   # 复制环境变量模板
# 编辑 .env，填入你的 API Key（至少 JWT_SECRET 必填）
uv run uvicorn app.main:app --reload --port 8001
```

健康检查：

```bash
curl http://localhost:8001/api/health
# {"status":"ok"}
```

### 前端

```bash
cd frontend
npm install
npm run dev                            # 默认 http://localhost:5173
```

前端 Vite 已配置代理，`:5173` 自动转发 `/api` 到 `:8001`。

### 默认管理员账号

首次启动后端时数据库会自动初始化并创建默认管理员：

- **用户名**：`admin`
- **密码**：`admin123`

> ⚠️ **生产部署务必立即修改密码**。建议在 `.env` 配置固定的 `JWT_SECRET`（生成命令：`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`），否则每次重启服务器所有用户会被登出。

---

## 配置说明

所有配置通过环境变量（`backend/.env`）注入，完整模板见 [`backend/.env.example`](backend/.env.example)。核心项：

| 变量 | 必填 | 说明 |
|---|---|---|
| `JWT_SECRET` | ✅ | JWT 签名密钥，长度 ≥32 的随机串 |
| `VOLCENGINE_API_KEY` | 图片/视频/分析 | 火山引擎 API Key（Seedream + Seedance + 豆包分析）|
| `SEEDREAM45_APIYI_API_KEY` | 图片 | Seedream 4.5 经 API易 中转 |
| `SEEDREAM5_APIYI_API_KEY` | 图片 | Seedream 5.0 经 API易 中转 |
| `OPENAI_API_KEY` | 图片 | OpenAI / GPT-Image-2 |
| `APIYI_BALANCE_TOKEN` | 余额展示 | API易 账户系统令牌（非业务 sk- key）|
| `ANTHROPIC_API_KEY` | Agent | Claude Sonnet 4.6（对话式 Agent）|

未配置的模型会自动降级到 Mock 模式，方便本地开发调试。

---

## 目录结构

```
.
├── backend/                   # FastAPI 后端
│   ├── app/
│   │   ├── api/               # 路由层（图片/视频/Agent/资产/追踪 ...）
│   │   ├── agents/            # LangGraph 对话式 Agent
│   │   ├── providers/         # AI 模型 Provider（图片 8 个 + 视频 3 个 + 分析）
│   │   ├── services/          # 业务层（存储/路由/prompt 引擎/工具）
│   │   ├── auth.py            # JWT 鉴权
│   │   ├── database.py        # SQLite 初始化 + 迁移
│   │   └── main.py            # 入口
│   ├── templates/             # prompt 模板（7 类任务）
│   ├── assets/                # mediapipe 模型 + 模特库索引
│   └── .env.example
├── frontend/                  # Vue 3 前端
│   └── src/
│       ├── views/             # 页面（25+ 个视图）
│       ├── components/        # 组件（含 Agent 子组件）
│       ├── composables/       # 组合式函数（auth/agentChat/referenceMention ...）
│       ├── api/               # API 封装
│       ├── router/            # 路由
│       └── utils/             # 工具（fileUrl/markdown/genId/promptAssembly）
├── deploy/                    # systemd 服务配置示例
└── LICENSE
```

---


## 部署

生产部署示例（systemd + Nginx）：

```bash
# 后端
cd backend
uv sync --frozen
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001

# 前端构建（后端托管静态文件）
cd frontend
npm install && npm run build
# 构建产物 dist/ 由后端 StaticFiles 挂载

# systemd 服务参考 deploy/ai-zw.service
```

详细 systemd 配置见 [`deploy/ai-zw.service`](deploy/ai-zw.service)。

---

## 路线图

- [x] 多用户支持 + JWT 鉴权
- [x] 对话式 AI Agent（LangGraph + Claude）
- [x] 素材资产库 + 数据追踪
- [x] Prompt 工坊（结构化生成）
- [ ] API 速率限制 + Agent 单次成本上限
- [ ] Prompt cache 接入（省钱）
- [ ] 虚拟试穿（IDM-VTON）
- [ ] 批量处理 + Docker Compose 部署

---

## 贡献

欢迎 Issue / PR。提交前请注意：

2. 中文注释，变量名英文，Python 3.10+ 兼容
3. 不自动重试 POST 写操作（避免重复扣费）
4. 涉及外部 API 调用时区分 5xx（网关错误，重试）vs 4xx（业务失败，不重试）

---

## License

[MIT](LICENSE) © 2026 gj666m
