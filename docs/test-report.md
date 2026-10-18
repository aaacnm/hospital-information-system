# 测试报告基线

## 当前状态

当前工作区已具备 FastAPI 和 React 工程，并有挂号、处方、收费、库存和发药的可验收 MVP 闭环；AI 分诊扩展也有接口、页面和 provider 失败兜底测试。取消挂号、CSV 导入和统计仍属于扩展能力。

当前可运行的测试入口包括项目契约、后端 API、前端 Vitest 和 Playwright 浏览器验收：

```powershell
python -m pip install pytest
python -m pytest -q
```

`tests/api/` 中的 health 和认证测试连接真实 FastAPI 应用。依赖或应用尚不存在时，它们会显示为明确的 `skipped`，而不是伪造 200/401 响应；依赖安装且应用存在后，缺少路由或状态码不正确会使测试失败。CI 的契约测试 job 会安装 `backend/requirements.txt`，因此当前应执行真实 API 测试。

最近一次本地验证：

```text
python -m pytest --collect-only -q
python -m pytest -q
22 passed
```

22 个后端/契约用例包含项目契约、health/认证、挂号、处方、收费回滚、发药、角色边界、CSV、取消挂号、统计和 AI 分诊；当前后端测试已修复并通过。40 个警告来自 `python-jose` 内部使用已弃用的 `datetime.utcnow()`，后续应在依赖升级或安全评审中处理。

前端和浏览器验收：

```text
npm run test --prefix frontend       # 15 passed
Set-Location tests/e2e; npm test     # 1 passed
```

Playwright 流程实际启动隔离 SQLite 后端和 Vite 前端，并通过浏览器完成登录、排班、挂号、处方、收费、发药和审计查询。失败时 CI 必须保留 HTML 报告、截图、视频和 trace。

## 必须补齐的测试证据

| 层级 | 最低范围 | 通过证据 |
|---|---|---|
| 单元 | 金额、号源、库存、状态机、角色映射 | `pytest tests/unit -q` 输出和覆盖率 |
| API | health、登录、`/me`、挂号、收费回滚、发药、403 | `pytest tests/api -q` |
| E2E | 收费员登录到管理员查审计的真实闭环 | Playwright 报告、截图和 trace |

## 发布门槛

进入 `main` 前必须满足：

1. 不再存在未解释的失败测试或安全告警。
2. 后端 lint、格式检查和 pytest 全部通过。
3. 前端 lint、类型检查和 production build 全部通过。
4. 关键路径覆盖率目标达到 70%；钱、库存、号源、权限和状态机必须有边界用例。
5. 测试数据库使用固定虚构种子数据，运行前后清理状态。

## 风险与未完成项

- 本轮测试覆盖 MVP 闭环；扩展功能和生产 PostgreSQL 迁移仍需单独验收。
- Dockerfile、Nginx 配置和 Compose 健康检查已提供；本机未安装 Docker CLI，因此本地不能给出镜像构建或容器启动证据。
- CI 会真实执行两个应用镜像的 `docker build` 和 Compose 应用镜像构建；构建失败会阻断流水线。

