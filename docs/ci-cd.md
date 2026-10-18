# 持续集成与持续交付基线

## 目标

`.github/workflows/ci.yml` 是课程项目的质量门禁入口。它将项目契约测试、后端检查、前端检查和 Compose 配置校验拆成独立 job，使失败原因可以定位到具体层级。

## 当前可用行为

- `contract-tests` 现在即可运行，执行治理文档检查和已注册的测试。
- 后端、前端尚未创建时，CI 明确输出 pending warning，不伪造构建成功。
- 后端出现后必须提供 `requirements.txt` 或 `pyproject.toml`；前端出现后必须同时提供 `package.json` 和 `package-lock.json`，否则 CI 失败。
- Compose 先做语法验证，再由 CI 真实构建 `backend` 和 `frontend` 镜像；构建失败会阻断流水线。

## 分支与发布

1. `feature/<name>` 分支只完成一个可验收小任务。
2. Pull Request 必须通过 CI，再合并到受保护的 `main`。
3. 发布使用 `v0.x.y` 标签，记录 commit、迁移版本、镜像标签和测试结果。
4. 先部署测试环境并执行 health check，再发布演示环境；失败时保留上一版镜像作为回滚点。

## 变为完整门禁的条件

业务骨架完成后，workflow 已启用：

- 后端迁移和固定种子数据。
- `pytest`、Ruff 和格式检查。
- 前端 `npm ci`、lint、typecheck、build。
- Docker 镜像构建和 Compose 应用镜像构建；镜像内及 Compose 中均配置健康检查。
- Playwright 主流程，并上传截图、trace 和日志 artifact。

## 环境变量与安全

真实密钥只能放在 GitHub/云平台 Secret。仓库只提交 `.env.example`；`.env`、数据库文件、备份和测试凭据由 `.gitignore` 排除。Compose 中的本地默认数据库密码仅用于本地启动，不能用于生产部署。

## 镜像与健康检查

- `backend/Dockerfile` 使用非 root 用户运行 `uvicorn app.main:app`，容器端口为 `8000`，健康检查访问 `/health`。
- `frontend/Dockerfile` 使用 Node 多阶段构建，再由 Nginx 在容器端口 `80` 提供静态文件；Nginx 将 `/api/` 反向代理到 `api:8000`，支持 React 路由回退。
- Compose 对 PostgreSQL、API 和 Web 都配置健康检查；Web 仅在 API 健康后启动。

本地若未安装 Docker CLI，只能完成 YAML 和 Dockerfile 静态检查，不能声称镜像构建或容器启动已通过。GitHub Actions runner 会执行真实 `docker build` 和 `docker compose build`。

