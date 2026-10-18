# Playwright 端到端验收

## 覆盖范围

`tests/e2e/flow.spec.ts` 覆盖唯一主线：

`收费员登录 → 查询排班 → 创建挂号 → 医生登录/开处方 → 收费 → 药师发药 → 管理员查看审计`

测试使用 `tests/e2e/serve_backend.py` 启动真实 FastAPI 应用和隔离 SQLite 数据库。种子数据仅为虚构数据；挂号、处方、提交、收费、发药和审计查询均由浏览器页面触发，测试不直接调用业务 API 来伪造状态。

## 本地运行

在仓库根目录执行：

```powershell
Set-Location tests/e2e
npm ci
npx playwright install chromium
npm test
```

Playwright 会自动启动：

- API：`http://127.0.0.1:8000`，健康检查 `/health`
- Web：`http://127.0.0.1:4173`，Vite 开发服务器

每次运行使用独立的 `tests/e2e/e2e.db`，该文件由 `.gitignore` 排除。失败时查看 `playwright-report/`、`test-results/` 中的截图、视频和 trace。

## 当前验收状态

页面必须保持当前验收所依赖的可访问标签、按钮名称和状态文本。测试不使用脆弱 CSS 层级，也不通过 API 直调、固定响应或本地假数据绕过页面操作；任一控件、权限或状态契约回归都会让 E2E 失败。

## CI 门禁

GitHub Actions 的 `e2e` job 依赖契约测试、后端检查和前端检查，安装 Chromium 后运行完整 Playwright 流程。无论成功或失败都会上传报告和测试产物；E2E 失败会阻断合并。

