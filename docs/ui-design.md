# 界面设计与组件来源

2026-10-29，按用户追加要求，将原始表单界面改成 shadcn/ui 门诊工作台。

## 视觉与交互

- 品牌：和序 HIS；深青侧栏、浅灰工作区、绿色主操作，搭配低饱和蓝色与琥珀色指标。
- 登录：左右分栏、业务流程说明、四种演示身份快捷填入；真实请求验证后进入工作台。
- 工作台：按角色展示数据库指标、快捷入口、门诊流程；加载时用 Skeleton，失败明确显示。
- 业务页：统一页面标题、筛选表单、分页表格、状态徽章、处方明细和费用；按钮统一高度、焦点与禁用样式。
- 适配：桌面双栏，小屏导航横向滚动；表格在自身容器滚动，保留数据列。

## 官方源码与许可

使用 [shadcn/ui](https://ui.shadcn.com/) 官方 New York v4 registry 的 Button、Input、Textarea、NativeSelect、Table、Card、Badge、Skeleton，保存为项目源码，采用其 MIT 许可。组件文件位于 `frontend/src/components/ui`，项目配置为 `frontend/components.json`。

来源模式：`https://ui.shadcn.com/r/styles/new-york-v4/<component>.json`。组件依赖 Tailwind CSS v4、class-variance-authority、clsx、tailwind-merge；Button 插槽使用 @radix-ui/react-slot，图标来自 lucide-react。沿用项目已存在的 React/Vite/TypeScript，无全局组件安装。

适配仅包括本地导入路径与 Radix Slot 导入方式。业务表单实际使用这些组件，表格封装使用 shadcn Table；页面的侧栏、布局、流程图由项目自行实现。

## 验证边界

TypeScript、ESLint、Vitest 和生产构建已执行，最终结果见 [测试报告](test-report.md)。Chrome DevTools 实际核对登录、处方、收费、发药、审计等页面。截图工具本次受保存目录限制且无文件模式超时，未取得可交付页面截图；不使用设计示意图充当真实截图。
