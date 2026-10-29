import {useState} from 'react';

export function TrendChart({values,labels,title,color='#5b6bff',money=false}:{values:number[];labels:string[];title:string;color?:string;money?:boolean}) {
  const [active,setActive]=useState<number|null>(null);
  const minimum=Math.min(0,...values),maximum=Math.max(1,...values),span=maximum-minimum;
  const point=(v:number,i:number)=>[40+i*600/Math.max(1,values.length-1),170-(v-minimum)*142/span];
  const points=values.map((v,i)=>point(v,i));
  const baseline=170-(0-minimum)*142/span;
  const area=points.length?`${points[0][0]},${baseline} ${points.map(p=>p.join(',')).join(' ')} ${points.at(-1)![0]},${baseline}`:'';
  const show=(v:number)=>money?'¥'+v.toFixed(2):String(v);
  const selected=active===null?values.length-1:active;
  return <div className="trend-chart"><div className="chart-caption"><span>{title}</span><strong style={{color}}>{labels[selected]||'暂无数据'} <b>{show(values[selected]||0)}</b></strong></div><svg viewBox="0 0 680 210" role="img" aria-label={title+'，共'+values.length+'天'}>
    {[0,1,2,3].map(i=><g key={i}><line x1="40" x2="640" y1={28+i*142/3} y2={28+i*142/3} stroke="#ececf2" strokeDasharray="3 5"/><text x="32" y={32+i*142/3} textAnchor="end" fill="#9a9aa5" fontSize="9">{(maximum-i*span/3).toFixed(money?1:0)}</text></g>)}
    <polygon points={area} fill={color} opacity=".08"/><polyline points={points.map(p=>p.join(',')).join(' ')} fill="none" stroke={color} strokeWidth="2.6" strokeLinejoin="round" strokeLinecap="round"/>
    {points.map(([x,y],i)=><g key={i}><rect x={x-300/Math.max(1,values.length-1)} y="20" width={600/Math.max(1,values.length-1)} height="160" fill="transparent" onMouseEnter={()=>setActive(i)} onMouseLeave={()=>setActive(null)}/><circle cx={x} cy={y} r={i===selected?4.5:2.1} fill={color} pointerEvents="none"><title>{labels[i]}：{show(values[i])}</title></circle></g>)}
    {labels.map((label,i)=>(i===0||i===labels.length-1||i===Math.floor(labels.length/2))&&<text key={i} x={point(0,i)[0]} y="198" textAnchor="middle" fill="#9a9aa5" fontSize="10">{label.slice(5)}</text>)}
  </svg></div>;
}
