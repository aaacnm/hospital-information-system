import {Button} from '../components/ui/button';
import {NativeSelect} from '../components/ui/native-select';
import {Input} from '../components/ui/input';
import {Modal} from '../components/Modal';
import {StateBadge} from '../components/StateBadge';
import {formatTime, localDay, useData} from '../api/hooks';
import {useState, type FormEvent} from 'react';
import {apiClient} from '../api/client';
import {useAuth} from '../auth/AuthContext';
import type {Account, Drug, PageData, Patient, Stock} from '../api/business';
import type {AuditLogPage} from '../api/types';
import {Empty, ErrorNotice, Field, Heading, Pager, Search, Table} from '../components/BusinessUI';
import {StatusMessage} from '../components/StatusMessage';

const roleLabels: Record<string, string> = {admin: '系统管理员', doctor: '门诊医生', cashier: '挂号收费员', pharmacist: '药房药师'};
const actionLabels: Record<string, string> = {
  login: '登录系统',
  'patient.create': '新建患者',
  'registration.create': '挂号',
  'registration.cancel': '取消挂号',
  'registration.start': '开始接诊',
  'prescription.create': '创建处方',
  'prescription.submit': '提交处方',
  'prescription.charge': '收费',
  'prescription.dispense': '发药',
  'prescription.refund': '退费',
  'drug.price.update': '药品调价',
  'drug.import': '药品导入',
  'stock.receive': '批次入库',
  'clinical.save': '保存诊疗文书',
  'report.export': '导出报表',
  'schedule.create': '创建排班',
  'user.status': '账号状态变更',
};

export function PatientsPage() {
  const {user} = useAuth();
  const showHistory = user?.roles.some(r => r === 'doctor' || r === 'admin');
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [version, setVersion] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const data = useData<PageData<Patient>>('/patient-list?page=' + page + '&keyword=' + encodeURIComponent(keyword), version);

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setError(null);
    setMessage('');
    try {
      await apiClient.post('/patients', Object.fromEntries(new FormData(form)));
      form.reset();
      setMessage('患者档案已创建，可以继续挂号。');
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title="患者档案" description="仅录入虚构演示信息。身份证与手机号由服务端脱敏后保存和显示。"/>
      <Search onSearch={v => {setKeyword(v); setPage(1);}}/>
      <ErrorNotice error={error || data.error}/>
      {message && <StatusMessage tone="success" title="患者已建档">{message}</StatusMessage>}
      <Table headers={['患者编号', '姓名', '性别', '证件（脱敏）', '电话（脱敏）', ...(showHistory ? ['操作'] : [])]} loading={data.loading}>
        {data.data?.items.map(p => (
          <tr key={p.id}>
            <td className="mono-code">{p.patient_no}</td>
            <td><strong>{p.name}</strong></td>
            <td>{p.gender || '—'}</td>
            <td>{p.id_no_masked || '—'}</td>
            <td>{p.phone || '—'}</td>
            {showHistory && <td><a className="text-action" href={'/patients/' + p.id + '/timeline'}>查看就诊时间线</a></td>}
          </tr>
        ))}
      </Table>
      <Empty visible={!data.loading && data.data?.items.length === 0} title="还没有患者档案"/>
      <Pager data={data.data} page={page} setPage={setPage}/>
      <details className="action-panel">
        <summary>新增患者</summary>
        <form className="form-panel" onSubmit={create}>
          <Field label="患者编号"><Input name="patient_no" required maxLength={32}/></Field>
          <Field label="姓名"><Input name="name" required maxLength={80}/></Field>
          <Field label="性别"><NativeSelect name="gender"><option>男</option><option>女</option><option>未知</option></NativeSelect></Field>
          <Field label="演示证件号"><Input name="id_no_masked" maxLength={32}/></Field>
          <Field label="演示电话"><Input name="phone" maxLength={32}/></Field>
          <Button disabled={busy}>{busy ? '保存中…' : '保存患者'}</Button>
        </form>
      </details>
    </section>
  );
}

export function DrugsPage() {
  const {user} = useAuth();
  const admin = Boolean(user?.roles.includes('admin'));
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [version, setVersion] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Drug | null>(null);
  const [price, setPrice] = useState('');
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [message, setMessage] = useState('');
  const list = useData<PageData<Drug>>('/drug-list?page=' + page + '&keyword=' + encodeURIComponent(keyword), version);

  async function view(drug: Drug) {
    setSelected(drug);
    setPrice(drug.unit_price);
    setError(null);
    try {
      setStocks(await apiClient.get<Stock[]>('/drugs/' + drug.id + '/stocks'));
    } catch (r) {
      setError(r);
    }
  }

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setBusy(true);
    setError(null);
    try {
      await apiClient.post('/drugs', {...data, stock_qty: Number(data.stock_qty)});
      form.reset();
      setVersion(v => v + 1);
      setMessage('药品已建档，可以继续入库或开方。');
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  async function patch() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await apiClient.patch('/drugs/' + selected.id + '/price', {unit_price: price});
      setVersion(v => v + 1);
      setMessage('价格已更新；既有处方价格快照保持不变。');
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  async function receive(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selected) return;
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    setBusy(true);
    setError(null);
    try {
      await apiClient.post('/drugs/' + selected.id + '/stocks', {...data, quantity: Number(data.quantity)});
      form.reset();
      await view(selected);
      setVersion(v => v + 1);
      setMessage('批次入库成功，库存已经更新。');
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title="药品与批次库存" description="通用名、商品名、规格、剂型、医保类别统一管理。收费按未过期批次先到期先出库。"/>
      <Search placeholder="通用名或商品名" onSearch={v => {setKeyword(v); setPage(1);}}/>
      <ErrorNotice error={error || list.error}/>
      {message && <StatusMessage tone="success" title="库存已更新">{message}</StatusMessage>}
      <Table headers={['通用名 / 商品名', '规格', '剂型', '医保类别', '单价', '总库存', '可用库存', '操作']} loading={list.loading}>
        {list.data?.items.map(d => (
          <tr key={d.id}>
            <td><strong>{d.generic_name}</strong><small className="cell-sub">{d.trade_name || '—'}</small></td>
            <td>{d.specification}</td>
            <td>{d.dosage_form}</td>
            <td>{d.insurance_type || '—'}</td>
            <td className="money-text">¥{d.unit_price}</td>
            <td>{d.stock_qty}</td>
            <td><strong className={(d.available_stock ?? d.stock_qty) <= 10 ? 'danger-text' : 'money-text'}>{d.available_stock ?? d.stock_qty}</strong></td>
            <td><Button onClick={() => view(d)} variant="outline">批次与维护</Button></td>
          </tr>
        ))}
      </Table>
      <Empty visible={!list.loading && list.data?.items.length === 0} title="没有匹配的药品"/>
      <Pager data={list.data} page={page} setPage={setPage}/>

      {selected && (
        <div className="action-panel">
          <div className="history-entry-heading"><h2>{selected.generic_name} · 库存批次</h2><Button variant="ghost" size="sm" onClick={() => setSelected(null)}>收起</Button></div>
          <Table headers={['批次', '数量', '有效期']}>
            {stocks.map(s => (
              <tr key={s.id}>
                <td className="mono-code">{s.batch_no}</td>
                <td>{s.quantity}</td>
                <td>{s.expiry_date}{s.expiry_date <= localDay() && <span className="cell-sub" style={{color: '#c26059'}}>已过期，不可发出</span>}</td>
              </tr>
            ))}
          </Table>
          <Empty visible={stocks.length === 0} title="这个药品还没有批次库存"/>
          {admin && (
            <div className="filter-bar">
              <Field label="新单价"><Input type="number" min="0.01" step="0.01" value={price} onChange={e => setPrice(e.target.value)}/></Field>
              <Button onClick={patch} disabled={busy} variant="secondary">更新价格</Button>
            </div>
          )}
          <form className="form-panel" onSubmit={receive}>
            <Field label="入库批号"><Input name="batch_no" required maxLength={64}/></Field>
            <Field label="入库数量"><Input name="quantity" type="number" min="1" max="1000000" required/></Field>
            <Field label="有效期"><Input name="expiry_date" type="date" min={localDay()} required/></Field>
            <Button disabled={busy}>批次入库</Button>
          </form>
        </div>
      )}

      <details className="action-panel">
        <summary>新增药品档案</summary>
        <form className="form-panel" onSubmit={create}>
          {[['generic_name', '通用名'], ['trade_name', '商品名'], ['specification', '规格'], ['dosage_form', '剂型'], ['insurance_type', '医保类别']].map(([name, label]) => <Field key={name} label={label}><Input name={name} required maxLength={name === 'dosage_form' || name === 'insurance_type' ? 40 : 120}/></Field>)}
          <Field label="单价"><Input name="unit_price" type="number" step="0.01" min="0.01" required/></Field>
          <Field label="初始库存"><Input name="stock_qty" type="number" min="0" max="1000000" defaultValue="0" required/></Field>
          <Field label="初始批次有效期"><Input name="expiry_date" type="date" min={localDay()} required/></Field>
          <Button disabled={busy}>保存药品</Button>
        </form>
      </details>
    </section>
  );
}

interface ImportResult {
  total: number;
  success: number;
  failure: number;
  errors: {row: number; reason: string}[];
}

export function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const body = new FormData();
      body.set('file', file);
      setResult(await apiClient.upload<ImportResult>('/drugs/import', body));
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title="药品 CSV 导入" description="支持 UTF-8 / GBK，每次不超过 2 MB、5000 行。合法行入库，错误行保留行号和原因；已存在的药品不重复创建。"/>
      <p><a className="button button-secondary" href="/api/import-template" download>下载 CSV 模板</a></p>
      <form className="form-panel" onSubmit={submit}>
        <Field label="CSV 文件"><Input type="file" accept=".csv" onChange={e => setFile(e.target.files?.[0] || null)} required/></Field>
        <Button disabled={busy}>{busy ? '导入中…' : '开始导入'}</Button>
      </form>
      <ErrorNotice error={error}/>
      {result && (
        <>
          <StatusMessage title="导入结果">总计 {result.total} 行，成功 {result.success} 行，失败 {result.failure} 行。</StatusMessage>
          <Table headers={['行号', '失败原因']}>
            {result.errors.map(r => <tr key={r.row}><td>{r.row}</td><td className="wrap-cell">{r.reason}</td></tr>)}
          </Table>
        </>
      )}
    </section>
  );
}

export function AuditLogsPage() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState('');
  const [userId, setUserId] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [version, setVersion] = useState(0);
  const accounts = useData<Account[]>('/users');
  const accountNames = new Map<number, string>((accounts.data ?? []).map(a => [a.id, a.display_name] as [number, string]));
  const query = new URLSearchParams({page: String(page)});
  if (action) query.set('action', action);
  if (userId) query.set('user_id', userId);
  if (start) query.set('start_date', start);
  if (end) query.set('end_date', end);
  const result = useData<AuditLogPage>('/audit-logs?' + query.toString(), version);

  return (
    <section className="page-section">
      <Heading title="审计日志" description="按操作人、动作和北京时间日期筛选。收费记录保留库存变化与批次分配。"/>
      <form className="filter-bar" onSubmit={e => {e.preventDefault(); setVersion(v => v + 1);}}>
        <Field label="操作人"><NativeSelect value={userId} onChange={e => {setUserId(e.target.value); setPage(1);}}><option value="">全部</option>{accounts.data?.map(a => <option key={a.id} value={a.id}>{a.display_name}</option>)}</NativeSelect></Field>
        <Field label="动作"><NativeSelect value={action} onChange={e => {setAction(e.target.value); setPage(1);}}><option value="">全部</option>{Object.keys(actionLabels).map(a => <option key={a} value={a}>{actionLabels[a]}</option>)}</NativeSelect></Field>
        <Field label="开始日期"><Input type="date" value={start} onChange={e => {setStart(e.target.value); setPage(1);}}/></Field>
        <Field label="结束日期"><Input type="date" value={end} onChange={e => {setEnd(e.target.value); setPage(1);}}/></Field>
        <Button>刷新日志</Button>
      </form>
      <ErrorNotice error={result.error || accounts.error}/>
      <Table headers={['时间', '操作人', '动作', '对象', 'IP', '变更详情']} loading={result.loading}>
        {result.data?.items.map(log => (
          <tr key={log.id}>
            <td>{formatTime(log.created_at)}</td>
            <td>{accountNames.get(log.user_id ?? -1) || log.user_id}</td>
            <td>{actionLabels[log.action] || log.action}<small className="cell-sub">{log.action}</small></td>
            <td>{log.resource_type} #{log.resource_id}</td>
            <td>{log.ip || '—'}</td>
            <td><details><summary>查看</summary><pre className="audit-detail">操作前：{log.before_json || '—'}{'\n'}操作后：{log.after_json || '—'}</pre></details></td>
          </tr>
        ))}
      </Table>
      <Empty visible={!result.loading && result.data?.items.length === 0} title="没有符合条件的审计记录"/>
      <Pager data={result.data} page={page} setPage={setPage}/>
    </section>
  );
}

export function AccountsPage() {
  const [version, setVersion] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState<Account | null>(null);
  const data = useData<Account[]>('/users', version);

  async function change() {
    if (!target) return;
    setBusy(true);
    setError(null);
    setMessage('');
    try {
      const next = target.status === 'active' ? 'disabled' : 'active';
      await apiClient.patch('/users/' + target.id, {status: next});
      setMessage(target.display_name + ' 已' + (next === 'active' ? '启用' : '禁用') + '。');
      setTarget(null);
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title="账号与角色" description="四类角色按职责划分。禁用账号不能登录，已有凭证也无法继续访问业务接口。"/>
      <ErrorNotice error={error || data.error}/>
      {message && <StatusMessage tone="success" title="账号状态已更新">{message}</StatusMessage>}
      <Table headers={['账号', '名称', '角色', '状态', '操作']} loading={data.loading}>
        {data.data?.map(a => (
          <tr key={a.id}>
            <td className="mono-code">{a.username}</td>
            <td><strong>{a.display_name}</strong></td>
            <td>{roleLabels[a.role] || a.role}</td>
            <td><StateBadge value={a.status === 'active' ? '启用' : '禁用'}/></td>
            <td><Button disabled={busy || a.role === 'admin'} onClick={() => setTarget(a)} variant="outline">{a.status === 'active' ? '禁用' : '启用'}</Button></td>
          </tr>
        ))}
      </Table>
      <Empty visible={!data.loading && data.data?.length === 0} title="没有账号记录"/>

      <Modal
        open={Boolean(target)}
        title={target?.status === 'active' ? '禁用这个账号？' : '启用这个账号？'}
        subtitle="账号状态变化会立即生效，并写入审计日志。"
        onClose={() => setTarget(null)}
        footer={<>
          <Button variant="outline" onClick={() => setTarget(null)}>先不改</Button>
          <Button onClick={change} disabled={busy}>{busy ? '处理中…' : target?.status === 'active' ? '确认禁用' : '确认启用'}</Button>
        </>}
      >
        {target && <p className="modal-copy">{target.display_name}（{target.username}）当前角色为{roleLabels[target.role] || target.role}。</p>}
      </Modal>
    </section>
  );
}

export function PasswordPage() {
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setError(null);
    try {
      await apiClient.post('/auth/password', Object.fromEntries(new FormData(form)));
      setDone(true);
      form.reset();
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title="修改密码" description="本机演示也应保管好账号，切勿在共享环境沿用公开演示密码。"/>
      <form className="form-panel" onSubmit={submit}>
        <Field label="当前密码"><Input type="password" name="old_password" required autoComplete="current-password"/></Field>
        <Field label="新密码"><Input type="password" name="new_password" minLength={8} maxLength={64} required autoComplete="new-password"/></Field>
        <Button disabled={busy}>{busy ? '更新中…' : '更新密码'}</Button>
      </form>
      <ErrorNotice error={error}/>
      {done && <StatusMessage tone="success" title="密码已更新"/>}
    </section>
  );
}
