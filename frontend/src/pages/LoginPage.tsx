import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { StatusMessage } from '../components/StatusMessage';

export function LoginPage() {
  const { login, isLoading, error, clearError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setHasSubmitted(true); clearError();
    try { await login(username.trim(), password); const from = (location.state as { from?: string } | null)?.from || '/'; navigate(from, { replace: true }); }
    catch { /* AuthContext exposes a user-facing error. */ }
  }

  return <main className="login-shell"><section className="login-intro"><p className="eyebrow">医院信息系统 · 课程设计</p><h1>从挂号到发药，<br />让每一步都可追溯。</h1><p>面向门诊业务闭环的演示工作台。真实数据由后端服务提供，权限和审计在接口层统一校验。</p><div className="flow-strip"><span>挂号</span><i>→</i><span>处方</span><i>→</i><span>收费</span><i>→</i><span>发药</span></div></section><section className="login-card" aria-labelledby="login-title"><div className="card-heading"><span className="brand-mark">HIS</span><div><p className="eyebrow">安全登录</p><h2 id="login-title">进入工作台</h2></div></div><form onSubmit={handleSubmit}><label htmlFor="username">用户名</label><input id="username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required maxLength={64} placeholder="请输入演示账号" /><label htmlFor="password">密码</label><input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required maxLength={128} placeholder="请输入密码" />{hasSubmitted && error ? <StatusMessage tone="error" title="登录未完成">{error}</StatusMessage> : null}<button className="button button-primary button-full" type="submit" disabled={isLoading}>{isLoading ? '正在验证…' : '登录工作台'}</button></form><p className="login-footnote">API 地址：<code>{import.meta.env.VITE_API_BASE_URL || '/api'}</code></p></section></main>;
}
