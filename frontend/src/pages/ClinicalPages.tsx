import {StateBadge} from '../components/StateBadge';
import {Button} from '../components/ui/button';
import {NativeSelect} from '../components/ui/native-select';
import {Input} from '../components/ui/input';
import { localDay, useData } from '../api/hooks';
import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import type { Directory, Drug, PageData, Patient, Visit } from '../api/business';
import type { Charge, Dispense, Prescription, PrescriptionItemInput, Registration, Schedule } from '../api/types';
import { Empty, ErrorNotice, Field, Heading, Pager, Search, Table } from '../components/BusinessUI';
import { StatusMessage } from '../components/StatusMessage';
export function SchedulesPage() {
    const { user } = useAuth();
    const [date, setDate] = useState(localDay());
    const [dept, setDept] = useState('');
    const [version, setVersion] = useState(0);
    const [error, setError] = useState<unknown>(null);
    const [busy, setBusy] = useState(false);
    const directory = useData<Directory>('/directory');
    const result = useData<Schedule[]>('/schedules?date=' + date + (dept ? '&dept_id=' + dept : ''), version);
    async function create(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        const d = Object.fromEntries(new FormData(e.currentTarget));
        setBusy(true);
        setError(null);
        try {
            await apiClient.post('/schedules', { doctor_id: Number(d.doctor_id), visit_date: date, period: d.period, total_quota: Number(d.total_quota) });
            setVersion(v => v + 1);
        }
        catch (r) {
            setError(r);
        }
        finally {
            setBusy(false);
        }
    }
    return <section className="page-section"><Heading title="排班与号源" description="按科室与就诊日期查号源，挂号后剩余数量实时更新。"/><form className="filter-bar" onSubmit={e => { e.preventDefault(); setVersion(v => v + 1); }}><Field label="就诊日期"><Input type="date" value={date} onChange={e => setDate(e.target.value)} required/></Field><Field label="科室"><NativeSelect value={dept} onChange={e => setDept(e.target.value)}><option value="">全部科室</option>{directory.data?.departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</NativeSelect></Field><Button>查询排班</Button></form><ErrorNotice error={error || result.error || directory.error}/><Table headers={['科室', '医生', '日期', '时段', '总号源', '剩余号源']}>{result.data?.map(s => <tr key={s.id}><td>{s.department_name}</td><td>{s.doctor_name}</td><td>{s.visit_date}</td><td>{s.period}</td><td>{s.total_quota}</td><td><strong>{s.remain_quota}</strong></td></tr>)}</Table><Empty visible={result.data?.length === 0}/>
 {user?.roles.includes('admin') && <details className="action-panel"><summary>新增医生排班</summary><form className="filter-bar" onSubmit={create}><Field label="医生"><NativeSelect name="doctor_id" required><option value="">请选择</option>{directory.data?.doctors.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</NativeSelect></Field><Field label="时段"><NativeSelect name="period"><option>上午</option><option>下午</option></NativeSelect></Field><Field label="总号源"><Input name="total_quota" type="number" min="1" max="1000" defaultValue="20" required/></Field><Button disabled={busy}>创建所选日期排班</Button></form></details>}</section>;
}
export function RegistrationsPage() {
    const { user } = useAuth();
    const doctor = user?.roles.includes('doctor');
    const [date, setDate] = useState(localDay());
    const [dept, setDept] = useState('');
    const [keyword, setKeyword] = useState('');
    const [patient, setPatient] = useState('');
    const [schedule, setSchedule] = useState('');
    const [page, setPage] = useState(1);
    const [version, setVersion] = useState(0);
    const [error, setError] = useState<unknown>(null);
    const [busy, setBusy] = useState(false);
    const [created, setCreated] = useState<Registration | null>(null);
    const directory = useData<Directory>('/directory');
    const patients = useData<PageData<Patient>>('/patient-list?keyword=' + encodeURIComponent(keyword));
    const schedules = useData<Schedule[]>('/schedules?date=' + date + (dept ? '&dept_id=' + dept : ''), version);
    const visits = useData<PageData<Visit>>('/registrations?page=' + page, version);
    async function submit(e: FormEvent) {
        e.preventDefault();
        setBusy(true);
        setError(null);
        setCreated(null);
        try {
            setCreated(await apiClient.post<Registration>('/registrations', { patient_id: Number(patient), schedule_id: Number(schedule) }));
            setVersion(v => v + 1);
        }
        catch (r) {
            setError(r);
        }
        finally {
            setBusy(false);
        }
    }
    async function cancel(id: number) {
        setBusy(true);
        setError(null);
        try {
            await apiClient.post('/registrations/' + id + '/cancel');
            setVersion(v => v + 1);
        }
        catch (r) {
            setError(r);
        }
        finally {
            setBusy(false);
        }
    }
    return <section className="page-section"><Heading title={doctor ? '我的待诊患者' : '挂号管理'} description="患者、医生、号源与排队号关联保存。取消未接诊挂号会释放号源。"/>
 {!doctor && <><Search onSearch={setKeyword}/><form className="form-panel" onSubmit={submit}><Field label="患者"><NativeSelect value={patient} onChange={e => setPatient(e.target.value)} required><option value="">请选择患者</option>{patients.data?.items.map(p => <option key={p.id} value={p.id}>{p.name} · {p.patient_no}</option>)}</NativeSelect></Field><Field label="就诊日期"><Input type="date" value={date} onChange={e => { setDate(e.target.value); setSchedule(''); }} required/></Field><Field label="科室"><NativeSelect value={dept} onChange={e => { setDept(e.target.value); setSchedule(''); }}><option value="">全部科室</option>{directory.data?.departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</NativeSelect></Field><Field label="医生与时段"><NativeSelect value={schedule} onChange={e => setSchedule(e.target.value)} required><option value="">请选择排班</option>{schedules.data?.map(s => <option key={s.id} value={s.id} disabled={s.remain_quota === 0}>{s.doctor_name} · {s.period} · 余号 {s.remain_quota}</option>)}</NativeSelect></Field><Button disabled={busy}>确认挂号</Button></form></>}
 <ErrorNotice error={error || visits.error || patients.error || schedules.error}/>{created && <StatusMessage tone="success" title="挂号成功">排队号 {created.queue_no}，状态 {created.status}。号源已扣减。</StatusMessage>}
 <Table headers={['患者', '患者编号', '医生', '就诊日期', '排队号', '状态', '操作']}>{visits.data?.items.map(v => <tr key={v.id}><td>{v.patient_name}</td><td>{v.patient_no}</td><td>{v.doctor_name}</td><td>{v.visit_date} {v.period}</td><td>{v.queue_no}</td><td><StateBadge value={v.status}/></td><td>{doctor && !v.prescription_id && v.status === '候诊' ? <Link className="button button-primary" to={'/prescriptions?registration=' + v.id}>接诊开方</Link> : !doctor && v.status === '候诊' && !v.prescription_id ? <Button onClick={() => cancel(v.id)} disabled={busy} variant="outline">取消挂号</Button> : '—'}</td></tr>)}</Table><Empty visible={visits.data?.items.length === 0}/><Pager data={visits.data} page={page} setPage={setPage}/></section>;
}
export function PrescriptionDetail({ rx }: {
    rx: Prescription;
}) {
    return <div className="result-panel"><h2>处方 #{rx.id} · {rx.patient_name}</h2><p>{rx.diagnosis_code} · {rx.diagnosis_name} · <strong>{rx.status}</strong></p><Table headers={['药品', '规格', '数量', '单价', '用法', '频次', '天数']}>{rx.items.map((item, i) => <tr key={i}><td>{item.drug_name}</td><td>{item.specification}</td><td>{item.quantity}</td><td>¥{item.unit_price}</td><td>{item.dosage || '—'}</td><td>{item.frequency || '—'}</td><td>{item.days || '—'}</td></tr>)}</Table><p className="amount">应付金额 ¥ {rx.total_amount}</p></div>;
}
export function PrescriptionsPage() {
    const { user } = useAuth();
    const canCreate = user?.roles.includes('doctor');
    const [params] = useSearchParams();
    const [editing, setEditing] = useState<number | null>(null);
    const [registration, setRegistration] = useState(params.get('registration') || '');
    const [code, setCode] = useState('J06.9');
    const [diagnosis, setDiagnosis] = useState('演示诊断');
    const [items, setItems] = useState<PrescriptionItemInput[]>([{ drug_id: 0, quantity: 1, dosage: '每次1片', frequency: '每日2次', days: 1 }]);
    const [keyword, setKeyword] = useState('');
    const [version, setVersion] = useState(0);
    const [page, setPage] = useState(1);
    const [error, setError] = useState<unknown>(null);
    const [busy, setBusy] = useState(false);
    const [selected, setSelected] = useState<Prescription | null>(null);
    const visits = useData<PageData<Visit>>(canCreate ? '/registrations?page_size=100' : null, version);
    const drugs = useData<PageData<Drug>>('/drug-list?keyword=' + encodeURIComponent(keyword));
    const list = useData<PageData<Prescription>>('/prescriptions?page=' + page, version);
    function edit(index: number, value: Partial<PrescriptionItemInput>) { setItems(rows => rows.map((item, i) => i === index ? { ...item, ...value } : item)); }
    async function create(e: FormEvent) {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
            const payload = { registration_id: Number(registration), diagnosis_code: code, diagnosis_name: diagnosis, items };
            setSelected(editing ? await apiClient.patch<Prescription>('/prescriptions/' + editing, payload) : await apiClient.post<Prescription>('/prescriptions', payload));
            setEditing(null);
            setRegistration('');
            setVersion(v => v + 1);
        }
        catch (r) {
            setError(r);
        }
        finally {
            setBusy(false);
        }
    }
    async function submit(rx: Prescription) {
        setBusy(true);
        setError(null);
        try {
            setSelected(await apiClient.post<Prescription>('/prescriptions/' + rx.id + '/submit'));
            setVersion(v => v + 1);
        }
        catch (r) {
            setError(r);
        }
        finally {
            setBusy(false);
        }
    }
    return <section className="page-section"><Heading title="处方管理" description="医生从本人挂号患者开方。金额由后端自动计算，处方单价固定；改价只影响新处方。"/>
 {canCreate && <details className="action-panel" open={Boolean(params.get('registration')) || Boolean(editing)}><summary>开立新处方</summary><Search onSearch={setKeyword} placeholder="搜索药品通用名或商品名"/><form onSubmit={create}><div className="form-panel"><Field label="待诊患者"><NativeSelect value={registration} onChange={e => setRegistration(e.target.value)} required><option value="">请选择</option>{visits.data?.items.filter(v => (!v.prescription_id && v.status === '候诊') || v.id === Number(registration)).map(v => <option key={v.id} value={v.id}>{v.patient_name} · {v.visit_date} · 排队 {v.queue_no}</option>)}</NativeSelect></Field><Field label="诊断编码"><Input value={code} onChange={e => setCode(e.target.value)} maxLength={32} required/></Field><Field label="诊断名称"><Input value={diagnosis} onChange={e => setDiagnosis(e.target.value)} maxLength={120} required/></Field></div>
 {items.map((item, i) => <div className="prescription-row" key={i}><Field label={'药品 ' + (i + 1)}><NativeSelect value={item.drug_id || ''} onChange={e => edit(i, { drug_id: Number(e.target.value) })} required><option value="">请选择药品</option>{drugs.data?.items.map(d => <option key={d.id} value={d.id}>{d.generic_name} · {d.specification} · ¥{d.unit_price} · 库存 {d.stock_qty}</option>)}</NativeSelect></Field><Field label={'数量 ' + (i + 1)}><Input type="number" min="1" max="1000" value={item.quantity} onChange={e => edit(i, { quantity: Number(e.target.value) })} required/></Field><Field label={'用法 ' + (i + 1)}><Input value={item.dosage} onChange={e => edit(i, { dosage: e.target.value })} maxLength={120}/></Field><Field label={'频次 ' + (i + 1)}><Input value={item.frequency} onChange={e => edit(i, { frequency: e.target.value })} maxLength={80}/></Field><Field label={'天数 ' + (i + 1)}><Input type="number" min="1" max="365" value={item.days} onChange={e => edit(i, { days: Number(e.target.value) })}/></Field><Button type="button" disabled={items.length === 1} onClick={() => setItems(rows => rows.filter((_, index) => index !== i))} variant="outline">移除</Button></div>)}
 <div className="toolbar"><Button type="button" disabled={items.length >= 50} onClick={() => setItems(rows => [...rows, { drug_id: 0, quantity: 1, dosage: '', frequency: '', days: 1 }])} variant="secondary">添加药品</Button><Button disabled={busy}>{editing ? '保存草稿并划价' : '创建草稿并划价'}</Button></div></form></details>}
 <ErrorNotice error={error || list.error || drugs.error}/><Table headers={['患者', '诊断', '金额', '状态', '操作']}>{list.data?.items.map(rx => <tr key={rx.id}><td>{rx.patient_name}</td><td>{rx.diagnosis_name}</td><td>¥{rx.total_amount}</td><td><StateBadge value={rx.status}/></td><td><Button onClick={() => setSelected(rx)} variant="outline">查看明细</Button>{canCreate && rx.status === '草稿' && <><Button onClick={() => { setEditing(rx.id); setRegistration(String(rx.registration_id)); setCode(rx.diagnosis_code || ''); setDiagnosis(rx.diagnosis_name || ''); setItems(rx.items.map(item => ({ drug_id: item.drug_id, quantity: item.quantity, dosage: item.dosage || '', frequency: item.frequency || '', days: item.days || 1 }))); window.scrollTo(0, 0); }} variant="outline">编辑草稿</Button><Button disabled={busy} onClick={() => submit(rx)}>提交为待收费</Button></>}</td></tr>)}</Table><Empty visible={list.data?.items.length === 0}/><Pager data={list.data} page={page} setPage={setPage}/>{selected && <><PrescriptionDetail rx={selected}/>{canCreate && selected.status === '草稿' && <Button disabled={busy} onClick={() => submit(selected)}>提交为待收费</Button>}</>}</section>;
}
function QueuePage({ dispense = false }: {
    dispense?: boolean;
}) {
    const [page, setPage] = useState(1);
    const [version, setVersion] = useState(0);
    const [selected, setSelected] = useState<Prescription | null>(null);
    const [error, setError] = useState<unknown>(null);
    const [busy, setBusy] = useState(false);
    const [receipt, setReceipt] = useState<Charge | Dispense | null>(null);
    const target = dispense ? '已收费' : '待收费';
    const list = useData<PageData<Prescription>>('/prescriptions?status=' + encodeURIComponent(target) + '&page=' + page, version);
    async function action() {
        if (!selected)
            return;
        setBusy(true);
        setError(null);
        setReceipt(null);
        try {
            setReceipt(await apiClient.post<Charge | Dispense>('/prescriptions/' + selected.id + (dispense ? '/dispense' : '/charge')));
            setSelected(null);
            setVersion(v => v + 1);
        }
        catch (r) {
            setError(r);
        }
        finally {
            setBusy(false);
        }
    }
    return <section className="page-section"><Heading title={dispense ? '药房发药' : '收费台'} description={dispense ? '核对患者与药品明细，确认后记录药师、时间和审计。本步骤不重复扣库存。' : '选择待收费处方，核对后端计算的金额后收费。任一药品库存不足，整笔操作回滚。'}/><Button onClick={() => setVersion(v => v + 1)} variant="secondary">刷新待办</Button><ErrorNotice error={error || list.error}/><Table headers={['患者', '患者编号', '诊断', '金额', '状态', '操作']}>{list.data?.items.map(rx => <tr key={rx.id}><td>{rx.patient_name}</td><td>{rx.patient_no}</td><td>{rx.diagnosis_name}</td><td>¥{rx.total_amount}</td><td><StateBadge value={rx.status}/></td><td><Button onClick={() => { setSelected(rx); setReceipt(null); }}>核对明细</Button></td></tr>)}</Table><Empty visible={list.data?.items.length === 0}/><Pager data={list.data} page={page} setPage={setPage}/>{selected && <><PrescriptionDetail rx={selected}/><Button onClick={action} disabled={busy}>{busy ? '处理中…' : dispense ? '确认发药' : '确认收费'}</Button></>}{receipt && <StatusMessage tone="success" title={dispense ? '发药成功' : '收费成功'}>处方 #{receipt.prescription_id} 已完成{dispense ? '发药' : '收费'}。{'amount' in receipt ? '金额 ¥ ' + receipt.amount : '发药记录已保存'}；审计可查询。</StatusMessage>}</section>;
}
export function BillingPage() { return <QueuePage />; }
export function DispensingPage() { return <QueuePage dispense/>; }
