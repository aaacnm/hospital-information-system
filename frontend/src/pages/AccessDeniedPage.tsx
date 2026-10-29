import { Link } from 'react-router-dom';
import { StatusMessage } from '../components/StatusMessage';
export function AccessDeniedPage() { return <section className="page-section narrow-page"><p className="eyebrow">访问受限</p><h1>没有访问权限</h1><StatusMessage tone="error" title="当前角色不能访问此模块">请切换到具有此模块权限的账号，或返回工作台选择可用功能。</StatusMessage><Link className="button button-secondary" to="/">返回工作台</Link></section>; }
