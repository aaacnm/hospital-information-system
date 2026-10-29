# 安全与业务正确性审查
本次记录来自当前分支的真实静态发现、代码修改及对应测试。AI完成发现与实现，未替组员签署人工复核；提交者应阅读并在答辩前自行确认。
| 发现 | 原因 | 修改 | 验证入口 |
|---|---|---|---|
| 重复药品可累计扣成负库存 | 每条分别检查，随后累计扣减 | 按药品汇总需求、批次FEFO、数据库非负约束 | test_repeated_drug_cannot_overdraw_stock |
| SQLite 号源/库存争抢未保障 | FOR UPDATE 不提供SQLite行锁 | 写请求在读之前BEGIN IMMEDIATE，串行写 | test_independent_sqlite_requests_are_atomic，3种场景 |
| 处方未自动划价 | 创建/提交只保存0元 | 后端开方/编辑计算金额、单价快照 | test_invoice_is_priced_before_charge_and_keeps_snapshot |
| 普通初始化缺数据 | 完整数据只在测试脚本 | 普通seed提供患者/排班/药品/批次，重复运行不补回消耗 | test_migration_and_seed_are_repeatable_and_preserve_existing_data |
| 身份字段未保证脱敏 | 字段名masked不能实现保护 | 保存与响应均在服务端脱敏 | test_sensitive_patient_fields_are_masked_and_disabled_login_rejected |
| 禁用账号仍可能签发token | 登录没检查status | 登录及当前用户都检查状态 | 同上，以及 test_password_change_and_user_status_are_audited |
| CSV重复入库与坏行误去重 | 只按文件seen，无数据库检查 | 有效行后去重、已有键每批200查询、5000行与2MB上限 | test_csv_repeat_and_bad_then_good_row |
| AI文本可含身份信息 | 症状直接外发 | 身份号/电话/身份字段模式拦截，失败标待人工评估 | test_private_triage_input_never_reaches_provider |
| 审计手工调用易漏 | 业务各自记录 | 保留语义日志，增加after_flush自动非敏感变更日志 | API日志筛选与操作测试 |
| 容器不包含迁移/初始化 | 只COPY app | 包含scripts/alembic并先迁移seed | 静态检查；本机无Docker，未声称运行验证 |

## 边界
- 默认密钥只用于开发；生产模式拒绝默认密钥；本机脚本为独立数据库目录生成随机密钥。
- CORS有限来源，ORM参数绑定，后端检查角色与医生归属；路由隐藏只是体验层。
- 不记录密码哈希、JWT、完整身份证/电话和原始症状到审计。
- 本轮检查当前代码与有限Git历史中的常见密钥模式，不等于专业渗透测试或完整敏感数据认证。
- 外部AI文本无法靠正则证明完全匿名。仅使用虚构症状，默认关闭provider；真实医疗信息禁止用于课程演示。
- 程序尚保留依赖弃用警告，具体见测试报告；未通过禁用断言或隐藏异常来伪造测试通过。
