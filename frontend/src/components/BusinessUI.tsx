import {Input} from './ui/input';
import {Button} from './ui/button';
import { cloneElement, useId, useState, type FormEvent, type ReactElement, type ReactNode } from 'react';
import { StatusMessage } from './StatusMessage';
import type { PageData } from '../api/business';
import { Table as ShadcnTable, TableHeader, TableBody, TableRow, TableHead } from './ui/table';
export function Heading({ title, description, children }: {
    title: string;
    description: string;
    children?: ReactNode;
}) {
    return <div className="page-heading"><div><p className="eyebrow">门诊业务工作台</p><h1>{title}</h1><p className="page-description">{description}</p></div>{children}</div>;
}
export function Field({ label, children }: {
    label: string;
    children: ReactElement<{id?:string}>;
}) { const generatedId=useId();const id=children.props.id||generatedId;return <div className="field"><label htmlFor={id}>{label}</label>{cloneElement(children,{id})}</div>; }
export function ErrorNotice({ error }: {
    error: unknown;
}) { return error ? <StatusMessage tone="error" title="操作未完成">{error instanceof Error ? error.message : '请稍后重试。'}</StatusMessage> : null; }
export function Table({ headers, children }: {
    headers: string[];
    children: ReactNode;
}) { return <div className="table-wrap"><ShadcnTable><TableHeader><TableRow>{headers.map(h => <TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{children}</TableBody></ShadcnTable></div>; }
export function Pager({ data, page, setPage }: {
    data: PageData<unknown> | null;
    page: number;
    setPage: (p: number) => void;
}) { return data ? <div className="pager"><span>共 {data.total} 条，第 {page} 页</span><Button disabled={page <= 1} onClick={() => setPage(page - 1)} variant="outline">上一页</Button><Button disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)} variant="outline">下一页</Button></div> : null; }
export function Search({ onSearch, placeholder = '姓名或患者编号' }: {
    onSearch: (v: string) => void;
    placeholder?: string;
}) {
    const [value, setValue] = useState('');
    function submit(event: FormEvent) { event.preventDefault(); onSearch(value.trim()); }
    return <form className="filter-bar" onSubmit={submit}><Field label="搜索"><Input value={value} onChange={e => setValue(e.target.value)} placeholder={placeholder}/></Field><Button variant="secondary">查询</Button></form>;
}
export function Empty({ visible }: {
    visible: boolean;
}) { return visible ? <StatusMessage title="暂无符合条件的记录">请调整筛选条件或完成前一步业务。</StatusMessage> : null; }
