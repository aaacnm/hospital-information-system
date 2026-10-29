# 接口与权限
本机 API 基址 http://127.0.0.1:8000/api。启动后 /docs 提供当前 OpenAPI；docs/openapi.json 为交付快照。
登录使用 OAuth2 表单，其他写操作 JSON。除健康/登录/CSV空模板外，业务接口需 Bearer JWT。
| 接口 | 权限 | 作用 |
|---|---|---|
| POST /auth/login；GET /auth/me | 登录/已登录 | bcrypt 校验，返回JWT；当前用户 |
| POST /auth/password | 已登录 | 校验当前密码并变更新密码 |
| GET /directory | 已登录 | 业务日期、科室与医生选择项 |
| GET /schedules?date=&dept_id= | 已登录 | 按日查询有效排班 |
| POST /schedules | admin | 新增日期/时段排班 |
| GET /patient-list?keyword=&page=&page_size= | admin/cashier/doctor | 患者分页，医生只见本人挂号关联患者 |
| GET/POST /patients | admin/cashier/doctor | 兼容有限查询/患者建档（服务端脱敏） |
| GET /registrations?page= | admin/cashier/doctor | 挂号列表；医生仅本人 |
| POST /registrations；POST /registrations/{id}/cancel | admin/cashier | 挂号扣号源；接诊前取消释放 |
| GET /prescriptions?status=&page=；GET /prescriptions/{id} | 按角色/归属 | 医生本人；收费员非草稿；药师已收费/已发药 |
| POST /prescriptions；PATCH /prescriptions/{id}；POST /prescriptions/{id}/submit | doctor | 开方/草稿编辑自动计价；提交 |
| POST /prescriptions/{id}/charge | admin/cashier | 收费、批次扣减、状态/日志同事务 |
| POST /prescriptions/{id}/dispense | admin/pharmacist | 仅已收费可发药，不再扣库 |
| GET /drug-list?keyword=&page=；GET /drugs | 已登录 | 药品分页/兼容有限查询 |
| POST /drugs；GET/POST /drugs/{id}/stocks | admin/pharmacist（读可已登录） | 药品档案、批次查询与入库 |
| PATCH /drugs/{id}/price；POST /drugs/import | admin | 改价、CSV导入 |
| GET /reports/today；POST /reports/today/export | admin | 北京时间统计，汇总导出并留痕 |
| GET /audit-logs?page=&page_size=&user_id=&action=&start_date=&end_date= | admin | 分页筛选审计 |
| GET /users；PATCH /users/{id} | admin | 列示账号/角色、启停账号（不允许自禁用） |
| POST /triage | 已登录 | 可选辅助建议，默认关闭外部provider |
列表返回 items/total/page/page_size。金额字段为固定两位字符串；兼容 /patients、/drugs 最多100条，业务页面使用分页入口。
业务错误结构：detail.code/message；Pydantic 参数校验为422。未登录401、无角色权限403、资源不存在404、状态/号源冲突409、库存/效期/CSV错误400。
批次先到期先出，过期不能用于扣减。诊断编码是教学字段，未接入完整ICD字典或医保对码。
