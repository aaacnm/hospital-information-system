# 测试入口

测试分为三层：

- `tests/test_project_contract.py`：现在即可运行，检查治理文档和交付入口存在。
- `tests/api/`：调用真实 FastAPI 应用；在 `backend/app/main.py` 尚未存在时会明确跳过，绝不返回伪造响应。
- `backend/tests/`：后端认证和门诊闭环 API 测试，根目录 `pytest -q` 会自动发现。

在仓库根目录运行：

```powershell
python -m pip install pytest
python -m pytest -q
```

根目录命令会发现 `tests/` 和 `backend/tests/`，并通过 `pytest.ini` 的 `pythonpath` 导入 `backend/app`。后端创建后，应先安装后端锁定依赖，再运行同一命令。`/health` 和 `/api/auth/me` 的测试会从跳过变为真实接口断言；业务闭环测试会验证挂号、处方、收费回滚、发药、权限和号源冲突。

## Playwright 真实验收

`tests/e2e/` 包含独立的 Playwright 工程。它会启动临时 SQLite 后端和 Vite 前端，使用虚构种子数据，然后要求浏览器真实完成登录、排班、挂号、处方、收费、发药和审计页面操作：

```powershell
Set-Location tests/e2e
npm ci
npx playwright install chromium
npm test
```

测试不会通过 API 请求替代页面操作，也不会注入业务成功状态。若页面控件、接口或状态契约回归，E2E 会失败并保留 `playwright-report/`、截图、视频或 trace；这属于真实验收阻塞，不应改成跳过。

