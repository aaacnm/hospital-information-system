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
| GET /registrations?keyword=&visit_date=&status=&page=&page_size= | admin/cashier/doctor | 挂号分页；医生仅本人；日期与状态可选 |
| POST /registrations；POST /registrations/{id}/cancel | admin/cashier | 挂号扣号源；接诊前取消释放 |
| GET /prescriptions?status=&keyword=&page=&page_size=；GET /prescriptions/{id} | 按角色/归属 | 医生本人；收费员非草稿；药师已收费/已发药；keyword 匹配患者姓名或编号 |
| POST /prescriptions；PATCH /prescriptions/{id}；POST /prescriptions/{id}/submit | doctor | 开方/草稿编辑自动计价；提交 |
| POST /prescriptions/{id}/charge | admin/cashier | 收费、批次扣减、状态/日志同事务 |
| POST /prescriptions/{id}/dispense | admin/pharmacist | 仅已收费可发药，不再扣库 |
| GET /drug-list?keyword=&page=&page_size=；GET /drugs | 已登录 | 药品分页/兼容有限查询；分页项含 available_stock（未过期批次可用量） |
| POST /drugs；GET/POST /drugs/{id}/stocks | admin/pharmacist（读可已登录） | 药品档案、批次查询与入库 |
| PATCH /drugs/{id}/price；POST /drugs/import | admin | 改价、CSV导入 |
| GET /reports/today；POST /reports/today/export | admin | 北京时间统计，汇总导出并留痕 |
| GET /workload | 已登录 | 按角色返回工作台统计：管理员待收费/待发药；医生草稿/已提交与今日候诊/就诊中/已完成；收费员待收费与今日挂号/收费/退费；药师待发药与今日发药 |
| GET /audit-logs?page=&page_size=&user_id=&action=&start_date=&end_date= | admin | 分页筛选审计 |
| GET /users；PATCH /users/{id} | admin | 列示账号/角色、启停账号（不允许自禁用） |
| POST /triage | 已登录 | 可选辅助建议，默认关闭外部provider |
列表返回 items/total/page/page_size。金额字段为固定两位字符串；兼容 /patients、/drugs 最多100条，业务页面使用分页入口。drug-list 的 available_stock 由同页药品ID批量聚合未过期批次得到，不随行逐条查询。
业务错误结构：detail.code/message；Pydantic 参数校验为422。未登录401、无角色权限403、资源不存在404、状态/号源冲突409、库存/效期/CSV错误400。
批次先到期先出，过期不能用于扣减。诊断编码是教学字段，未接入完整ICD字典或医保对码。


## 功能展示版新增接口

| 接口 | 权限 | 页面用途 |
|---|---|---|
| POST /registrations/{id}/start | doctor（本人） | 候诊改为就诊中 |
| GET /diagnoses?keyword= | 已登录 | 12项常用诊断教学示例检索 |
| GET /registrations/{id}/clinical-record | admin/doctor（本人） | 患者信息与本次文书 |
| PUT /registrations/{id}/clinical-record | doctor（本人） | 保存五项文书，签署后拒绝修改 |
| GET /patients/{id}/timeline?page=&page_size= | admin/doctor（本人就诊） | 患者就诊时间线，默认10条、最多20条 |
| POST /prescriptions/{id}/refund | admin/cashier | JSON reason，未发药全额退费与原批次回库 |
| GET /prescriptions/{id}/receipt | admin/cashier | 原收费凭证、收费员和退费标记 |
| GET /billing-records?keyword=&status=&page= | admin/cashier | 收费分页，含处方状态以控制退费入口 |
| GET /stock-alerts?kind=&page= | admin/pharmacist | low/expiring/expired或全部提醒 |
| GET /stock-movements?drug_id=&prescription_id=&kind=&page= | admin/pharmacist | 批次出入库流水 |
| GET /reports/range?start_date=&end_date= | admin | 最多90天，逐日与科室聚合 |
| POST /reports/range/export?start_date=&end_date= | admin | UTF-8 BOM CSV，导出留痕 |

收费POST可传payment_method：现金、银行卡、模拟扫码；不传时为现金。均为模拟记账。
退费拒绝已发药、已退费、缺少原批次出库流水的处方。原收费记录状态refunded，处方状态已退费。
金额保持两位小数字符串；区间净额=本区间发生收费-本区间发生退费。打印页组合读取处方与凭证接口，不新增伪造发票接口。
