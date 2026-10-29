import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../src/auth/AuthContext';
import { LoginPage } from '../src/pages/LoginPage';

describe('LoginPage', () => {
  it('opens the workbench when a different role logs in from an old protected page', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({access_token:'demo-token'}), {status:200}))
      .mockResolvedValueOnce(new Response(JSON.stringify({id:4,username:'pharmacist.demo',display_name:'药师',role:'pharmacist'}), {status:200})));
    render(<MemoryRouter initialEntries={[{pathname:'/login',state:{from:'/reports'}}]}><AuthProvider><Routes><Route path="/login" element={<LoginPage/>}/><Route path="/" element={<h1>角色工作台</h1>}/><Route path="/reports" element={<h1>上一账号页面</h1>}/></Routes></AuthProvider></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', {name:'药师'}));
    fireEvent.click(screen.getByRole('button', {name:'登录工作台'}));
    expect(await screen.findByRole('heading', {name:'角色工作台'})).toBeInTheDocument();
    expect(screen.queryByRole('heading', {name:'上一账号页面'})).not.toBeInTheDocument();
  });
  it('shows the backend error and does not fabricate a successful login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: '用户名或密码错误' }), { status: 401 })));
    render(<MemoryRouter><AuthProvider><LoginPage /></AuthProvider></MemoryRouter>);

    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'demo' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: '登录工作台' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('用户名或密码错误');
    expect(window.localStorage.getItem('his_access_token')).toBeNull();
  });
});
