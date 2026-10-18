import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BillingPage, RegistrationsPage, SchedulesPage } from '../src/pages/ModulePages';

describe('MVP business pages', () => {
  it('renders schedule data returned by the backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify([{ id: 1, doctor_id: 2, doctor_name: '演示医生', department_id: 1, department_name: '内科', visit_date: '2099-01-01', period: '上午', total_quota: 20, remain_quota: 19, status: 'active' }]), { status: 200 })));
    render(<SchedulesPage />);
    fireEvent.click(screen.getByRole('button', { name: '查询排班' }));
    expect(await screen.findByText('演示医生')).toBeInTheDocument();
    expect(screen.getByText('19')).toBeInTheDocument();
  });

  it('shows a 409 conflict without claiming a registration succeeded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'QUOTA_EXHAUSTED', message: '号源已满' } }), { status: 409 })));
    render(<RegistrationsPage />);
    fireEvent.change(screen.getByLabelText('患者 ID'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('排班 ID'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: '确认挂号' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('号源已满');
    expect(screen.queryByText('挂号已由服务端创建')).not.toBeInTheDocument();
  });

  it('maps a 400 charge failure to an error state without an amount result', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: { code: 'INSUFFICIENT_STOCK', message: '库存不足' } }), { status: 400 })));
    render(<BillingPage />);
    fireEvent.change(screen.getByLabelText('收费处方 ID'), { target: { value: '4' } });
    fireEvent.click(screen.getByRole('button', { name: '收费台' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('库存不足');
    expect(screen.queryByText('收费已由服务端确认')).not.toBeInTheDocument();
  });
});
