import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { StatusMessage } from '../components/StatusMessage';

export function DashboardPage() {
  const { user } = useAuth();
  const actions = user?.roles.includes('cashier') ? [{ label: '查看排班号源', path: '/schedules' }, { label: '进入收费台', path: '/billing' }] : user?.roles.includes('doctor') ? [{ label: '查看今日排班', path: '/schedules' }, { label: '处理处方', path: '/prescriptions' }] : user?.roles.includes('pharmacist') ? [{ label: '待发药处方', path: '/dispensing' }, { label: '查看处方', path: '/prescriptions' }] : [{ label: '查看系统审计', path: '/audit-logs' }, { label: '维护药品数据', path: '/prescriptions' }];
  return <section className="page-section"><div className="page-heading"><div><p className="eyebrow">今日概览</p><h1>你好，{user?.displayName || user?.username}</h1><p className="page-description">当前工作台只展示服务端已确认的状态，不预填业务成功数据。</p></div><span className="state-label">已登录</span></div><StatusMessage title="业务数据尚未加载">后端健康检查、今日统计和待办列表接入后会显示在这里。先从一个具体模块开始，完成后再进行端到端验证。</StatusMessage><div className="metric-grid"><article className="metric-card"><span>今日挂号</span><strong>—</strong><small>等待 <code>/api/reports/today</code></small></article><article className="metric-card"><span>待收费处方</span><strong>—</strong><small>等待 <code>/api/prescriptions</code></small></article><article className="metric-card"><span>待发药处方</span><strong>—</strong><small>等待 <code>/api/prescriptions?status=已收费</code></small></article></div><div className="action-panel"><h2>按角色开始</h2><div className="action-list">{actions.map((action) => <Link className="action-link" key={action.path} to={action.path}>{action.label}<span aria-hidden="true">→</span></Link>)}</div></div></section>;
}
