import {ClinicalRecordEditor} from './ClinicalExtensions';
import {StateBadge} from '../components/StateBadge';
import {Modal} from '../components/Modal';
import {Button} from '../components/ui/button';
import {NativeSelect} from '../components/ui/native-select';
import {Input} from '../components/ui/input';
import {localDay, useData} from '../api/hooks';
import {useState, type FormEvent} from 'react';
import {Link, useSearchParams} from 'react-router-dom';
import {Printer, RotateCcw} from 'lucide-react';
import {apiClient} from '../api/client';
import {useAuth} from '../auth/AuthContext';
import type {Directory, Drug, PageData, Patient, Visit} from '../api/business';
import type {Charge, Dispense, Prescription, PrescriptionItemInput, Registration, Schedule} from '../api/types';
import {Empty, ErrorNotice, Field, Heading, Pager, Search, Table} from '../components/BusinessUI';
import {StatusMessage} from '../components/StatusMessage';

const prescriptionStatuses = [
  ['', '全部'],
  ['草稿', '草稿'],
  ['待收费', '待收费'],
  ['已收费', '已收费'],
  ['已发药', '已发药'],
  ['已退费', '已退费'],
];
const registrationStatuses = [['', '全部'], ['候诊', '候诊'], ['就诊中', '就诊中'], ['已完成', '已完成'], ['已取消', '已取消']];

export function SchedulesPage() {
  const {user} = useAuth();
  const [date, setDate] = useState(localDay());
  const [dept, setDept] = useState('');
  const [version, setVersion] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const directory = useData<Directory>('/directory');
  const result = useData<Schedule[]>('/schedules?date=' + date + (dept ? '&dept_id=' + dept : ''), version);

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const d = Object.fromEntries(new FormData(form));
    setBusy(true);
    setError(null);
    setMessage('');
    try {
      await apiClient.post('/schedules', {doctor_id: Number(d.doctor_id), visit_date: date, period: d.period, total_quota: Number(d.total_quota)});
      form.reset();
      setMessage('排班已创建，号源已准备就绪。');
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title="排班与号源" description="按科室与就诊日期查号源，挂号后剩余数量实时更新。"/>
      <form className="filter-bar" onSubmit={e => {e.preventDefault(); setVersion(v => v + 1);}}>
        <Field label="就诊日期"><Input type="date" value={date} onChange={e => setDate(e.target.value)} required/></Field>
        <Field label="科室"><NativeSelect value={dept} onChange={e => setDept(e.target.value)}><option value="">全部科室</option>{directory.data?.departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</NativeSelect></Field>
        <Button>查询排班</Button>
      </form>
      <ErrorNotice error={error || result.error || directory.error}/>
      {message && <StatusMessage tone="success" title="排班已更新">{message}</StatusMessage>}
      <Table headers={['科室', '医生', '日期', '时段', '总号源', '剩余号源']} loading={result.loading}>
        {result.data?.map(s => (
          <tr key={s.id}>
            <td>{s.department_name}</td>
            <td><strong>{s.doctor_name}</strong></td>
            <td>{s.visit_date}</td>
            <td>{s.period}</td>
            <td>{s.total_quota}</td>
            <td><strong className={s.remain_quota === 0 ? 'danger-text' : 'money-text'}>{s.remain_quota}</strong></td>
          </tr>
        ))}
      </Table>
      <Empty visible={!result.loading && result.data?.length === 0} title="这一天还没有排班"/>
      {user?.roles.includes('admin') && (
        <details className="action-panel">
          <summary>新增医生排班</summary>
          <form className="filter-bar" onSubmit={create}>
            <Field label="医生"><NativeSelect name="doctor_id" required><option value="">请选择</option>{directory.data?.doctors.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</NativeSelect></Field>
            <Field label="时段"><NativeSelect name="period"><option>上午</option><option>下午</option></NativeSelect></Field>
            <Field label="总号源"><Input name="total_quota" type="number" min="1" max="1000" defaultValue="20" required/></Field>
            <Button disabled={busy}>{busy ? '创建中…' : '创建所选日期排班'}</Button>
          </form>
        </details>
      )}
    </section>
  );
}

export function RegistrationsPage() {
  const {user} = useAuth();
  const doctor = Boolean(user?.roles.includes('doctor'));
  const [date, setDate] = useState(localDay());
  const [dept, setDept] = useState('');
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState('');
  const [patient, setPatient] = useState('');
  const [schedule, setSchedule] = useState('');
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<Registration | null>(null);
  const [cancelTarget, setCancelTarget] = useState<Visit | null>(null);
  const directory = useData<Directory>('/directory');
  const patients = useData<PageData<Patient>>('/patient-list?keyword=' + encodeURIComponent(keyword) + '&page_size=100');
  const schedules = useData<Schedule[]>('/schedules?date=' + date + (dept ? '&dept_id=' + dept : ''), version);
  const visits = useData<PageData<Visit>>(
    '/registrations?page=' + page
    + '&keyword=' + encodeURIComponent(keyword)
    + (status ? '&status=' + encodeURIComponent(status) : ''),
    version,
  );

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setCreated(null);
    setMessage('');
    try {
      setCreated(await apiClient.post<Registration>('/registrations', {patient_id: Number(patient), schedule_id: Number(schedule)}));
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!cancelTarget) return;
    setBusy(true);
    setError(null);
    try {
      await apiClient.post('/registrations/' + cancelTarget.id + '/cancel');
      setMessage('挂号已取消，号源已经释放。');
      setCancelTarget(null);
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title={doctor ? '我的待诊患者' : '挂号管理'} description="患者、医生、号源与排队号关联保存。取消未接诊挂号会释放号源。"/>
      <Search onSearch={v => {setKeyword(v); setPage(1);}}/>
      {!doctor && (
        <form className="form-panel" onSubmit={submit}>
          <Field label="患者"><NativeSelect value={patient} onChange={e => setPatient(e.target.value)} required><option value="">请选择患者</option>{patients.data?.items.map(p => <option key={p.id} value={p.id}>{p.name} · {p.patient_no}</option>)}</NativeSelect></Field>
          <Field label="就诊日期"><Input type="date" value={date} min={localDay()} onChange={e => {setDate(e.target.value); setSchedule('');}} required/></Field>
          <Field label="科室"><NativeSelect value={dept} onChange={e => {setDept(e.target.value); setSchedule('');}}><option value="">全部科室</option>{directory.data?.departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</NativeSelect></Field>
          <Field label="医生与时段"><NativeSelect value={schedule} onChange={e => setSchedule(e.target.value)} required><option value="">请选择排班</option>{schedules.data?.map(s => <option key={s.id} value={s.id} disabled={s.remain_quota === 0}>{s.doctor_name} · {s.period} · 余号 {s.remain_quota}</option>)}</NativeSelect></Field>
          <Button disabled={busy}>确认挂号</Button>
        </form>
      )}
      <ErrorNotice error={error || visits.error || patients.error || schedules.error}/>
      {created && <StatusMessage tone="success" title="挂号成功">排队号 {created.queue_no}，状态 {created.status}。号源已扣减。</StatusMessage>}
      {message && <StatusMessage tone="success" title="挂号已取消">{message}</StatusMessage>}
      <div className="toolbar">
        <div className="segmented-control">
          {registrationStatuses.map(([value, label]) => (
            <Button key={value} variant={status === value ? 'default' : 'ghost'} size="sm" onClick={() => {setStatus(value); setPage(1);}}>{label}</Button>
          ))}
        </div>
        <Button variant="outline" onClick={() => setVersion(v => v + 1)}><RotateCcw size={14}/>刷新</Button>
      </div>
      <Table headers={['患者', '患者编号', '医生', '就诊日期', '排队号', '状态', '操作']} loading={visits.loading}>
        {visits.data?.items.map(v => (
          <tr key={v.id}>
            <td><strong>{v.patient_name}</strong></td>
            <td>{v.patient_no}</td>
            <td>{v.doctor_name}</td>
            <td>{v.visit_date} {v.period}</td>
            <td>{v.queue_no}</td>
            <td><StateBadge value={v.status}/></td>
            <td>
              {doctor && !v.prescription_id && ['候诊', '就诊中'].includes(v.status)
                ? <Link className="button button-primary" to={'/prescriptions?registration=' + v.id}>接诊开方</Link>
                : !doctor && v.status === '候诊' && !v.prescription_id
                  ? <Button onClick={() => setCancelTarget(v)} disabled={busy} variant="outline">取消挂号</Button>
                  : '—'}
            </td>
          </tr>
        ))}
      </Table>
      <Empty visible={!visits.loading && visits.data?.items.length === 0} title="没有匹配的挂号记录"/>
      <Pager data={visits.data} page={page} setPage={setPage}/>

      <Modal
        open={Boolean(cancelTarget)}
        title="取消这次挂号？"
        subtitle="取消后号源会释放，患者需要重新挂号。"
        onClose={() => setCancelTarget(null)}
        footer={<>
          <Button variant="outline" onClick={() => setCancelTarget(null)}>保留挂号</Button>
          <Button onClick={cancel} disabled={busy}>{busy ? '正在取消…' : '确认取消挂号'}</Button>
        </>}
      >
        {cancelTarget && (
          <p className="modal-copy">
            {cancelTarget.patient_name} · {cancelTarget.visit_date} {cancelTarget.period} · 排队号 {cancelTarget.queue_no}。
            只有尚未开方的候诊挂号可以取消。
          </p>
        )}
      </Modal>
    </section>
  );
}

export function PrescriptionDetail({rx, embedded = false}: {rx: Prescription; embedded?: boolean}) {
  return (
    <div className="result-panel">
      {!embedded && (
        <div className="history-entry-heading">
          <div>
            <h2>处方 #{rx.id} · {rx.patient_name}</h2>
            <p>{rx.diagnosis_code || '未录入编码'} · {rx.diagnosis_name || '未录入诊断'}</p>
          </div>
          <StateBadge value={rx.status}/>
        </div>
      )}
      {embedded && (
        <div className="prescription-meta">
          <p>{rx.diagnosis_code || '未录入编码'} · {rx.diagnosis_name || '未录入诊断'}</p>
          <StateBadge value={rx.status}/>
        </div>
      )}
      <Table headers={['药品', '规格', '数量', '单价', '用法', '频次', '天数']}>
        {rx.items.map((item, i) => (
          <tr key={i}>
            <td>{item.drug_name}</td>
            <td>{item.specification}</td>
            <td>{item.quantity}</td>
            <td>¥{item.unit_price}</td>
            <td>{item.dosage || '—'}</td>
            <td>{item.frequency || '—'}</td>
            <td>{item.days || '—'}</td>
          </tr>
        ))}
      </Table>
      <p className="amount">应付金额 ¥ {rx.total_amount}</p>
      <a className="button button-secondary" href={'/print/prescriptions/' + rx.id}><Printer size={14}/>查看 / 打印处方笺</a>
    </div>
  );
}

export function PrescriptionsPage() {
  const {user} = useAuth();
  const canCreate = Boolean(user?.roles.includes('doctor'));
  const [params] = useSearchParams();
  const [editing, setEditing] = useState<number | null>(null);
  const [registration, setRegistration] = useState(params.get('registration') || '');
  const [code, setCode] = useState('J06.9');
  const [diagnosis, setDiagnosis] = useState('急性上呼吸道感染，未特指');
  const [diagnosisKeyword, setDiagnosisKeyword] = useState('');
  const [items, setItems] = useState<PrescriptionItemInput[]>([{drug_id: 0, quantity: 1, dosage: '每次1片', frequency: '每日2次', days: 1}]);
  const [drugKeyword, setDrugKeyword] = useState('');
  const [listKeyword, setListKeyword] = useState('');
  const [status, setStatus] = useState('');
  const [version, setVersion] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Prescription | null>(null);
  const diagnosisOptions = useData<{code: string; name: string}[]>('/diagnoses?keyword=' + encodeURIComponent(diagnosisKeyword));
  const visits = useData<PageData<Visit>>(canCreate ? '/registrations?page_size=100' : null, version);
  const drugs = useData<PageData<Drug>>('/drug-list?keyword=' + encodeURIComponent(drugKeyword) + '&page_size=100');
  const list = useData<PageData<Prescription>>(
    '/prescriptions?page=' + page
    + (status ? '&status=' + encodeURIComponent(status) : '')
    + '&keyword=' + encodeURIComponent(listKeyword),
    version,
  );
  const visibleStatuses = user?.roles.includes('doctor') || user?.roles.includes('admin')
    ? prescriptionStatuses
    : user?.roles.includes('cashier')
      ? prescriptionStatuses.filter(([value]) => value !== '草稿')
      : prescriptionStatuses.filter(([value]) => ['', '已收费', '已发药'].includes(value));

  function edit(index: number, value: Partial<PrescriptionItemInput>) {
    setItems(rows => rows.map((item, i) => i === index ? {...item, ...value} : item));
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {registration_id: Number(registration), diagnosis_code: code, diagnosis_name: diagnosis, items};
      setSelected(editing
        ? await apiClient.patch<Prescription>('/prescriptions/' + editing, payload)
        : await apiClient.post<Prescription>('/prescriptions', payload));
      setEditing(null);
      setRegistration('');
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  async function submit(rx: Prescription) {
    setBusy(true);
    setError(null);
    try {
      setSelected(await apiClient.post<Prescription>('/prescriptions/' + rx.id + '/submit'));
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-section">
      <Heading title="处方管理" description="医生从本人挂号患者开方。金额由后端自动计算，处方单价固定；改价只影响新处方。"/>
      {canCreate && (
        <details className="action-panel" open={Boolean(params.get('registration')) || Boolean(editing)}>
          <summary>诊疗记录与开方</summary>
          <ClinicalRecordEditor registrationId={Number(registration)} version={version}/>
          <Search onSearch={setDrugKeyword} placeholder="搜索药品通用名或商品名"/>
          <form onSubmit={create}>
            <div className="form-panel">
              <Field label="待诊患者"><NativeSelect value={registration} onChange={e => setRegistration(e.target.value)} required><option value="">请选择</option>{visits.data?.items.filter(v => (!v.prescription_id && ['候诊', '就诊中'].includes(v.status)) || v.id === Number(registration)).map(v => <option key={v.id} value={v.id}>{v.patient_name} · {v.visit_date} · 排队 {v.queue_no}</option>)}</NativeSelect></Field>
              <Field label="搜索常用诊断"><Input value={diagnosisKeyword} onChange={e => setDiagnosisKeyword(e.target.value)} placeholder="输入名称或 ICD-10 编码"/></Field>
              <Field label="常用诊断示例"><NativeSelect value={diagnosisOptions.data?.some(d => d.code === code) ? code : ''} onChange={e => {const d = diagnosisOptions.data?.find(d => d.code === e.target.value); if (d) {setCode(d.code); setDiagnosis(d.name);}}}><option value="">也可手动录入诊断</option>{diagnosisOptions.data?.map(d => <option key={d.code} value={d.code}>{d.code} · {d.name}</option>)}</NativeSelect></Field>
              <Field label="诊断编码"><Input value={code} onChange={e => setCode(e.target.value)} maxLength={32} required/></Field>
              <Field label="诊断名称"><Input value={diagnosis} onChange={e => setDiagnosis(e.target.value)} maxLength={120} required/></Field>
            </div>
            {items.map((item, i) => (
              <div className="prescription-row" key={i}>
                <Field label={'药品 ' + (i + 1)}><NativeSelect value={item.drug_id || ''} onChange={e => edit(i, {drug_id: Number(e.target.value)})} required><option value="">请选择药品</option>{drugs.data?.items.map(d => <option key={d.id} value={d.id} disabled={(d.available_stock ?? d.stock_qty) <= 0}>{d.generic_name} · {d.specification} · ¥{d.unit_price} · 可用 {d.available_stock ?? d.stock_qty}</option>)}</NativeSelect></Field>
                <Field label={'数量 ' + (i + 1)}><Input type="number" min="1" max="1000" value={item.quantity} onChange={e => edit(i, {quantity: Number(e.target.value)})} required/></Field>
                <Field label={'用法 ' + (i + 1)}><Input value={item.dosage} onChange={e => edit(i, {dosage: e.target.value})} maxLength={120}/></Field>
                <Field label={'频次 ' + (i + 1)}><Input value={item.frequency} onChange={e => edit(i, {frequency: e.target.value})} maxLength={80}/></Field>
                <Field label={'天数 ' + (i + 1)}><Input type="number" min="1" max="365" value={item.days} onChange={e => edit(i, {days: Number(e.target.value)})}/></Field>
                <Button type="button" disabled={items.length === 1} onClick={() => setItems(rows => rows.filter((_, index) => index !== i))} variant="outline">移除</Button>
              </div>
            ))}
            <div className="toolbar">
              <Button type="button" disabled={items.length >= 50} onClick={() => setItems(rows => [...rows, {drug_id: 0, quantity: 1, dosage: '', frequency: '', days: 1}])} variant="secondary">添加药品</Button>
              <Button disabled={busy}>{editing ? '保存草稿并划价' : '创建草稿并划价'}</Button>
            </div>
          </form>
        </details>
      )}

      <ErrorNotice error={error || list.error || drugs.error}/>
      <Search onSearch={v => {setListKeyword(v); setPage(1);}} placeholder="按患者姓名或编号查找处方"/>
      <div className="toolbar">
        <div className="segmented-control">
          {visibleStatuses.map(([value, label]) => (
            <Button key={value} variant={status === value ? 'default' : 'ghost'} size="sm" onClick={() => {setStatus(value); setPage(1);}}>{label}</Button>
          ))}
        </div>
        <Button variant="outline" onClick={() => setVersion(v => v + 1)}><RotateCcw size={14}/>刷新</Button>
      </div>
      <Table headers={['患者', '诊断', '金额', '状态', '操作']} loading={list.loading}>
        {list.data?.items.map(rx => (
          <tr key={rx.id}>
            <td><strong>{rx.patient_name}</strong><small className="cell-sub">{rx.patient_no}</small></td>
            <td>{rx.diagnosis_name || '—'}</td>
            <td><strong className="money-text">¥{rx.total_amount}</strong></td>
            <td><StateBadge value={rx.status}/></td>
            <td>
              <Button onClick={() => {setSelected(rx); setError(null);}} variant="outline">查看明细</Button>
              {canCreate && rx.status === '草稿' && (
                <>
                  <Button onClick={() => {
                    setEditing(rx.id);
                    setRegistration(String(rx.registration_id));
                    setCode(rx.diagnosis_code || '');
                    setDiagnosis(rx.diagnosis_name || '');
                    setItems(rx.items.map(item => ({drug_id: item.drug_id, quantity: item.quantity, dosage: item.dosage || '', frequency: item.frequency || '', days: item.days || 1})));
                    window.scrollTo(0, 0);
                  }} variant="outline">编辑草稿</Button>
                  <Button disabled={busy} onClick={() => submit(rx)}>提交为待收费</Button>
                </>
              )}
            </td>
          </tr>
        ))}
      </Table>
      <Empty visible={!list.loading && list.data?.items.length === 0} title="没有匹配的处方"/>
      <Pager data={list.data} page={page} setPage={setPage}/>

      <Modal
        open={Boolean(selected)}
        title={selected ? '处方 #' + selected.id : '处方明细'}
        subtitle={selected ? selected.patient_name + ' · ' + (selected.patient_no || '') : undefined}
        onClose={() => setSelected(null)}
        footer={selected ? (
          <>
            <Button variant="outline" onClick={() => setSelected(null)}>关闭</Button>
            {canCreate && selected.status === '草稿' && <Button disabled={busy} onClick={() => submit(selected)}>{busy ? '提交中…' : '提交为待收费'}</Button>}
          </>
        ) : undefined}
      >
        {selected && <PrescriptionDetail rx={selected} embedded/>}
      </Modal>
    </section>
  );
}

function QueuePage({dispense = false}: {dispense?: boolean}) {
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [selected, setSelected] = useState<Prescription | null>(null);
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState(dispense ? '已收费' : '待收费');
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState<Charge | Dispense | null>(null);
  const [paymentMethod, setPaymentMethod] = useState('现金');
  const target = dispense ? status : '待收费';
  const pending = target === '已收费' || target === '待收费';
  const list = useData<PageData<Prescription>>(
    '/prescriptions?status=' + encodeURIComponent(target)
    + '&keyword=' + encodeURIComponent(keyword)
    + '&page=' + page,
    version,
  );

  async function action() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setReceipt(null);
    try {
      setReceipt(await apiClient.post<Charge | Dispense>('/prescriptions/' + selected.id + (dispense ? '/dispense' : '/charge'), dispense ? undefined : {payment_method: paymentMethod}));
      setSelected(null);
      setVersion(v => v + 1);
    } catch (r) {
      setError(r);
    } finally {
      setBusy(false);
    }
  }

  const footer = selected ? (
    <>
      {!dispense && pending && (
        <Field label="收费方式">
          <NativeSelect value={paymentMethod} onChange={e => setPaymentMethod(e.target.value)}>
            <option>现金</option><option>银行卡</option><option>模拟扫码</option>
          </NativeSelect>
        </Field>
      )}
      <Button variant="outline" onClick={() => setSelected(null)}>关闭</Button>
      {pending
        ? <Button onClick={action} disabled={busy}>{busy ? '处理中…' : dispense ? '确认发药' : '确认收费'}</Button>
        : <a className="button button-secondary" href={'/print/prescriptions/' + selected.id}>查看处方笺</a>}
    </>
  ) : undefined;

  return (
    <section className="page-section">
      <Heading
        title={dispense ? '药房发药' : '收费台'}
        description={dispense
          ? '核对患者与药品明细，确认后记录药师、时间和审计。本步骤不重复扣库存。'
          : '选择待收费处方，核对后端计算的金额后收费。任一药品库存不足，整笔操作回滚。'}
      />
      {dispense && (
        <div className="segmented-control section-tabs">
          {[['已收费', '待发药'], ['已发药', '已发药']].map(([value, label]) => (
            <Button key={value} variant={status === value ? 'default' : 'ghost'} onClick={() => {setStatus(value); setSelected(null); setReceipt(null); setPage(1);}}>{label}</Button>
          ))}
        </div>
      )}
      <Search onSearch={v => {setKeyword(v); setPage(1);}} placeholder="按患者姓名或编号查找"/>
      <div className="toolbar">
        <Button onClick={() => setVersion(v => v + 1)} variant="outline"><RotateCcw size={14}/>刷新待办</Button>
      </div>
      <ErrorNotice error={selected ? null : error || list.error}/>
      {receipt && (
        <StatusMessage tone="success" title={dispense ? '发药成功' : '收费成功'}>
          处方 #{receipt.prescription_id} 已完成{dispense ? '发药' : '收费'}。{'amount' in receipt ? '金额 ¥ ' + receipt.amount : '发药记录已保存'}；审计可查询。
          {!dispense && <a className="text-action" href={'/print/receipts/' + receipt.prescription_id}>查看收费凭证</a>}
        </StatusMessage>
      )}
      <Table headers={['患者', '患者编号', '诊断', '金额', '状态', '操作']} loading={list.loading}>
        {list.data?.items.map(rx => (
          <tr key={rx.id}>
            <td><strong>{rx.patient_name}</strong></td>
            <td>{rx.patient_no}</td>
            <td>{rx.diagnosis_name || '—'}</td>
            <td><strong className="money-text">¥{rx.total_amount}</strong></td>
            <td><StateBadge value={rx.status}/></td>
            <td><Button onClick={() => {setSelected(rx); setReceipt(null); setError(null);}} variant="outline">{pending ? '核对明细' : '查看明细'}</Button></td>
          </tr>
        ))}
      </Table>
      <Empty visible={!list.loading && list.data?.items.length === 0} title={dispense ? (status === '已发药' ? '还没有已发药记录' : '没有待处理的发药记录') : '当前没有待收费处方'}/>
      <Pager data={list.data} page={page} setPage={setPage}/>

      <Modal
        open={Boolean(selected)}
        title={selected ? (dispense ? '发药核对' : '收费核对') + ' · ' + selected.patient_name : '处方明细'}
        subtitle={selected ? '处方 #' + selected.id + ' · ' + selected.patient_no : undefined}
        onClose={() => setSelected(null)}
        footer={footer}
      >
        {selected && <PrescriptionDetail rx={selected} embedded/>}
        {selected && <ErrorNotice error={error}/>}
        {!dispense && pending && <p className="inline-tip">教学演示记账，不连接真实支付。</p>}
      </Modal>
    </section>
  );
}

export function BillingPage() { return <QueuePage/>; }
export function DispensingPage() { return <QueuePage dispense/>; }
