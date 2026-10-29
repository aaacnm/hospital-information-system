import {useState, type FormEvent} from 'react';
import {useNavigate} from 'react-router-dom';
import {Activity, ArrowRight, LockKeyhole, Pill, ShieldCheck, Sparkles, Stethoscope, UsersRound} from 'lucide-react';
import {useAuth} from '../auth/AuthContext';
import {StatusMessage} from '../components/StatusMessage';
import {Button} from '../components/ui/button';
import {Input} from '../components/ui/input';
import {Badge} from '../components/ui/badge';
import {Card, CardContent} from '../components/ui/card';

export function LoginPage() {
  const {login, isLoading, error, clearError} = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [hasSubmitted, setHasSubmitted] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setHasSubmitted(true);
    clearError();
    try {
      await login(username.trim(), password);
      navigate('/', {replace: true});
    } catch {
      // AuthContext displays the login error.
    }
  }

  return (
    <main className="login-shell">
      <header className="login-nav">
        <div className="login-brand">
          <span className="brand-mark"><Activity size={19}/></span>
          <strong>和序 HIS</strong>
          <span className="login-brand-sub">门诊业务管理系统</span>
        </div>
        <Badge variant="outline" className="login-badge"><span className="tiny-dot"/>本机演示 · 虚构数据</Badge>
      </header>

      <section className="login-hero">
        <Badge variant="outline" className="login-eyebrow"><Sparkles size={12}/>门诊业务一体化工作台</Badge>
        <h1>让门诊业务<br/><span>清晰而有序。</span></h1>
        <p>连接患者、医生、收费与药房。<br/>从一次挂号开始，让每一步都清楚、可靠。</p>
      </section>

      <Card className="login-card">
        <CardContent className="p-0">
          <div className="login-card-head">
            <div className="login-lock"><LockKeyhole size={19}/></div>
            <div>
              <h2 id="login-title">登录工作台</h2>
              <p>使用演示账号，或输入你自己的账号。</p>
            </div>
          </div>
          <form aria-labelledby="login-title" onSubmit={submit}>
            <label htmlFor="username">用户名</label>
            <Input id="username" name="username" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required maxLength={64} placeholder="请输入账号"/>
            <label htmlFor="password">密码</label>
            <Input id="password" name="password" type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required maxLength={128} placeholder="请输入密码"/>
            {hasSubmitted && error && <StatusMessage tone="error" title="登录未完成">{error}</StatusMessage>}
            <Button className="button-full" disabled={isLoading}>
              {isLoading ? '正在验证…' : '登录工作台'}
              <ArrowRight size={16}/>
            </Button>
          </form>
          <div className="demo-account-section">
            <div className="demo-account-title"><span>选择演示身份</span><small>自动填入演示账号</small></div>
            <div className="demo-accounts">
              {[{name: '管理员', account: 'admin'}, {name: '医生', account: 'doctor'}, {name: '收费员', account: 'cashier'}, {name: '药师', account: 'pharmacist'}].map(a => (
                <Button key={a.account} type="button" variant="outline" size="sm" onClick={() => {setUsername(a.account + '.demo'); setPassword('Demo123!'); clearError();}}>
                  {a.name}
                </Button>
              ))}
            </div>
          </div>
          <p className="login-footnote"><ShieldCheck size={13}/>请勿录入真实患者身份和临床信息</p>
        </CardContent>
      </Card>

      <div className="login-features">
        {[
          {icon: UsersRound, title: '患者与号源', text: '建档、排班、挂号一条线'},
          {icon: Stethoscope, title: '接诊与开方', text: '文书、诊断、处方自动划价'},
          {icon: Pill, title: '收费与发药', text: '批次库存与退费全程留痕'},
        ].map(item => (
          <div className="login-feature" key={item.title}>
            <item.icon size={18} strokeWidth={1.7}/>
            <div><strong>{item.title}</strong><small>{item.text}</small></div>
          </div>
        ))}
      </div>
      <p className="login-footer">和序 HIS · 门诊业务闭环系统 · 仅用于课程演示</p>
    </main>
  );
}
