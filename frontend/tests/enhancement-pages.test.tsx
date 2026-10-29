import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,expect,it,vi} from 'vitest';
import {ClinicalRecordEditor} from '../src/pages/ClinicalExtensions';
import {FinancialRecordsPage,InventoryCenterPage} from '../src/pages/OperationsPages';
import type {ClinicalNote} from '../src/api/enhancements';

vi.mock('../src/auth/AuthContext',()=>({useAuth:()=>({user:{roles:['doctor']}})}));
const response=(value:unknown)=>Promise.resolve(new Response(JSON.stringify(value),{status:200}));
const paged=(items:unknown[])=>({items,total:items.length,page:1,page_size:20});

describe('visible outpatient enhancements',()=>{
  it('keeps the saved clinical note and success message after refreshing from the server',async()=>{
    let saved:ClinicalNote|null=null;
    const request=vi.fn().mockImplementation((_url:string,init?:RequestInit)=>{
      if(init?.method==='PUT'){
        saved={...JSON.parse(String(init.body)),id:1,signed_at:null,updated_at:'2026-10-29T08:00:00Z'};
        return response(saved);
      }
      return response({registration_id:7,patient:{id:2,name:'虚构患者甲',patient_no:'DEMO-001'},record:saved,locked:false});
    });
    vi.stubGlobal('fetch',request);
    render(<MemoryRouter><ClinicalRecordEditor registrationId={7} version={0}/></MemoryRouter>);
    fireEvent.click(await screen.findByRole('button',{name:'填入教学示例'}));
    fireEvent.click(screen.getByRole('button',{name:'保存诊疗记录'}));
    expect(await screen.findByText('诊疗记录已保存')).toBeInTheDocument();
    await waitFor(()=>expect(screen.getByLabelText('主诉')).toHaveValue('咽部不适伴低热2天（虚构教学示例）'));
    expect(request.mock.calls.some(([,init])=>init?.method==='PUT')).toBe(true);
    expect(screen.getByText('诊疗记录已保存')).toBeInTheDocument();
  });

  it('offers refunds only before dispensing and updates the visible record after refund',async()=>{
    let refunded=false;
    vi.stubGlobal('fetch',vi.fn().mockImplementation((_url:string,init?:RequestInit)=>{
      if(init?.method==='POST'){refunded=true;return response({amount:'25.00'});}
      return response(paged([
        {id:1,prescription_id:4,receipt_no:'CH-000001',patient_name:'虚构患者甲',patient_no:'P-1',amount:'25.00',payment_method:'现金',status:refunded?'refunded':'completed',prescription_status:refunded?'已退费':'已收费',paid_at:'2026-10-29T08:00:00Z',cashier:'演示收费员'},
        {id:2,prescription_id:5,receipt_no:'CH-000002',patient_name:'虚构患者乙',patient_no:'P-2',amount:'12.00',payment_method:'现金',status:'completed',prescription_status:'已发药',paid_at:'2026-10-29T08:00:00Z',cashier:'演示收费员'},
      ]));
    }));
    render(<FinancialRecordsPage/>);
    fireEvent.click(await screen.findByRole('button',{name:'申请退费'}));
    expect(screen.getAllByRole('button',{name:'申请退费'})).toHaveLength(1);
    fireEvent.change(screen.getByLabelText('退费原因'),{target:{value:'患者取消本次教学处方'}});
    fireEvent.click(screen.getByRole('button',{name:'确认退费并回库'}));
    expect(await screen.findByText('退费完成')).toBeInTheDocument();
    await waitFor(()=>expect(screen.queryByRole('button',{name:'申请退费'})).not.toBeInTheDocument());
    expect(screen.getAllByRole('link',{name:'打印凭证'})).toHaveLength(2);
  });

  it('switches between stock alerts and batch movement history',async()=>{
    const request=vi.fn().mockImplementation((url:string)=>{
      if(url.includes('/drug-list'))return response(paged([]));
      if(url.includes('/stock-movements'))return response(paged([{id:1,drug_id:1,stock_id:1,prescription_id:4,kind:'收费出库',quantity_delta:-2,balance_after:8,created_at:'2026-10-29T08:00:00Z',generic_name:'教学药品',specification:'10mg',batch_no:'BATCH-001',expiry_date:'2027-01-01',operator:'演示收费员'}]));
      return response(paged([{id:1,generic_name:'教学药品',specification:'10mg',stock_qty:10,available_stock:8,expiring_quantity:2,expired_quantity:2,nearest_expiry:'2026-11-10'}]));
    });
    vi.stubGlobal('fetch',request);
    render(<InventoryCenterPage/>);
    expect(await screen.findByText('教学药品')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:/近效期/}));
    await waitFor(()=>expect(request.mock.calls.some(([url])=>String(url).includes('kind=expiring'))).toBe(true));
    fireEvent.click(screen.getByRole('button',{name:'出入库流水'}));
    expect(await screen.findByText('BATCH-001')).toBeInTheDocument();
    expect(screen.getByText('-2')).toBeInTheDocument();
    expect(screen.getByRole('cell',{name:'收费出库'})).toBeInTheDocument();
  });
});
