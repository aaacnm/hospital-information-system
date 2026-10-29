# 路径与磁盘检查

本次复用已安装运行时，不新增系统工具：Python基础运行时位于C盘Codex bundled runtime；实际项目解释器入口为 `D:\rubbish\zhongjian\envs\医院信息系统\dev\Scripts\python.exe`，项目包安装在该独立环境。Node使用 `D:\Code\nodejs\node.exe`，前端依赖位于项目frontend/node_modules。

2026-10-29实测文件逻辑大小（不是磁盘分配大小）：

| 位置 | 实测 |
|---|---|
| 项目前端node_modules | 约184.1 MiB，14216个文件 |
| 项目Python独立环境 | 约104.3 MiB，3848个文件 |
| D盘医院信息系统构建目录（打包前） | 约2.5 MiB |
| D盘本次独立临时目录（打包前） | 约16.5 MiB |
| 最终答辩PPT | 45336字节 |

Python缓存 `D:\rubbish\zhongjian\caches\python` 约3.62 GiB、Node缓存 `D:\rubbish\zhongjian\caches\node` 约3.05 GiB，均为已有共享缓存的当前总量，不是本次新增量；没有删除共享数据。
临时文件位于 `D:\rubbish\zhongjian\temp\医院信息系统\dev-lboverfys-20261029`，构建和最终交付分别位于 `D:\rubbish\zhongjian\build\医院信息系统`、`D:\rubbish\zhongjian\artifacts\医院信息系统`。交付包占用见交付清单。

C盘检查限于本次可能涉及的已知默认缓存路径：pip/Cache不存在，npm-cache仅1898字节、最后修改为2025-08-30；未在这些位置发现本轮大量依赖/缓存写入。没有扫描整个C盘，也不声称已排除所有工具内部写入。Codex/MCP必要的少量状态沿用现有标准位置。
