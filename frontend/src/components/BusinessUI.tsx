import {Input} from './ui/input';
import {Button} from './ui/button';
import {cloneElement, useId, useState, type FormEvent, type ReactElement, type ReactNode} from 'react';
import {SearchX} from 'lucide-react';
import {StatusMessage} from './StatusMessage';
import {ApiError} from '../api/client';
import type {PageData} from '../api/business';
import {Table as ShadcnTable, TableHeader, TableBody, TableRow, TableHead} from './ui/table';

export function Heading({title, description, eyebrow = '门诊业务工作台', children}: {
  title: string;
  description: string;
  eyebrow?: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {children}
    </div>
  );
}

export function Field({label, children}: {label: string; children: ReactElement<{id?: string}>}) {
  const generatedId = useId();
  const id = children.props.id || generatedId;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {cloneElement(children, {id})}
    </div>
  );
}

function errorTitle(error: unknown): string {
  if (!(error instanceof ApiError)) return '操作未完成';
  if (error.status === 0) return '暂时连不上后端服务';
  if (error.status === 400) return '这个操作的条件还不满足';
  if (error.status === 401) return '登录已失效';
  if (error.status === 403) return '当前角色没有此权限';
  if (error.status === 404) return '没有找到对应记录';
  if (error.status === 409) return '业务状态已经变化';
  return `操作未完成（${error.status}）`;
}

export function ErrorNotice({error}: {error: unknown}) {
  return error
    ? <StatusMessage tone="error" title={errorTitle(error)}>{error instanceof Error ? error.message : '请稍后重试。'}</StatusMessage>
    : null;
}

export function Table({headers, children, loading = false}: {
  headers: string[];
  children: ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="table-wrap">
      <ShadcnTable>
        <TableHeader>
          <TableRow>{headers.map(h => <TableHead key={h}>{h}</TableHead>)}</TableRow>
        </TableHeader>
        <TableBody>
          {loading
            ? Array.from({length: 4}).map((_, row) => (
                <TableRow key={'skeleton-' + row}>
                  {headers.map((head, col) => (
                    <td key={head + col}>
                      <span className="skeleton-line" style={{width: col === 0 ? '72%' : '48%'}}/>
                    </td>
                  ))}
                </TableRow>
              ))
            : children}
        </TableBody>
      </ShadcnTable>
    </div>
  );
}

export function Pager({data, page, setPage}: {
  data: PageData<unknown> | null;
  page: number;
  setPage: (p: number) => void;
}) {
  if (!data) return null;
  const pages = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <div className="pager">
      <span>共 {data.total} 条 · 第 {page} / {pages} 页</span>
      <Button disabled={page <= 1} onClick={() => setPage(page - 1)} variant="outline">上一页</Button>
      <Button disabled={page * data.page_size >= data.total} onClick={() => setPage(page + 1)} variant="outline">下一页</Button>
    </div>
  );
}

export function Search({onSearch, placeholder = '姓名或患者编号'}: {
  onSearch: (v: string) => void;
  placeholder?: string;
}) {
  const [value, setValue] = useState('');
  function submit(event: FormEvent) {
    event.preventDefault();
    onSearch(value.trim());
  }
  return (
    <form className="filter-bar search-bar" onSubmit={submit}>
      <Field label="搜索"><Input value={value} onChange={e => setValue(e.target.value)} placeholder={placeholder}/></Field>
      <Button variant="secondary">查询</Button>
    </form>
  );
}

export function Empty({visible, title = '暂无符合条件的记录'}: {visible: boolean; title?: string}) {
  if (!visible) return null;
  return (
    <div className="empty-panel">
      <SearchX size={22} strokeWidth={1.6}/>
      <strong style={{fontSize: 13, fontWeight: 550, color: '#6f6f7b'}}>{title}</strong>
      <span style={{fontSize: 11}}>调整筛选条件，或先完成前一步业务。</span>
    </div>
  );
}
