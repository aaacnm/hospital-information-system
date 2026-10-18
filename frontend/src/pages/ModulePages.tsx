import { useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, apiClient } from '../api/client';
import type { AuditLogPage, Charge, Dispense, Prescription, Registration, Schedule, TriageResponse } from '../api/types';
import { StatusMessage } from '../components/StatusMessage';

function errorTitle(reason: unknown): string {
  if (!(reason instanceof ApiError)) return '请求失败';
  if (reason.status === 400) return '请求参数或业务条件不满足';
  if (reason.status === 401) return '登录已失效';
  if (reason.status === 403) return '当前角色没有此权限';
  if (reason.status === 409) return '业务状态冲突';
  return reason.status === 0 ? '后端服务不可用' : `请求失败（${reason.status}）`;
}

function RequestError({ reason }: { reason: unknown }) {
  return <StatusMessage tone="error" title={errorTitle(reason)}>{reason instanceof Error ? reason.message : '请稍后重试。'}</StatusMessage>;
}

function ResultPanel({ title, children }: { title: string; children: ReactNode }) {
  return <div className="result-panel"><strong>{title}</strong><div className="result-grid">{children}</div></div>;
}

function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return <label className="field"><span>{label}</span>{children}{hint ? <small>{hint}</small> : null}</label>;
}

export function SchedulesPage() {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [deptId, setDeptId] = useState('');
  const [items, setItems] = useState<Schedule[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  async function load(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(null); setItems(null);
    const query = new URLSearchParams({ date }); if (deptId) query.set('dept_id', deptId);
    try { setItems(await apiClient.get<Schedule[]>(`/schedules?${query.toString()}`)); } catch (reason) { setError(reason); } finally { setLoading(false); }
  }
  return <section className="page-section"><Heading eyebrow="业务模块 · F04" title="排班与号源" description="查询服务端有效排班。剩余号源由后端返回，不能在前端自行推算。" label="在线查询" /><form className="filter-bar" onSubmit={load}><Field label="就诊日期"><input aria-label="就诊日期" type="date" value={date} onChange={(event) => setDate(event.target.value)} required /></Field><Field label="科室 ID" hint="可留空查询全部科室"><input aria-label="科室 ID" inputMode="numeric" value={deptId} onChange={(event) => setDeptId(event.target.value.replace(/\D/g, ''))} placeholder="例如 1" /></Field><button className="button button-primary" type="submit" disabled={loading}>{loading ? '查询中…' : '查询排班'}</button></form>{error ? <RequestError reason={error} /> : null}{items && items.length === 0 ? <StatusMessage title="暂无排班">服务端没有返回符合条件的有效排班。</StatusMessage> : null}{items && items.length > 0 ? <div className="table-wrap"><table><caption>排班与剩余号源</caption><thead><tr><th>排班 ID</th><th>科室</th><th>医生</th><th>日期</th><th>时段</th><th>总号源</th><th>剩余</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td>{item.id}</td><td>{item.department_name}</td><td>{item.doctor_name}</td><td>{item.visit_date}</td><td>{item.period}</td><td>{item.total_quota}</td><td><strong>{item.remain_quota}</strong></td></tr>)}</tbody></table></div> : null}</section>;
}

export function RegistrationsPage() {
  const [patientId, setPatientId] = useState(''); const [scheduleId, setScheduleId] = useState('');
  const [result, setResult] = useState<Registration | null>(null); const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setLoading(true); setError(null); setResult(null); try { setResult(await apiClient.post<Registration>('/registrations', { patient_id: Number(patientId), schedule_id: Number(scheduleId) })); } catch (reason) { setError(reason); } finally { setLoading(false); } }
  return <section className="page-section"><Heading eyebrow="业务模块 · F05" title="挂号管理" description="提交后由服务端原子扣减号源并生成排队号。号源不足返回 409，不会创建半条挂号单。" label="真实提交" /><form className="form-panel" onSubmit={submit}><Field label="患者 ID" hint="当前后端 MVP 使用演示患者 ID"><input aria-label="患者 ID" inputMode="numeric" value={patientId} onChange={(event) => setPatientId(event.target.value.replace(/\D/g, ''))} required placeholder="例如 1" /></Field><Field label="排班 ID"><input aria-label="排班 ID" inputMode="numeric" value={scheduleId} onChange={(event) => setScheduleId(event.target.value.replace(/\D/g, ''))} required placeholder="从排班页面复制" /></Field><button className="button button-primary" type="submit" disabled={loading}>{loading ? '提交中…' : '确认挂号'}</button></form>{error ? <RequestError reason={error} /> : null}{result ? <ResultPanel title="挂号已由服务端创建"><div><span>挂号单</span><strong>#{result.id}</strong></div><div><span>排队号</span><strong>{result.queue_no}</strong></div><div><span>状态</span><strong>{result.status}</strong></div><div><span>号源</span><strong>#{result.schedule_id}</strong></div></ResultPanel> : null}</section>;
}

export function PrescriptionsPage() {
  const [registrationId, setRegistrationId] = useState(''); const [diagnosisCode, setDiagnosisCode] = useState(''); const [diagnosisName, setDiagnosisName] = useState(''); const [drugId, setDrugId] = useState(''); const [quantity, setQuantity] = useState('1');
  const [result, setResult] = useState<Prescription | null>(null); const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(false); const [submitting, setSubmitting] = useState(false);
  async function create(event: FormEvent) { event.preventDefault(); setLoading(true); setError(null); setResult(null); try { setResult(await apiClient.post<Prescription>('/prescriptions', { registration_id: Number(registrationId), diagnosis_code: diagnosisCode, diagnosis_name: diagnosisName, items: [{ drug_id: Number(drugId), quantity: Number(quantity) }] })); } catch (reason) { setError(reason); } finally { setLoading(false); } }
  async function submit() { if (!result) return; setSubmitting(true); setError(null); try { setResult(await apiClient.post<Prescription>(`/prescriptions/${result.id}/submit`)); } catch (reason) { setError(reason); } finally { setSubmitting(false); } }
  return <section className="page-section"><Heading eyebrow="业务模块 · F06" title="处方管理" description="医生创建草稿处方，再由服务端执行提交状态转换。金额不由前端填写。" label="医生操作" /><form className="form-panel form-grid" onSubmit={create}><Field label="挂号单 ID"><input aria-label="挂号单 ID" inputMode="numeric" value={registrationId} onChange={(event) => setRegistrationId(event.target.value.replace(/\D/g, ''))} required /></Field><Field label="诊断编码"><input aria-label="诊断编码" value={diagnosisCode} onChange={(event) => setDiagnosisCode(event.target.value)} required maxLength={32} placeholder="例如 J06.9" /></Field><Field label="诊断名称"><input aria-label="诊断名称" value={diagnosisName} onChange={(event) => setDiagnosisName(event.target.value)} required maxLength={120} /></Field><Field label="药品 ID"><input aria-label="药品 ID" inputMode="numeric" value={drugId} onChange={(event) => setDrugId(event.target.value.replace(/\D/g, ''))} required /></Field><Field label="数量"><input aria-label="数量" type="number" min="1" max="1000" value={quantity} onChange={(event) => setQuantity(event.target.value)} required /></Field><div className="form-action"><button className="button button-primary" type="submit" disabled={loading}>{loading ? '创建中…' : '创建草稿处方'}</button></div></form>{error ? <RequestError reason={error} /> : null}{result ? <ResultPanel title={`处方 #${result.id}`}><div><span>状态</span><strong>{result.status}</strong></div><div><span>诊断</span><strong>{result.diagnosis_code} · {result.diagnosis_name}</strong></div><div><span>项目数</span><strong>{result.items.length}</strong></div>{result.status === '草稿' ? <div><button className="button button-secondary" type="button" onClick={submit} disabled={submitting}>{submitting ? '提交中…' : '提交为待收费'}</button></div> : null}</ResultPanel> : null}</section>;
}

export function BillingPage() {
  const [prescriptionId, setPrescriptionId] = useState(''); const [result, setResult] = useState<Charge | null>(null); const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setLoading(true); setError(null); setResult(null); try { setResult(await apiClient.post<Charge>(`/prescriptions/${Number(prescriptionId)}/charge`)); } catch (reason) { setError(reason); } finally { setLoading(false); } }
  return <ActionPage title="收费台" eyebrow="业务模块 · F08" description="输入待收费处方 ID。服务端重算金额并在同一事务中扣库存，前端不接受金额输入。" label="收费处方 ID" value={prescriptionId} setValue={setPrescriptionId} loading={loading} onSubmit={submit} result={result ? <ResultPanel title="收费已由服务端确认"><div><span>收费单</span><strong>#{result.id}</strong></div><div><span>处方</span><strong>#{result.prescription_id}</strong></div><div><span>金额</span><strong>¥ {result.amount}</strong></div><div><span>状态</span><strong>{result.status}</strong></div></ResultPanel> : null} error={error} />;
}

export function DispensingPage() {
  const [prescriptionId, setPrescriptionId] = useState(''); const [result, setResult] = useState<Dispense | null>(null); const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setLoading(true); setError(null); setResult(null); try { setResult(await apiClient.post<Dispense>(`/prescriptions/${Number(prescriptionId)}/dispense`)); } catch (reason) { setError(reason); } finally { setLoading(false); } }
  return <ActionPage title="药房发药" eyebrow="业务模块 · F10" description="输入已收费处方 ID。服务端验证状态并记录药师和发药时间。" label="已收费处方 ID" value={prescriptionId} setValue={setPrescriptionId} loading={loading} onSubmit={submit} result={result ? <ResultPanel title="发药已由服务端确认"><div><span>发药单</span><strong>#{result.id}</strong></div><div><span>处方</span><strong>#{result.prescription_id}</strong></div><div><span>状态</span><strong>{result.status}</strong></div><div><span>发药时间</span><strong>{result.dispensed_at || '—'}</strong></div></ResultPanel> : null} error={error} />;
}

function ActionPage({ title, eyebrow, description, label, value, setValue, loading, onSubmit, result, error }: { title: string; eyebrow: string; description: string; label: string; value: string; setValue: (value: string) => void; loading: boolean; onSubmit: (event: FormEvent) => void; result: ReactNode; error: unknown }) {
  return <section className="page-section"><Heading eyebrow={eyebrow} title={title} description={description} label="真实提交" /><form className="form-panel" onSubmit={onSubmit}><Field label={label}><input aria-label={label} inputMode="numeric" value={value} onChange={(event) => setValue(event.target.value.replace(/\D/g, ''))} required placeholder="请输入正整数 ID" /></Field><button className="button button-primary" type="submit" disabled={loading}>{loading ? '提交中…' : title}</button></form>{error ? <RequestError reason={error} /> : null}{result}</section>;
}

export function AuditLogsPage() {
  const [result, setResult] = useState<AuditLogPage | null>(null); const [error, setError] = useState<unknown>(null); const [loading, setLoading] = useState(false);
  async function load() { setLoading(true); setError(null); try { setResult(await apiClient.get<AuditLogPage>('/audit-logs?page=1&page_size=50')); } catch (reason) { setError(reason); } finally { setLoading(false); } }
  return <section className="page-section"><div className="page-heading"><div><p className="eyebrow">业务模块 · F11</p><h1>审计日志</h1><p className="page-description">管理员查询服务端记录的登录、挂号、处方、收费和发药操作。</p></div><button className="button button-primary" type="button" onClick={load} disabled={loading}>{loading ? '查询中…' : '刷新日志'}</button></div>{error ? <RequestError reason={error} /> : null}{result && result.items.length === 0 ? <StatusMessage title="暂无审计记录">服务端没有返回日志。</StatusMessage> : null}{result && result.items.length > 0 ? <div className="table-wrap"><table><caption>最近操作（{result.total} 条）</caption><thead><tr><th>时间</th><th>用户 ID</th><th>动作</th><th>资源</th><th>资源 ID</th><th>IP</th></tr></thead><tbody>{result.items.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.user_id ?? '—'}</td><td><code>{item.action}</code></td><td>{item.resource_type || '—'}</td><td>{item.resource_id || '—'}</td><td>{item.ip || '—'}</td></tr>)}</tbody></table></div> : null}</section>;
}

export function TriagePage() {
  const [symptoms, setSymptoms] = useState('');
  const [result, setResult] = useState<TriageResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setLoading(true); setError(null); setResult(null);
    try { setResult(await apiClient.post<TriageResponse>('/triage', { symptoms: symptoms.trim() })); }
    catch (reason) { setError(reason); }
    finally { setLoading(false); }
  }

  const isFallback = result?.source === 'fallback';
  return <section className="page-section"><Heading eyebrow="辅助功能 · F16" title="智能分诊" description="根据症状生成候选科室和紧急程度。此功能只提供辅助建议，不诊断、不处方、不改变收费结果。" label="AI 辅助" /><div className="ai-disclaimer">本建议由 AI 生成，仅供参考，请以医生诊断为准。出现急危重症症状时请立即联系急救服务。</div><form className="form-panel triage-form" onSubmit={submit}><Field label="症状描述" hint="请勿输入姓名、身份证号或手机号"><textarea aria-label="症状描述" value={symptoms} onChange={(event) => setSymptoms(event.target.value)} required minLength={2} maxLength={1000} placeholder="例如：昨晚开始发热、咽痛，体温 38.2℃" /></Field><button className="button button-primary" type="submit" disabled={loading}>{loading ? '分析中…' : '获取辅助建议'}</button></form>{error ? <RequestError reason={error} /> : null}{result ? <div className={`triage-result ${isFallback ? 'triage-fallback' : ''}`} role="status"><div className="triage-result-heading"><strong>{isFallback ? '暂未获得 AI 建议' : '已获得辅助建议'}</strong><span>{isFallback ? '系统兜底' : 'AI 返回'}</span></div><dl><div><dt>建议科室</dt><dd>{result.dept}</dd></div><div><dt>紧急程度</dt><dd>{result.urgency}</dd></div><div><dt>说明</dt><dd>{result.notes}</dd></div></dl><p className="triage-result-disclaimer">{result.disclaimer || '本建议由 AI 生成，仅供参考，请以医生诊断为准。'}</p></div> : null}</section>;
}

function Heading({ eyebrow, title, description, label }: { eyebrow: string; title: string; description: string; label: string }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div><span className="state-label">{label}</span></div>;
}
