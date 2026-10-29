import {useEffect,useState,type FormEvent} from 'react';
import {Link,useParams} from 'react-router-dom';
import {Activity,ArrowRight,CalendarDays,ClipboardPlus,Clock3,History,Save,Stethoscope,UsersRound} from 'lucide-react';
import {apiClient} from '../api/client';
import {formatTime,localDay,useData} from '../api/hooks';
import type {PageData,Visit} from '../api/business';
import type {ClinicalInput,ClinicalNote,ClinicalVisit,HistoryData} from '../api/enhancements';
import {useAuth} from '../auth/AuthContext';
import {Empty,ErrorNotice,Field,Heading,Pager} from '../components/BusinessUI';
import {StateBadge} from '../components/StateBadge';
import {StatusMessage} from '../components/StatusMessage';
import {Badge} from '../components/ui/badge';
import {Button} from '../components/ui/button';
import {Card,CardContent} from '../components/ui/card';
import {Textarea} from '../components/ui/textarea';

const fields:[keyof ClinicalInput,string,number][]=[['chief_complaint','主诉',300],['present_illness','现病史',2000],['past_history','既往史',1000],['allergy_history','过敏史',500],['examination','查体与诊疗意见',1000]];
const emptyNote:ClinicalInput={chief_complaint:'',present_illness:'',past_history:'',allergy_history:'',examination:''};
const sampleNote:ClinicalInput={chief_complaint:'咽部不适伴低热2天（虚构教学示例）',present_illness:'两日前出现咽部不适，伴低热，无明显呼吸困难。本内容仅用于课堂演示。',past_history:'患者自述既往体健（虚构教学数据）。',allergy_history:'自述无已知药物过敏史（虚构；实际开方须由医生核实）。',examination:'教学演示未开展实际查体，不作为临床诊疗依据。'};

function NoteForm({registrationId,initial,locked,onSaved}:{registrationId:number;initial:ClinicalNote|null;locked:boolean;onSaved:()=>void}) {
  const [form,setForm]=useState<ClinicalInput>(initial||emptyNote);
  const [busy,setBusy]=useState(false),[error,setError]=useState<unknown>(null);
  async function save(e:FormEvent){e.preventDefault();setBusy(true);setError(null);try{await apiClient.put('/registrations/'+registrationId+'/clinical-record',form);onSaved();}catch(e){setError(e);}finally{setBusy(false);}}
  return <form className="clinical-note-form" onSubmit={save}><div className="note-form-title"><div><h3>本次门诊记录</h3><p>记录就诊情况，提交处方后锁定本次文书。</p></div><div className="toolbar"><Badge variant="outline">{locked?'已锁定':'可编辑'}</Badge>{!locked&&<Button type="button" variant="ghost" size="sm" onClick={()=>setForm(sampleNote)}>填入教学示例</Button>}</div></div><div className="note-fields">{fields.map(([key,label,max])=><Field label={label} key={key}><Textarea value={form[key]} onChange={e=>setForm({...form,[key]:e.target.value})} required maxLength={max} disabled={locked} placeholder={'请输入'+label}/></Field>)}</div><ErrorNotice error={error}/>{!locked&&<Button disabled={busy}><Save size={15}/>{busy?'保存中…':'保存诊疗记录'}</Button>}</form>;
}

export function ClinicalRecordEditor({registrationId,version}:{registrationId:number;version:number}) {
  const [refresh,setRefresh]=useState(0),[savedRegistration,setSavedRegistration]=useState<number|null>(null);
  const result=useData<ClinicalVisit>(registrationId?'/registrations/'+registrationId+'/clinical-record':null,version+refresh);
  if(!registrationId)return <div className="inline-tip"><ClipboardPlus size={16}/>选择待诊患者后，可填写本次诊疗记录。</div>;
  return <Card className="clinical-record-card"><CardContent className="p-6"><ErrorNotice error={result.error}/>{savedRegistration===registrationId&&<StatusMessage tone="success" title="诊疗记录已保存"/>}{result.data&&<><div className="patient-ribbon"><span className="patient-avatar">{result.data.patient.name.slice(-1)}</span><div><strong>{result.data.patient.name}</strong><span>{result.data.patient.patient_no} · {result.data.patient.gender||'性别未录入'}</span></div><Link className="text-action" to={'/patients/'+result.data.patient.id+'/timeline'}><History size={15}/>查看就诊时间线<ArrowRight size={13}/></Link></div><NoteForm key={registrationId+'-'+(result.data.record?.updated_at||'new')} registrationId={registrationId} initial={result.data.record} locked={result.data.locked} onSaved={()=>{setSavedRegistration(registrationId);setRefresh(v=>v+1);}}/></>}</CardContent></Card>;
}

export function PatientTimelinePage(){
  const {patientId}=useParams();const [page,setPage]=useState(1);
  const result=useData<HistoryData>('/patients/'+patientId+'/timeline?page='+page);
  return <section className="page-section"><Heading title="患者就诊时间线" description="按时间回看接诊、诊断和处方，快速了解患者既往就诊情况。"/><ErrorNotice error={result.error}/>{result.data&&<><Card className="patient-summary"><CardContent className="p-6"><span className="patient-avatar large">{result.data.patient.name.slice(-1)}</span><div><h2>{result.data.patient.name}</h2><p>{result.data.patient.patient_no} · {result.data.patient.gender||'性别未录入'}</p></div><div className="patient-meta"><span>联系电话</span><strong>{result.data.patient.phone||'未录入'}</strong></div><div className="patient-meta"><span>证件号码</span><strong>{result.data.patient.id_no_masked||'未录入'}</strong></div></CardContent></Card><div className="history-timeline">{result.data.items.map(v=><article className="history-entry" key={v.registration_id}><span className="timeline-dot"><Stethoscope size={16}/></span><div className="history-date"><CalendarDays size={13}/>{v.visit_date} {v.period}<span>{v.doctor_name}</span></div><Card><CardContent className="p-6"><div className="history-entry-heading"><h2>{v.diagnosis_name||'待完成诊断'}</h2><StateBadge value={v.prescription_status||v.status}/></div><p className="history-code">{v.diagnosis_code||'未录入诊断编码'} · 就诊编号 V-{String(v.registration_id).padStart(6,'0')}</p><p className="history-complaint">{v.chief_complaint||'本次未保存诊疗文书'}</p><div className="history-entry-footer"><span>处方金额 <strong>¥{v.amount}</strong></span>{v.prescription_id&&<Link className="text-action" to={'/print/prescriptions/'+v.prescription_id}>查看处方<ArrowRight size={13}/></Link>}{v.signed_at&&<small>签署于 {formatTime(v.signed_at)}</small>}</div></CardContent></Card></article>)}</div><Empty visible={result.data.items.length===0}/><Pager data={result.data} page={page} setPage={setPage}/></>}</section>;
}

export function QueueBoardPage(){
  const {user}=useAuth();const doctor=user?.roles.includes('doctor');
  const [version,setVersion]=useState(0),[clock,setClock]=useState(new Date()),[error,setError]=useState<unknown>(null),[busy,setBusy]=useState(false);
  useEffect(()=>{const timer=window.setInterval(()=>setClock(new Date()),1000);return()=>window.clearInterval(timer);},[]);
  useEffect(()=>{const timer=window.setInterval(()=>setVersion(v=>v+1),15000);return()=>window.clearInterval(timer);},[]);
  const result=useData<PageData<Visit>>('/registrations?visit_date='+localDay()+'&page_size=100',version);
  const today=result.data?.items||[];
  const waiting=today.filter(v=>v.status==='候诊').slice().sort((a,b)=>a.queue_no-b.queue_no),active=today.filter(v=>v.status==='就诊中'),completed=today.filter(v=>v.status==='已完成');
  async function start(v:Visit){setBusy(true);setError(null);try{await apiClient.post('/registrations/'+v.id+'/start');setVersion(n=>n+1);}catch(e){setError(e);}finally{setBusy(false);}}
  return <section className="page-section"><Heading title="门诊接诊看板" description="清晰查看候诊与接诊进度，按排队号有序处理今日患者。"><Button variant="outline" onClick={()=>setVersion(v=>v+1)}>刷新看板</Button></Heading><ErrorNotice error={error||result.error}/><div className="queue-hero"><div><Badge variant="outline"><span className="tiny-dot"/>今日门诊</Badge><h2>有序候诊，安心就医</h2><p>{localDay()} · 展示今日挂号与接诊进度</p></div><div className="queue-clock">{clock.toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}<small>每15秒更新候诊列表</small></div></div><div className="queue-stat-grid">{[{label:'候诊患者',value:waiting.length,icon:UsersRound},{label:'正在接诊',value:active.length,icon:Activity},{label:'今日已完成',value:completed.length,icon:ClipboardPlus}].map(item=><Card key={item.label}><CardContent className="p-5"><item.icon size={21}/><div><span>{item.label}</span><strong>{item.value}</strong></div></CardContent></Card>)}</div><div className="queue-columns"><div><div className="section-title"><h2><Clock3 size={17}/>候诊队列</h2><span>{waiting.length}人等待</span></div>{waiting.map(v=><Card className="queue-patient" key={v.id}><CardContent className="p-5"><span className="queue-number">{String(v.queue_no).padStart(2,'0')}</span><div><strong>{v.patient_name}</strong><p>{v.doctor_name} · {v.period} · {v.patient_no}</p></div>{doctor?<Button size="sm" disabled={busy} onClick={()=>start(v)}>开始接诊</Button>:<StateBadge value="候诊"/>}</CardContent></Card>)}<Empty visible={!result.loading&&waiting.length===0} title="当前没有候诊患者"/></div><div><div className="section-title"><h2><Stethoscope size={17}/>接诊中</h2><span>{active.length}人</span></div>{active.map(v=><Card className="active-consultation" key={v.id}><CardContent className="p-6"><div className="history-entry-heading"><Badge variant="secondary">排队号 {v.queue_no}</Badge><span className="tiny-dot"/></div><h3>{v.patient_name}</h3><p>{v.doctor_name} · {v.patient_no}</p>{doctor&&<Link className="button button-primary" to={'/prescriptions?registration='+v.id}>进入诊疗工作台<ArrowRight size={14}/></Link>}{v.prescription_id&&<small>处方 RX-{String(v.prescription_id).padStart(6,'0')}</small>}</CardContent></Card>)}<Empty visible={!result.loading&&active.length===0} title="当前没有接诊中的患者"/></div></div>{completed.length>0&&<div className="completed-list"><div className="section-title"><h2><ClipboardPlus size={17}/>今日已完成</h2><span>{completed.length}人</span></div><Card><CardContent className="p-0">{completed.map(v=><div className="completed-row" key={v.id}><span className="queue-number">{String(v.queue_no).padStart(2,'0')}</span><strong>{v.patient_name}</strong><span>{v.doctor_name} · {v.period}</span><StateBadge value={v.status}/>{v.prescription_id&&<Link className="text-action" to={'/print/prescriptions/'+v.prescription_id}>查看处方<ArrowRight size={13}/></Link>}</div>)}</CardContent></Card></div>}</section>;
}
