# 和序 HIS 界面说明

按用户要求使用shadcn/ui。深青侧栏、浅灰工作区和绿色主操作贯穿登录、工作台与各业务页面。

## 本版可见内容

- 接诊看板：深绿横幅、实时时钟、候诊/接诊/完成指标、患者卡片与接诊入口。
- 医生诊疗：患者信息条、五项诊疗表单、常用诊断检索、保存提示和文书锁定状态。
- 患者时间线：患者信息卡、按日期排列的就诊记录、诊断/状态/费用与处方入口。
- 收费记录：状态筛选、患者搜索、凭证打印、符合条件处方的退费确认。
- 库存中心：低库存/近效期/过期提醒、数量对照与批次流水。
- 经营看板：日期快捷切换、四项金额/业务指标、双趋势图、科室条形分布和明细。
- 单据打印：A4处方和收费凭证，打印时隐藏导航和工具栏，保留教学标记。

图表使用原生SVG，没有新增图表依赖。表单标签通过label的htmlFor关联真实输入框id，支持键盘与辅助工具精确定位。桌面使用多列布局，小屏切单列，表格在自身容器横向滚动。

## 组件与许可

使用 https://ui.shadcn.com/ 官方New York v4 registry的Button、Input、Textarea、NativeSelect、Table、Card、Badge、Skeleton源码，MIT许可。代码在frontend/src/components/ui，来源及依赖许可见frontend/THIRD_PARTY_NOTICES.md。

侧栏、业务布局和SVG图表为项目实现。使用现有Tailwind CSS v4、Radix Slot、class-variance-authority、clsx、tailwind-merge和lucide-react，本轮未安装新依赖。

## 验证状态

ESLint、TypeScript、20项Vitest和生产构建通过。旧版主流程已有Chrome DevTools文字观察。本版因专用浏览器配置占用，用户选择延后页面验收，因此新版布局、悬停效果和真实打印预览还需浏览器核对；未用示意图充当页面截图。
