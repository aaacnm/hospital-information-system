# 课程验收材料包

本目录是医院信息系统课程设计的现场验收材料包。材料以当前仓库代码、测试和既有文档为准，不替代自动化测试，也不把静态页面或录屏当作业务证据。

## 材料目录

| 文件 | 用途 | 当前状态 |
|---|---|---|
| [01-submission-checklist.md](01-submission-checklist.md) | 提交物、环境和证据总清单 | 已整理，现场勾选 |
| [02-demo-runbook.md](02-demo-runbook.md) | 5-7 分钟真实演示流程 | 已整理，需现场填入实际 ID |
| [03-business-loop-record.md](03-business-loop-record.md) | 业务闭环逐步验收记录模板 | 已整理，截图位置待补 |
| [04-role-permission-matrix.md](04-role-permission-matrix.md) | 角色、接口和 401/403 验收表 | 已整理，现场记录响应证据 |
| [05-test-ci-evidence-index.md](05-test-ci-evidence-index.md) | 测试结果、CI、Docker 证据索引 | 本地测试有记录，CI/Docker 待补链接 |
| [06-ai-triage-compliance.md](06-ai-triage-compliance.md) | AI 分诊边界、风险和人工复核 | 已整理，AI 为扩展项 |
| [07-open-items-risks.md](07-open-items-risks.md) | 未完成项、风险和答辩口径 | 已整理，发布前更新 |

## 当前可引用的仓库证据

- 后端/契约测试：`python -m pytest -q`，最近记录为 `22 passed`。
- 前端 Vitest：最近记录为 `16 passed`。
- Playwright 主流程：最近记录为 `1 passed`。
- Ruff、前端 lint/typecheck/build：最近记录为通过。
- Docker：当前验收机未安装 Docker CLI；不得把本地容器构建写成已通过，需引用 CI run。
- 现场截图、CI URL、部署 URL、手机热点访问截图：均需由提交人补入，不得编造。

## 使用规则

1. 先复制模板中的“实际结果”和“证据位置”字段，再执行演示或测试。
2. 每张截图只使用虚构数据，并记录截图文件名、页面和时间。
3. 不能证明的项目保持“待补/未验证”，不要改成“通过”。
4. 演示前用全新种子数据库运行一次主流程，避免重复收费、重复排队号影响结果。
