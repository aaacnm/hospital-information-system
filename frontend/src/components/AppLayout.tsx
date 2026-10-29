import {useEffect} from 'react';
import {Link, NavLink, Outlet, useLocation} from 'react-router-dom';
import {
  Activity,
  Boxes,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronRight,
  ClipboardList,
  FileInput,
  KeyRound,
  LayoutDashboard,
  LogOut,
  PackageSearch,
  Pill,
  ReceiptText,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UsersRound,
  Wallet,
} from 'lucide-react';
import {useAuth} from '../auth/AuthContext';
import type {Role} from '../api/types';
import {Button} from './ui/button';
import {Badge} from './ui/badge';
import {localDay} from '../api/hooks';

const navigation = [
  {label: '工作台', path: '/', icon: LayoutDashboard, group: '门诊业务'},
  {label: '接诊看板', path: '/queue-board', icon: LayoutDashboard, roles: ['admin', 'cashier', 'doctor'], group: '门诊业务'},
  {label: '患者档案', path: '/patients', icon: UsersRound, roles: ['admin', 'cashier', 'doctor'], group: '门诊业务'},
  {label: '排班与号源', path: '/schedules', icon: CalendarDays, roles: ['admin', 'cashier', 'doctor'], group: '门诊业务'},
  {label: '挂号与待诊', path: '/registrations', icon: Stethoscope, roles: ['admin', 'cashier', 'doctor'], group: '门诊业务'},
  {label: '处方管理', path: '/prescriptions', icon: ClipboardList, group: '门诊业务'},
  {label: '收费台', path: '/billing', icon: ReceiptText, roles: ['admin', 'cashier'], group: '收费与药房'},
  {label: '收费记录与退费', path: '/financial-records', icon: Wallet, roles: ['admin', 'cashier'], group: '收费与药房'},
  {label: '药房发药', path: '/dispensing', icon: Pill, roles: ['admin', 'pharmacist'], group: '收费与药房'},
  {label: '药品与库存', path: '/drugs', icon: PackageSearch, roles: ['admin', 'pharmacist'], group: '收费与药房'},
  {label: '库存预警与流水', path: '/inventory-center', icon: Boxes, roles: ['admin', 'pharmacist'], group: '收费与药房'},
  {label: '经营数据看板', path: '/reports', icon: ChartNoAxesCombined, roles: ['admin'], group: '数据与系统'},
  {label: '药品导入', path: '/import', icon: FileInput, roles: ['admin'], group: '数据与系统'},
  {label: '审计日志', path: '/audit-logs', icon: ScrollText, roles: ['admin'], group: '数据与系统'},
  {label: '账号与角色', path: '/accounts', icon: ShieldCheck, roles: ['admin'], group: '数据与系统'},
  {label: '智能分诊', path: '/triage', icon: Sparkles, group: '辅助与设置'},
  {label: '修改密码', path: '/password', icon: KeyRound, group: '辅助与设置'},
];
const groups = ['门诊业务', '收费与药房', '数据与系统', '辅助与设置'];
const roles: Record<Role, string> = {admin: '系统管理员', doctor: '门诊医生', cashier: '挂号收费员', pharmacist: '药房药师'};

export function AppLayout() {
  const {user, logout} = useAuth();
  const location = useLocation();
  const allowed = navigation.filter(item => !item.roles || item.roles.some(role => user?.roles.includes(role as Role)));
  const current = navigation.find(item => item.path === location.pathname)?.label || '门诊工作台';
  const role = user?.roles[0] || 'cashier';

  useEffect(() => {
    document.title = `${current} · 和序 HIS`;
  }, [current]);

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="主导航">
        <Link to="/" className="brand">
          <span className="brand-mark"><Activity size={20} strokeWidth={2}/></span>
          <span>
            <strong>和序 HIS</strong>
            <small>门诊业务管理系统</small>
          </span>
        </Link>
        <nav>
          {groups.map(group => (
            <div className="nav-group" key={group}>
              {allowed.some(item => item.group === group) && <p className="nav-group-title">{group}</p>}
              {allowed.filter(item => item.group === group).map(item => (
                <NavLink
                  key={item.path}
                  className={({isActive}) => 'nav-link ' + (isActive ? 'active' : '')}
                  to={item.path}
                  end={item.path === '/'}
                >
                  <item.icon size={16} strokeWidth={1.7}/>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot"/>
          <div>
            <strong>本机演示环境</strong>
            <small>仅使用虚构教学数据</small>
          </div>
          <ShieldCheck size={15}/>
        </div>
      </aside>
      <div className="app-body">
        <header className="topbar">
          <div className="breadcrumb">
            <span>和序 HIS</span>
            <ChevronRight size={13}/>
            <strong>{current}</strong>
          </div>
          <div className="account-area">
            <span className="topbar-date"><CalendarDays size={13}/>{localDay()}</span>
            <Badge variant="outline" className="role-chip">{roles[role]}</Badge>
            <div className="avatar">{user?.displayName?.slice(-1) || '医'}</div>
            <div className="account-name">
              <strong>{user?.displayName || user?.username}</strong>
              <small>{user?.username}</small>
            </div>
            <Button variant="ghost" size="sm" onClick={logout}><LogOut size={14}/><span>退出</span></Button>
          </div>
        </header>
        <main className="main-content"><Outlet/></main>
        <footer className="workspace-footer">
          <span>和序 HIS · 门诊业务闭环</span>
          <span>本机演示 · 仅限虚构数据</span>
        </footer>
      </div>
    </div>
  );
}
