# 本次开发测试报告

日期：2026-10-29。分支：dev_lboverfys，验证时为工作区版本；基线93bcbea。仅记录本轮实际执行结果。

## 结果

| 检查 | 本轮结果 | 证据 |
|---|---|---|
| 后端/契约 pytest | 42 passed，1个依赖弃用警告，73.34秒 | evidence/pytest-result.txt |
| 应用语句覆盖率 | 1225条，1124条覆盖，91.76%（终端取整92%） | evidence/coverage-summary.json |
| Ruff检查/格式 | 通过 | evidence/ruff-result.txt |
| 前端ESLint | 通过 | evidence/frontend-lint.txt |
| TypeScript | 通过 | evidence/frontend-typecheck.txt |
| Vitest | 6个文件，16 passed | evidence/frontend-test.txt |
| 前端生产构建 | 通过，输出D盘指定目录 | evidence/frontend-build.txt |
| Chrome DevTools业务主线 | 挂号、两药处方、收费28.00、发药、审计与报表实际核对 | evidence/browser-mainline.md |
| PPT | 8页，逐页视觉检查及文件结构/原生表格检查 | deliverables/和序HIS-课程答辩.pptx |

后端警告来自Starlette TestClient引用anyio.abc.BlockingPortal弃用别名，不是失败；python-jose已升级3.5.0。未隐藏警告或跳过失败用例。

## 关键覆盖

- Decimal金额、北京时间业务日、身份字段脱敏。
- 同药重复项汇总、不足全事务回滚、过期批次跳过、先到期先出、价格快照。
- 独立HTTP请求/数据库连接并发争抢最后号源、最后库存和同处方收费：仅一次成功。
- 草稿编辑/状态限制、重复收费/发药、角色与医生归属、未绑定医生返回403。
- CSV坏行后合法行、重复文件、部分成功、导入上限相关规则。
- 空库迁移、重复初始化不补回消耗；有版本及无版本旧库升级前备份、保留库存/收费/发药历史。
- 禁用账号、修改密码、UTF-8密码字节边界；AI隐私拦截及失败明确待人工评估。

覆盖率范围为backend/app应用语句，不含Alembic/脚本；迁移脚本由独立测试执行，不将该覆盖率冒充整个仓库覆盖率。

## 复现

在项目根目录使用README指定的D盘Python环境与Node可执行文件。后端：`python -m pytest -q --cov=backend/app --cov-report=term-missing`；缓存、COVERAGE_FILE、TEMP/TMP和basetemp应指向D盘任务目录。
静态：`python -m ruff check backend tests`、`python -m ruff format --check backend tests`。
前端：依次执行 `npm run lint/typecheck/test/build --prefix frontend`（分别运行各脚本），生产输出按README指定D盘outDir。

## 验证边界

本轮未运行本地Playwright（遵守Chrome DevTools限定），仓库保留更新后的CI脚本，不能把旧版1 passed算作本次结果。
本机无Docker CLI；本轮本地验证不包含新CI结果；未测试PostgreSQL、真实支付/医保或真实外部LLM。
截图工具因目录限制/超时未取得图片，提供真实文字观察与数据库核对摘要，不伪造截图或trace。
本轮数据为数十条以内的虚构单机演示量，未做大规模压测。

## 数据访问检查

涉及patients、schedules、registration_orders、prescriptions/items、drugs/stocks、charge/dispense_orders、audit_logs、users等13表。
列表默认20条、上限100条，兼容列表限100；处方关联通过selectinload/joinedload批量加载，药品与库存按当前处方ID集合批量读取，无逐条远程调用。CSV最大5000行，已有键每批200个查询，次数随批次数增长，不按行逐次查询。
关键时间/外键/状态索引已检查定义；本机小样本EXPLAIN结果另见 evidence/query-plans.json。不能据此保证生产规模索引选择。
