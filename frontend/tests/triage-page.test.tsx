import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { TriagePage } from '../src/pages/ModulePages';

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText('症状描述'), { target: { value: '发热和咽痛' } });
  fireEvent.click(screen.getByRole('button', { name: '获取辅助建议' }));
}

describe('TriagePage', () => {
  it('shows the fixed disclaimer and a normal backend result', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ dept: '全科门诊', urgency: '普通', notes: '建议到院进一步判断', source: 'llm' }), { status: 200 })));
    render(<TriagePage />);
    expect(screen.getByText(/本建议由 AI 生成，仅供参考，请以医生诊断为准/)).toBeInTheDocument();
    fillAndSubmit();
    expect(await screen.findByText('全科门诊')).toBeInTheDocument();
    expect(screen.getByText('AI 返回')).toBeInTheDocument();
  });

  it('renders a backend fallback result as degraded, not as an AI success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ dept: '全科门诊', urgency: '普通', notes: '请由医生进一步判断', disclaimer: '固定免责声明', source: 'fallback' }), { status: 200 })));
    render(<TriagePage />);
    fillAndSubmit();
    expect(await screen.findByText('暂未获得 AI 建议')).toBeInTheDocument();
    expect(screen.getByText('系统兜底')).toBeInTheDocument();
    expect(screen.getByText('固定免责声明')).toBeInTheDocument();
  });

  it('shows a network failure state without fabricating a triage result', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    render(<TriagePage />);
    fillAndSubmit();
    expect(await screen.findByRole('alert')).toHaveTextContent('无法连接后端服务');
    expect(screen.queryByText('已获得辅助建议')).not.toBeInTheDocument();
    expect(screen.queryByText('暂未获得 AI 建议')).not.toBeInTheDocument();
  });
});
