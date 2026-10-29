# 第二轮环境与磁盘记录

复用D盘项目Python入口和独立包目录：D:\rubbish\zhongjian\envs\医院信息系统\dev。其基础解释器是C盘已有Codex bundled runtime，本轮未安装或更新运行时。项目Node为D:\Code\nodejs\node.exe，前端依赖保留frontend/node_modules，没有新增依赖。

缓存沿用D:\rubbish\zhongjian\caches\python与caches\node。TEMP/TMP指向D盘high-score-20261029任务目录；启动脚本使用D盘local-demo目录。前端构建、PPT渲染/候选、交付暂存均位于D:\rubbish\zhongjian\build\医院信息系统\high-score。

打包前实测逻辑大小：构建目录约2.87MiB（228文件，含交付暂存）；本轮独立临时目录约13.86MiB（1488文件）；最终产物目录当时约0.92MiB（含三份独立虚构展示库与新版PPT）。最终ZIP和当前目录实测值以产物目录delivery-manifest.json为准，以上不是磁盘分配大小。

C盘只检查本次涉及的已知默认缓存位置：npm-cache共1898字节、最后修改2025-08-30；pip/Cache不存在。这些位置未发现本轮大量依赖/下载写入。没有扫描整个C盘，不将不可见工具内部少量状态声称为已完全排除。Codex/MCP必要状态保留标准位置，未迁移工具配置或删除共享缓存。

最终PPT、报告、操作稿和ZIP位于D:\rubbish\zhongjian\artifacts\医院信息系统\高分升级-20261029。旧版最终文件保留，未覆盖。
