# 门诊业务闭环系统
依据《医院信息系统基本功能规范》（2002 年）的课程选题，实现门诊医生工作站、门诊收费和门诊药房的部分功能。患者建档、排班挂号作为主线支撑。最终交付面向本机现场演示，不需要公网地址。

## 功能展示版（本轮推荐）

本版增加接诊看板、诊疗记录、常用诊断检索、患者就诊时间线、收费记录与未发药退费、处方/凭证打印、库存预警与出入库流水、经营趋势与科室分布。

```powershell
.\start-showcase.ps1
```

在 http://127.0.0.1:8000 展示。首次准备当天的独立虚构场景库；同一天再次启动保留操作，换一天使用新的日期目录，不覆盖旧数据。7天教学记录让图表、待办和预警首次打开就有内容。统一密码Demo123!，账号见下表。

- 展示库：`D:\rubbish\zhongjian\artifacts\医院信息系统\高分升级-20261029\demo\当天日期\hospital.sqlite`。
- 展示前端：`D:\rubbish\zhongjian\build\医院信息系统\high-score\frontend`，首次缺少构建时自动构建，也可加`-Build`重建。
- 当前终端Ctrl+C停止。端口被占用时用`-Port 8001`，不终止原服务。
- 需要全新练习库：用`start-demo.ps1 -Showcase -DatabasePath 新的绝对路径 -WebPath 上述展示前端目录`，不要删除旧库。
- 新版PPT：`deliverables/和序HIS-功能展示版.pptx`；[演示操作稿](docs/demo-script.md)、[课程报告](docs/课程设计报告.md)。

本版前端20项、后端46项测试通过。用户选择将新版页面浏览器验收延后，尚未声称完成页面视觉/打印验收。提交、推送与PR状态以远程仓库记录为准。

## 技术与业务范围
React 19 + Vite + TypeScript；FastAPI + SQLAlchemy + Alembic；本机 SQLite。
流程：患者建档 → 选择排班挂号 → 本人医生接诊/多药处方/自动划价 → 收费与批次库存同一事务 → 药师确认发药 → 审计与统计。
挂号不单独收费；候诊 → 就诊中 → 已完成，接诊前可取消。
处方：草稿（可编辑）→ 待收费 → 已收费 → 已发药；已收费且未发药可全额退费，结束为已退费。开方/编辑时使用药品档案计价并保存价格快照，后续改价只影响新处方。收费时合并同药需求量，按未过期批次先到期先出库；发药不再扣第二次库存。
不包括住院、真实医保、真实支付、PACS 或区域平台联调。AI 默认关闭，只返回人工分诊指引；无外部密钥也能展示完整基础业务。

## 本机启动
已在本任务电脑准备：
- Python：`D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe`
- Node：`D:\Code\nodejs\node.exe`
- 依赖：前端 `frontend/node_modules`；Python 上述独立环境。
- 默认构建：`D:\rubbish\zhongjian\build\医院信息系统\frontend`
- 默认演示库/本地密钥：`D:\rubbish\zhongjian\artifacts\医院信息系统\demo`。

在项目根目录执行（首次加 Build，之后可省略）：
```powershell
.\start-demo.ps1 -Build
```
浏览器打开 [本机演示](http://127.0.0.1:8000)。前端与 API 共用一个进程/端口，当前终端按 Ctrl+C 停止。
脚本先检查端口，不终止已有进程；可用 `-Port 8001` 更换端口。
指定独立演示数据可用 `-DatabasePath D:\你的目录\演示.sqlite`，不清空其他数据库；迁移前自动备份旧库，重复 seed 不恢复已消耗库存。

其他电脑可用 `-PythonPath`、`-NodePath`、`-WebPath` 指定真实路径。交付包含 web 构建时无需 Node 构建；Python 依赖仍需提前准备。脚本不是包含所有运行时的免安装 exe。

## 新电脑准备环境
先检查 Python 3.11+、Node 20.19+/22.12+ 和 D 盘空间。示例只安装项目依赖，不修改全局环境：
```powershell
# 替换“现有Python”为本机已安装解释器路径
& '现有Python\python.exe' -m venv 'D:\rubbish\zhongjian\envs\医院信息系统\dev'
$env:PIP_CACHE_DIR='D:\rubbish\zhongjian\caches\python'
$env:npm_config_cache='D:\rubbish\zhongjian\caches\node'
& 'D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe' -m pip install -r backend/requirements.txt
npm ci --prefix frontend
```
缓存/临时目录应放 D 盘；D 盘不可用时由操作者指定位置，不自动改写 C 盘。当前环境测得规模和验证结果见 docs/test-report.md。

## 虚构演示账号
统一密码 `Demo123!`。不包含真实患者；教学药品与用法不可作为诊疗参考。
| 账号 | 角色 |
|---|---|
| admin.demo | 管理员：排班、药品、导入、统计、审计、禁用账号 |
| doctor.demo | 医生：接诊看板、诊疗记录、本人处方与时间线 |
| cashier.demo | 收费员：患者、挂号、收费、未发药退费与凭证 |
| pharmacist.demo | 药师：药品/批次、发药、库存预警与流水 |
可在“修改密码”页变更。共享使用前更改公开演示密码；真实密钥不得进入 Git。

## 手动后端命令
在 backend 目录，用项目解释器运行 `-m scripts.init_db`、`-m scripts.seed`、`-m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
必须先迁移再启动；应用不再用 create_all 隐式改表。接口文档：[/docs](http://127.0.0.1:8000/docs)；健康检查：[/health](http://127.0.0.1:8000/health)。

## 验证
```powershell
& 'D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe' -m pytest -q
& 'D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe' -m ruff check backend tests
& 'D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe' -m ruff format --check backend tests
npm run lint --prefix frontend
npm run typecheck --prefix frontend
npm run test --prefix frontend
npm run build --prefix frontend -- --outDir D:\rubbish\zhongjian\build\医院信息系统\frontend
```
测试、覆盖率、缓存建议分别用 TEMP/TMP、COVERAGE_FILE、RUFF_CACHE_DIR 指向独立 D 盘任务目录；详细记录见测试报告。
SQLite 写请求在身份查询前用 BEGIN IMMEDIATE 取得写预留；小型本机演示选择串行写，测试验证独立请求争抢号源和库存。未宣称支持高并发生产环境。
浏览器交互按工作区规则只使用 Chrome DevTools MCP；仓库的 Playwright 主流程用于获授权的 CI 环境，不绕过本机工具限制运行。

## 可选 Docker
`docker compose up --build` 启动 API + Web，SQLite 数据持久化到命名卷。本机无 Docker CLI，容器运行验证以实际 CI 为准；本次交付无需 Docker，也不依赖公网。
新 CI 配置包含构建、启动和健康冒烟；本轮本地验证不包含远程 CI 结果，推送后应查看本分支最新运行，不能引用旧版本成功记录代替。
不要执行 `docker compose down -v` 清除演示数据。

## 交付材料
- docs/课程设计报告.md：选题、需求、架构、数据与设计。
- docs/requirements.md、docs/er.md、docs/api.md：功能矩阵、ER/字典、API。
- docs/test-report.md、docs/security-review.md：验证与安全复测。
- docs/ai-development-log.md：本次真实 AI 协作记录。
- docs/demo-script.md：5 分钟演示 + 2 分钟答辩。
- deliverables/：本项目演示 PPT；ppt/ 仍是老师课件。
