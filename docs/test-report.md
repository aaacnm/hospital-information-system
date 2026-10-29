# 功能展示版验证记录

日期：2026-10-29。分支：dev_lboverfys，基线0a2ad39。测试在本次提交前的工作区执行，第一轮42项/16项结果保留在原evidence文件中，本报告以下为本版实际结果。

## 本地结果

| 检查 | 结果 | 证据位置（docs/evidence/high-score/） |
|---|---|---|
| 后端/契约pytest | 46 passed，1个依赖弃用警告，76.28秒 | pytest-result.txt |
| 应用语句覆盖率 | 1535条，覆盖1412条，91.99% | coverage-summary.json |
| 收费列表增加处方状态后复测 | 4项相关用例通过 | query-regression.txt |
| Ruff检查/格式 | 通过，48个文件格式正常 | ruff-result.txt |
| 前端ESLint / TypeScript | 通过 | frontend-lint.txt、frontend-typecheck.txt |
| Vitest | 8个文件，20 passed | frontend-test.txt |
| 前端生产构建 | 通过，JS约391.60kB、CSS约52.63kB（未gzip） | frontend-build.txt |
| 展示场景API读取 | 12项200，含四角色、文书、时间线、凭证、预警和流水 | showcase-api-evidence.json |
| 新版PPT | 10页，逐页渲染检查，可编辑表格和图表 | presentation-check.json |

覆盖率范围仅backend/app应用语句，不包含迁移或初始化脚本，不冒充全仓库覆盖率。警告来自Starlette TestClient引用AnyIO弃用别名，没有隐藏或跳过失败用例。

## 本版重点回归

- 文书保存、医生角色限制、提交后锁定、患者时间线与诊断检索。
- 银行卡记账、收费凭证、全额退费、原批次回库、重复退费及已发药拒绝，毛收入/退费/净额一致。
- 库存提醒、流水、报表日期边界、CSV导出。旧库迁移与重复初始化保留已有业务。
- 前端直接验证文书保存后提示不消失、已发药不显示退费按钮、退费后记录更新、库存预警/流水切换。
- 表单label与真实select使用htmlFor/id关联，修正旧CI患者精确标签定位失败的原因。

原有并发、最后号源/库存争抢、重复药品汇总、库存不足回滚、权限与脱敏用例继续包含在46项中。

## 浏览器与CI边界

新页面浏览器视觉与交互验收尚未完成。Chrome DevTools专用配置被占用，用户明确选择“先完成开发，稍后再验收页面”。本版未新建浏览器标签页，未改用Playwright或其他工具绕过，也未取得新版页面截图或实际打印结果。旧版浏览器主线证据仍在evidence/browser-mainline.md，不能代替本版验收。

基线0a2ad39的远程CI：后端、前端、项目契约、Docker配置/启动检查通过；Playwright主流程失败于getByLabel('患者', {exact:true})。本版已修正label关系并更新文书/报表步骤，新CI结果以本次提交关联的运行记录为准，此处不将基线结果当作新版CI结果。

CI链接：https://github.com/aaacnm/hospital-information-system/actions/runs/40853238334 。本机未运行Playwright或Docker；未验证PostgreSQL、真实支付/医保或真实外部模型。

## 数据访问检查

涉及原13张业务表和clinical_records、refund_orders、stock_movements，共16表。展示场景为44次挂号、15名患者、10种药品、数十条收费/流水的小样本，不做生产规模推断。

列表默认20条，上限100条；患者时间线默认10条，上限20条；报表最多90天。收费记录/库存流水使用关联查询；时间线采用关联加载；库存提醒在数据库聚合；区间报表分别分组聚合后在内存按日期匹配。查询次数不随列表每一行逐次增长，没有逐条远程请求。

CSV最大5000行，已有键每200个批量查询，次数随批次数增加。新增表已声明医生/外键/药品时间等索引，本轮未对新查询另做执行计划或大规模压测；原小样本执行计划仅属于旧版记录。

## 复现

从项目根目录用README列出的项目Python和Node执行pytest、Ruff与前端lint/typecheck/test/build。TEMP/TMP、COVERAGE_FILE、basetemp和缓存放D盘独立任务目录。API验证使用本轮独立的虚构展示库，没有连接线上数据库。
