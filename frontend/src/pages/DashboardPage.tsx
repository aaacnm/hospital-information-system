import {Link} from 'react-router-dom';
import {ArrowUpRight,CalendarDays,ClipboardList,Pill,ReceiptText,ScrollText,Stethoscope,UsersRound} from 'lucide-react';
import {useAuth} from '../auth/AuthContext';
import {useData} from '../api/hooks';
import {ErrorNotice,Heading} from '../components/BusinessUI';
import {Card,CardContent} from '../components/ui/card';
import {Badge} from '../components/ui/badge';
import {Skeleton} from '../components/ui/skeleton';

const labels:Record<string,string>={registration_count:'今日有效挂号',charged_amount:'今日收费金额',dispensed_count:'今日发药单数',draft_count:'我的草稿处方',submitted_count:'我的已提交处方',pending_count:'当前待办处方'};
const metricIcons=[UsersRound,ReceiptText,Pill];
export function DashboardPage(){
 const {user}=useAuth();const {data,error,loading}=useData<Record<string,string|number>>('/workload');
 const actions=user?.roles.includes('admin')?[{name:'经营统计',description:'查看挂号、收费与发药汇总',path:'/reports',icon:ReceiptText},{name:'审计追溯',description:'查询操作记录与库存变化',path:'/audit-logs',icon:ScrollText},{name:'药品库存',description:'维护药品档案与批次效期',path:'/drugs',icon:Pill}]:user?.roles.includes('doctor')?[{name:'接诊工作台',description:'从本人待诊患者开始接诊',path:'/registrations',icon:Stethoscope},{name:'处方管理',description:'编辑草稿、核对明细并提交',path:'/prescriptions',icon:ClipboardList}]:user?.roles.includes('cashier')?[{name:'患者挂号',description:'选择患者、医生与就诊时段',path:'/registrations',icon:UsersRound},{name:'待收费处方',description:'核对药品明细和应付金额',path:'/billing',icon:ReceiptText}]:[{name:'待发药处方',description:'核验已收费处方并确认发药',path:'/dispensing',icon:Pill},{name:'药品库存',description:'查看批次库存与有效期',path:'/drugs',icon:ClipboardList}];
 return <section className="page-section"><Heading title={'你好，'+(user?.displayName||'')} description="有序处理每一笔门诊业务，让诊疗流程清晰可追溯。"><Badge variant="outline" className="day-badge"><CalendarDays size={14}/>{data?.date||'今日工作概览'}</Badge></Heading><ErrorNotice error={error}/>
 <div className="metric-grid">{loading?[0,1,2].map(i=><Card key={i}><CardContent className="p-6"><Skeleton className="h-4 w-24"/><Skeleton className="mt-4 h-10 w-20"/></CardContent></Card>):data&&Object.entries(data).filter(([key])=>key!=='date').map(([key,value],i)=>{const Icon=metricIcons[i%3];return <Card key={key} className="metric-card"><CardContent className="p-6"><div className="metric-top"><span>{labels[key]||key}</span><span className={'metric-icon tone-'+i}><Icon size={19}/></span></div><strong className="metric-value">{key==='charged_amount'&&<em>¥</em>}{value}</strong><small>来自当前业务记录<span className="tiny-dot"/></small></CardContent></Card>;})}</div>
 <div className="section-title"><h2>快捷工作台</h2><span>按职责进入业务</span></div><div className="quick-grid">{actions.map(action=><Link key={action.path} to={action.path} className="quick-action"><span className="quick-icon"><action.icon size={22}/></span><div><strong>{action.name}</strong><p>{action.description}</p></div><ArrowUpRight size={18}/></Link>)}</div>
 <Card className="flow-overview"><CardContent className="p-7"><div className="section-title"><h2>门诊业务流程</h2><Badge variant="secondary">全程留痕</Badge></div><div className="workflow">{[{title:'患者挂号',note:'确认患者与就诊号源',icon:UsersRound},{title:'医生开方',note:'诊断记录与后端划价',icon:Stethoscope},{title:'核对收费',note:'费用与批次库存同步',icon:ReceiptText},{title:'药房发药',note:'药师核验与操作追溯',icon:Pill}].map((step,i)=><div className="workflow-step" key={step.title}><div className="step-icon"><step.icon size={21}/></div><div><small>0{i+1}</small><strong>{step.title}</strong><p>{step.note}</p></div>{i<3&&<span className="step-line"/>}</div>)}</div></CardContent></Card>
 <div className="workspace-note"><span className="note-icon">i</span><p>当前使用虚构教学数据。请按角色完成操作，涉及诊疗的判断仍需由医生确认。</p></div></section>;
}
