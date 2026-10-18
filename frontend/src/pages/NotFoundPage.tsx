import { Link } from 'react-router-dom';
export function NotFoundPage() { return <section className="page-section narrow-page"><p className="eyebrow">HTTP 404</p><h1>页面不存在</h1><p className="page-description">请从主导航选择一个已配置的业务模块。</p><Link className="button button-secondary" to="/">返回工作台</Link></section>; }
