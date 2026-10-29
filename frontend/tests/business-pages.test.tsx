import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BillingPage, SchedulesPage } from '../src/pages/ClinicalPages';
vi.mock('../src/auth/AuthContext', () => ({ useAuth: () => ({ user: { roles: ['cashier'] } }) }));
const rx = { id: 4, patient_name: '演示患者', patient_no: 'P-1', status: '待收费', diagnosis_name: '演示诊断', diagnosis_code: 'J06.9', total_amount: '25.00', items: [{ id: 1, drug_id: 1, drug_name: '演示药', specification: '10mg', quantity: 2, unit_price: '12.50' }] };
describe('business work queues', () => {
    it('shows server schedules with names rather than requiring IDs', async () => {
        vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(new Response(JSON.stringify(url.includes('/directory') ? { date: '2099-01-01', departments: [], doctors: [] } : [{ id: 1, doctor_name: '演示医生', department_name: '内科', visit_date: '2099-01-01', period: '上午', total_quota: 20, remain_quota: 19 }]), { status: 200 }))));
        render(<SchedulesPage />);
        expect(await screen.findByText('演示医生')).toBeInTheDocument();
        expect(screen.getByText('19')).toBeInTheDocument();
        expect(screen.queryByLabelText('科室 ID')).not.toBeInTheDocument();
    });
    it('shows the invoice amount before charge and never claims a failed charge succeeded', async () => {
        vi.stubGlobal('fetch', vi.fn().mockImplementation((_url: string, init: RequestInit) => Promise.resolve(init?.method === 'POST' ? new Response(JSON.stringify({ detail: { code: 'INSUFFICIENT_STOCK', message: '库存不足' } }), { status: 400 }) : new Response(JSON.stringify({ items: [rx], total: 1, page: 1, page_size: 20 }), { status: 200 }))));
        render(<BillingPage />);
        fireEvent.click(await screen.findByRole('button', { name: '核对明细' }));
        expect(screen.getByText('应付金额 ¥ 25.00')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: '确认收费' }));
        expect(await screen.findByRole('alert')).toHaveTextContent('库存不足');
        expect(screen.queryByText('收费成功')).not.toBeInTheDocument();
    });
});
