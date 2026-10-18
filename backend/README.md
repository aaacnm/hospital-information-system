# Hospital Information System API

这是医院信息系统课程设计的后端基础包，当前提供工程骨架、数据模型、数据库初始化、演示种子数据和登录/RBAC 基础边界。挂号、处方、收费、库存和发药业务将在后续小任务中分别实现。

## 环境

- Python 3.11+
- 默认数据库为本地 SQLite；多人或部署环境通过 `DATABASE_URL` 切换 PostgreSQL。
- PowerShell 命令均在 `backend/` 目录执行。

## 安装与配置

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

生产或共享环境必须把 `JWT_SECRET` 替换为随机长密钥；真实 `.env` 不得提交 Git。

## 初始化、种子和启动

```powershell
python -m scripts.init_db
python -m scripts.seed
python -m uvicorn app.main:app --reload --port 8000
```

启动成功判据：访问 `http://localhost:8000/health` 返回 `{"status":"ok", ...}`，Swagger 位于 `/docs`。

演示账号均为虚构数据，密码统一为 `Demo123!`：`admin.demo`、`doctor.demo`、`cashier.demo`、`pharmacist.demo`。首次部署后应立即改为本地演示专用密码。

## 接口边界

- `GET /health`：数据库连通性健康检查。
- `POST /api/auth/login`：OAuth2 form 登录，返回 Bearer JWT。
- `GET /api/auth/me`：需要登录，返回当前用户和角色。
- `GET /api/admin/ping`：仅 admin，用于部署冒烟和 RBAC 403 验收。
- `GET /api/schedules?dept_id=&date=`：登录用户查询有效排班和剩余号源。
- `POST /api/registrations`：收费员或管理员挂号并原子扣减号源。
- `POST /api/prescriptions`、`/{id}/submit`：医生创建并提交处方。
- `POST /api/prescriptions/{id}/charge`：收费员按药品当前价格重算、收费并扣库存。
- `POST /api/prescriptions/{id}/dispense`：药师为已收费处方发药。
- `GET /api/audit-logs`：管理员分页查询写操作审计记录。
- `GET/POST /api/patients`：业务角色查询或创建脱敏患者档案。
- `GET/POST /api/drugs`：查询或维护药品档案；`PATCH /api/drugs/{id}/price` 仅管理员改价。
- `POST /api/drugs/import`：管理员上传 UTF-8/GBK CSV，返回逐行成功/失败明细。
- `POST /api/registrations/{id}/cancel`：未进入处方流程的挂号取消并释放号源。
- `GET /api/reports/today`：管理员查询今日挂号量、收费金额和发药量。
- `POST /api/triage`：登录用户可获取辅助分诊建议；仅返回允许的科室和优先级，不诊断、不自动开药，失败时返回全科门诊兜底。

### 可选 AI provider

默认 `AI_PROVIDER=disabled`，不会发起外部请求。仅在明确配置 provider 时启用兼容 OpenAI Chat Completions 的服务：

```text
AI_PROVIDER=disabled|openai|openai_compatible
AI_API_KEY=
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

密钥只允许来自环境变量或云平台 Secret，不能写入代码、前端或 Git。调用超时固定为 10 秒，网络异常、空输入、恶意提示词或 JSON 不符合契约时返回固定“全科门诊”结果。所有返回都包含“仅供参考，请以医生诊断为准”，AI 不得诊断、开药或修改收费结果。

## 数据库迁移

Alembic 已建立迁移入口。当前本地开发启动会通过 SQLAlchemy `create_all` 创建基础表，正式环境应使用：

```powershell
alembic upgrade head
```

后续模型变化必须新增可追踪 migration，不直接修改共享数据库。

## 检查与测试

```powershell
pytest -q
ruff check .
ruff format --check .
```

测试覆盖健康检查、登录成功/失败、JWT 当前用户、RBAC 403，以及挂号到发药的业务闭环、库存不足回滚、重复收费和号源冲突。
