import { StatusMessage } from './StatusMessage';

interface ModulePlaceholderProps { title: string; description: string; requiredRoles: string; endpoint: string; }
export function ModulePlaceholder({ title, description, requiredRoles, endpoint }: ModulePlaceholderProps) {
  return <section className="page-section"><div className="page-heading"><div><p className="eyebrow">业务模块</p><h1>{title}</h1><p className="page-description">{description}</p></div><span className="state-label">待后端接口</span></div><div className="empty-panel"><StatusMessage title="当前页面等待后端服务接入">此页面不会使用本地假数据。接口 <code>{endpoint}</code> 返回真实数据后，这里将展示可操作的业务记录。</StatusMessage><dl className="module-meta"><div><dt>接口</dt><dd><code>{endpoint}</code></dd></div><div><dt>访问角色</dt><dd>{requiredRoles}</dd></div><div><dt>数据原则</dt><dd>服务端计算、操作后刷新、写操作记录审计</dd></div></dl></div></section>;
}
