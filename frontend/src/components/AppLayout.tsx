import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import type { Role } from '../api/types';

interface NavigationItem { label: string; path: string; roles?: Role[]; }
const navigation: NavigationItem[] = [
  { label: '工作台', path: '/' },
  { label: '排班与号源', path: '/schedules', roles: ['admin', 'cashier', 'doctor'] },
  { label: '挂号管理', path: '/registrations', roles: ['admin', 'cashier'] },
  { label: '处方管理', path: '/prescriptions', roles: ['admin', 'doctor', 'cashier', 'pharmacist'] },
  { label: '收费台', path: '/billing', roles: ['admin', 'cashier'] },
  { label: '药房发药', path: '/dispensing', roles: ['admin', 'pharmacist'] },
  { label: '审计日志', path: '/audit-logs', roles: ['admin'] },
  { label: '智能分诊', path: '/triage', roles: ['admin', 'doctor', 'cashier', 'pharmacist'] },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const allowed = navigation.filter((item) => !item.roles || item.roles.some((role) => user?.roles.includes(role)));
  return <div className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">HIS</span><div><strong>门诊业务工作台</strong><small>课程设计演示环境</small></div></div><div className="account-area"><span>{user?.displayName || user?.username}</span><span className="role-chip">{user?.roles.join(' / ')}</span><button className="button button-quiet" type="button" onClick={logout}>退出登录</button></div></header><div className="app-body"><aside className="sidebar" aria-label="主导航"><nav>{allowed.map((item) => <NavLink key={item.path} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'} to={item.path} end={item.path === '/'}>{item.label}</NavLink>)}</nav><div className="sidebar-note"><span className="status-dot" /> API：{import.meta.env.VITE_API_BASE_URL || '/api'}</div></aside><main className="main-content"><Outlet /></main></div></div>;
}
