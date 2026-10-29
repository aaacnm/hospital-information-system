import {Button} from '../components/ui/button';
import {Textarea} from '../components/ui/textarea';
import { useState, type FormEvent, type ReactNode } from 'react';
import { ApiError, apiClient } from '../api/client';
import type { TriageResponse } from '../api/types';
import { StatusMessage } from '../components/StatusMessage';
import { Heading } from '../components/BusinessUI';
function errorTitle(reason: unknown): string {
    if (!(reason instanceof ApiError))
        return '请求失败';
    if (reason.status === 400)
        return '请求参数或业务条件不满足';
    if (reason.status === 401)
        return '登录已失效';
    if (reason.status === 403)
        return '当前角色没有此权限';
    if (reason.status === 409)
        return '业务状态冲突';
    return reason.status === 0 ? '后端服务不可用' : `请求失败（${reason.status}）`;
}
function RequestError({ reason }: {
    reason: unknown;
}) {
    return <StatusMessage tone="error" title={errorTitle(reason)}>{reason instanceof Error ? reason.message : '请稍后重试。'}</StatusMessage>;
}
function Field({ label, children, hint }: {
    label: string;
    children: ReactNode;
    hint?: string;
}) {
    return <label className="field"><span>{label}</span>{children}{hint ? <small>{hint}</small> : null}</label>;
}
export function TriagePage() {
    const [symptoms, setSymptoms] = useState('');
    const [result, setResult] = useState<TriageResponse | null>(null);
    const [error, setError] = useState<unknown>(null);
    const [loading, setLoading] = useState(false);
    async function submit(event: FormEvent) {
        event.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            setResult(await apiClient.post<TriageResponse>('/triage', { symptoms: symptoms.trim() }));
        }
        catch (reason) {
            setError(reason);
        }
        finally {
            setLoading(false);
        }
    }
    const isFallback = result?.source === 'fallback';
    return <section className="page-section"><Heading eyebrow="辅助功能 · F16" title="智能分诊" description="根据症状生成候选科室和紧急程度。此功能只提供辅助建议，不诊断、不处方、不改变收费结果。"/><div className="ai-disclaimer">本建议由 AI 生成，仅供参考，请以医生诊断为准。出现急危重症症状时请立即联系急救服务。</div><form className="form-panel triage-form" onSubmit={submit}><Field label="症状描述" hint="请勿输入姓名、身份证号或手机号"><Textarea aria-label="症状描述" value={symptoms} onChange={(event) => setSymptoms(event.target.value)} required minLength={2} maxLength={1000} placeholder="例如：昨晚开始发热、咽痛，体温 38.2℃"/></Field><Button type="submit" disabled={loading}>{loading ? '分析中…' : '获取辅助建议'}</Button></form>{error ? <RequestError reason={error}/> : null}{result ? <div className={`triage-result ${isFallback ? 'triage-fallback' : ''}`} role="status"><div className="triage-result-heading"><strong>{isFallback ? '暂未获得 AI 建议' : '已获得辅助建议'}</strong><span>{isFallback ? '系统兜底' : 'AI 返回'}</span></div><dl><div><dt>建议科室</dt><dd>{result.dept}</dd></div><div><dt>紧急程度</dt><dd>{result.urgency}</dd></div><div><dt>说明</dt><dd>{result.notes}</dd></div></dl><p className="triage-result-disclaimer">{result.disclaimer || '本建议由 AI 生成，仅供参考，请以医生诊断为准。'}</p></div> : null}</section>;
}
