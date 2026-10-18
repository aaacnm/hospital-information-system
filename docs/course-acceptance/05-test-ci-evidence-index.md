# 测试与 CI 证据索引

## 本地测试记录

以下是仓库已有的最近记录，不等同于本次现场重新运行。重新运行后请把命令输出或报告路径填入“证据位置”。

| 层级 | 命令 | 最近记录 | 证据位置 |
|---|---|---:|---|
| 根目录契约/后端 | `python -m pytest -q` | 22 passed | `待补：终端输出或 CI log` |
| 后端格式 | `python -m ruff check backend tests` | 通过 | `待补` |
| 后端格式检查 | `python -m ruff format --check backend tests` | 通过 | `待补` |
| 前端单元 | `npm run test --prefix frontend` | 16 passed | `待补` |
| 前端 lint | `npm run lint --prefix frontend` | 通过 | `待补` |
| 前端类型 | `npm run typecheck --prefix frontend` | 通过 | `待补` |
| 前端构建 | `npm run build --prefix frontend` | 通过 | `待补` |
| Playwright | `Set-Location tests/e2e; npm test` | 1 passed | `待补：playwright-report` |

## CI 证据

| 项目 | 预期 | 当前证据 |
|---|---|---|
| commit SHA | 与提交版本一致 | `待填` |
| workflow URL | 可公开/可授权访问 | `待填` |
| 后端 job | pytest、Ruff、migration/seed 通过 | `待填` |
| 前端 job | npm ci、lint、typecheck、build 通过 | `待填` |
| E2E job | Playwright 通过并上传报告 | `待填` |
| Docker job | 两个镜像和 Compose 构建通过 | `待填` |

当前验收机没有 Docker CLI。没有 CI run URL 和日志前，Docker 项目必须保持“待补证据”，不能填写“通过”。

## 证据命名建议

```text
evidence/<commit-sha>/
  01-health.png
  02-registration-before-after.png
  03-prescription-pending-charge.png
  04-charge-stock-audit.png
  05-dispense.png
  06-rbac-403.png
  07-ci-run-url.txt
  08-playwright-report.zip
```

截图和日志不得包含真实患者数据、密钥、完整手机号或身份证号。
