# CI与本机交付

本次选择本机现场演示，无需公网地址或云端部署。`start-demo.ps1`启动单端口Web/API，Alembic迁移、重复安全seed、SQLite持久化；详见README。

工作流 `.github/workflows/ci.yml` 提供契约、后端Ruff/pytest、前端lint/类型/测试/构建、Playwright主流程与Docker检查。
Docker任务现配置为真实构建镜像、Compose启动等待健康、health/login/挂号列表冒烟，always日志与down收尾；保留数据卷，不用down -v。
Compose为API+Web两个服务、SQLite命名卷，端口仅绑定127.0.0.1。不再以PostgreSQL容器作为本次验收依赖。

本机没有Docker CLI，因此只完成Docker/Compose配置审查。本轮本地检查没有本分支新CI结果，推送后应查看最新运行。历史main上的成功run只能证明历史版本，不作为当前修改通过证据。
用户随后明确授权提交并推送dev_lboverfys分支；未要求创建PR。需要异机运行时，先按README准备项目环境；交付包不是包含Python运行时的免安装exe。
