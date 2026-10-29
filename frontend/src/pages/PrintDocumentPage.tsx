import {Link,useParams} from 'react-router-dom';
import {ArrowLeft,Printer} from 'lucide-react';
import {useData,formatTime} from '../api/hooks';
import type {Prescription} from '../api/types';
import type {Receipt} from '../api/enhancements';
import {ErrorNotice} from '../components/BusinessUI';
import {Button} from '../components/ui/button';

export function PrintDocumentPage({receipt=false}:{receipt?:boolean}){
  const {prescriptionId}=useParams();
  const rx=useData<Prescription>('/prescriptions/'+prescriptionId);
  const payment=useData<Receipt>(receipt?'/prescriptions/'+prescriptionId+'/receipt':null);
  return <section className="document-preview"><div className="document-tools print-hide"><Link className="text-action" to={receipt?'/financial-records':'/prescriptions'}><ArrowLeft size={15}/>返回业务列表</Link><Button onClick={()=>window.print()} disabled={!rx.data||(receipt&&!payment.data)}><Printer size={16}/>打印 / 保存为 PDF</Button></div><ErrorNotice error={rx.error||payment.error}/>{rx.data&&(!receipt||payment.data)&&<article className="print-document"><div className="document-hospital">和序 HIS · 门诊业务管理</div><h1>{receipt?'门诊收费凭证':'门诊处方笺'}</h1><div className="document-number"><span>{receipt?payment.data?.receipt_no:'RX-'+String(rx.data.id).padStart(6,'0')}</span><strong>教学演示 · 非临床使用</strong></div><div className="document-patient"><p>患者姓名：<b>{rx.data.patient_name}</b></p><p>患者编号：{rx.data.patient_no}</p><p>接诊医生：{rx.data.doctor_name}</p><p>处方状态：{rx.data.status}</p></div><p className="document-diagnosis">诊断：{rx.data.diagnosis_name} <span>{rx.data.diagnosis_code}</span></p><table><thead><tr><th>药品 / 规格</th><th>用法 / 频次</th><th>天数</th><th>数量</th><th>单价</th></tr></thead><tbody>{rx.data.items.map(item=><tr key={item.id}><td>{item.drug_name}<small>{item.specification}</small></td><td>{item.dosage||'—'}<small>{item.frequency||'—'}</small></td><td>{item.days||'—'}</td><td>{item.quantity}</td><td>¥{item.unit_price}</td></tr>)}</tbody></table><div className="document-total">{receipt?'收费金额':'处方合计'} <strong>¥{receipt?payment.data!.charge.amount:rx.data.total_amount}</strong></div>{receipt&&payment.data&&<div className="document-payment"><p>收费方式：{payment.data.charge.payment_method||'未记录'}</p><p>收费员：{payment.data.cashier}</p><p>收费时间：{payment.data.charge.paid_at?formatTime(payment.data.charge.paid_at):'未记录'}</p>{payment.data.refund&&<div className="document-refund"><strong>本笔已全额退费 ¥{payment.data.refund.amount}</strong><p>退费时间：{formatTime(payment.data.refund.refunded_at)}</p><p>退费原因：{payment.data.refund.reason}</p></div>}</div>}<div className="document-signatures"><span>接诊医生：{rx.data.doctor_name}</span><span>核对人：____________</span></div><footer>本凭证由课程演示系统生成，不作为真实处方、发票或支付证明。请勿用于真实诊疗。</footer></article>}</section>;
}
