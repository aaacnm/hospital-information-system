import { Link } from 'react-router-dom';
import { StatusMessage } from '../components/StatusMessage';
export function AccessDeniedPage() { return <section className="page-section narrow-page"><p className="eyebrow">HTTP 403</p><h1>没有访问权限</h1><StatusMessage tone="error" title="当前角色不能访问此模块">权限判断必须由后端接口最终执行。前端只隐藏不适用的导航，不把隐藏按钮当作安全措施。</StatusMessage><Link className="button button-secondary" to="/">返回工作台</Link></section>; }
