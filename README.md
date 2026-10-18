# 医院信息系统课程设计

本项目依据《2002 医院信息系统功能规范》，实现一条可现场验收的门诊业务闭环：

`患者/排班 → 挂号 → 处方 → 收费 → 扣库存 → 发药 → 审计日志`

项目交付包含 React 前端、FastAPI 后端、数据库模型、三层测试、Docker/Compose 配置、CI 门禁和课程验收文档。所有演示数据均为虚构数据。

## 技术栈

- 前端：React、Vite、TypeScript、Vitest
- 后端：FastAPI、Pydantic、SQLAlchemy、Alembic
- 数据库：本地 SQLite；Compose/共享环境支持 PostgreSQL
- 安全：JWT、bcrypt/pwdlib、RBAC、审计日志
- 质量：pytest、Ruff、Playwright、GitHub Actions

## 本地启动

环境要求：Python 3.11+、Node.js 20+、npm。PowerShell 命令从仓库根目录执行。

### 后端

```powershell
Set-Location backend
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -m scripts.init_db
python -m scripts.seed
python -m uvicorn app.main:app --reload --port 8000
```

成功判据：访问 `http://localhost:8000/health` 返回 `status=ok`，Swagger 位于 `http://localhost:8000/docs`。

### 前端

另开 PowerShell：

```powershell
Set-Location frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

成功判据：访问 `http://localhost:5173/login`，前端 API 地址默认为 `http://localhost:8000/api`。

## 演示账号

账号均为虚构课程数据，统一密码为 `Demo123!`：

| 账号 | 角色 | 主要操作 |
|---|---|---|
| `admin.demo` | 管理员 | 审计查询、管理探针 |
| `doctor.demo` | 医生 | 创建和提交处方 |
| `cashier.demo` | 收费员 | 查询号源、挂号、收费 |
| `pharmacist.demo` | 药师 | 发药 |

演示环境不得使用真实患者信息。部署到共享或云环境后必须替换密码和 `JWT_SECRET`。

## 实现状态

| 功能 | 状态 | 关键验收 |
|---|---|---|
| 登录、JWT、RBAC | 已实现 | 错误密码 401，越权 403 |
| 排班、号源、挂号 | 已实现 | 号源减 1、排队号唯一、号源不足 409 |
| 处方、收费、扣库存 | 已实现 | 后端重算金额，库存不足整体回滚 |
| 药房发药、审计日志 | 已实现 | 仅已收费处方可发药，写操作可查询 |
| CSV 导入、报表 | 扩展 | 需单独验收 |
| 智能分诊 | 已实现扩展 | 固定结构、免责声明和 provider 失败兜底 |
| 住院、真实医保/支付、区域平台联调 | 不纳入 MVP | 不得在演示中伪装完成 |

## API 速查

所有业务接口以 `/api` 开头，写操作需要 Bearer JWT。

```text
POST /api/auth/login                    OAuth2 form 登录
GET  /api/auth/me                       当前用户
GET  /api/admin/ping                    admin 权限探针
GET  /api/schedules?dept_id=&date=      查询排班号源
POST /api/registrations                 收费员/管理员挂号
POST /api/prescriptions                 医生创建处方
POST /api/prescriptions/{id}/submit     提交待收费
POST /api/prescriptions/{id}/charge     收费并扣库存
POST /api/prescriptions/{id}/dispense   药师发药
GET  /api/audit-logs                    管理员查询审计
POST /api/triage                        登录用户获取辅助分诊建议
```

金额由后端根据药品价格计算，前端金额输入不被信任；收费、处方状态和库存处于同一事务边界。

`/api/triage` 只接受症状文本，返回候选科室、紧急程度、说明、免责声明和来源；不能诊断、开药或改变处方/收费。provider 超时、错误或不可用时返回固定兜底结果。

## 测试和质量门禁

```powershell
python -m pytest -q
python -m ruff check backend tests
python -m ruff format --check backend tests
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run test --prefix frontend
npm run build --prefix frontend
Set-Location tests/e2e
npm ci
npx playwright install chromium
npm test
```

当前最近一次完整验证：后端/契约 `22 passed`，前端 Vitest `15 passed`，Playwright 主流程 `1 passed`。`python-jose` 的弃用警告已记录，不影响断言结果；发布前仍以 CI 最新结果和 Docker 构建证据为准。

## Docker 和 CI

```powershell
docker compose up --build
```

Web 映射 `http://localhost:5173`，API 映射 `http://localhost:8000`，PostgreSQL 使用命名卷。生产环境必须覆盖本地默认密码和 JWT 密钥。

验收证据边界：当前验收机未安装 Docker CLI，因此本地没有声称 `docker build` 或 `docker compose up` 已通过；CI 工作流会在 Linux runner 上真实执行两个镜像的构建、Compose 配置校验和应用镜像构建，失败会阻断合并。发布前应保存对应 CI run 链接和日志。

CI 在 push/PR 上执行根目录 pytest、后端 Ruff 和测试、前端 lint/typecheck/Vitest/build、Playwright E2E、Compose 校验和真实 Docker 镜像构建。E2E 失败会上传报告、截图、视频和 trace，并阻断合并。

## 课程验收材料

- [最终验收清单](docs/final-acceptance-checklist.md)
- [7 分钟演示脚本](docs/demo-script.md)
- [AI 医疗合规说明](docs/ai-compliance.md)
- [测试报告](docs/test-report.md)
- [Playwright 验收说明](docs/e2e-acceptance.md)
- [CI/CD 说明](docs/ci-cd.md)
- [AI 开发和工程规则](AGENTS.md)

验收时必须真实操作，不使用录屏、静态按钮或假数据掩盖未实现功能。

