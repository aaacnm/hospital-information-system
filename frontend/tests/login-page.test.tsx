import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../src/auth/AuthContext';
import { LoginPage } from '../src/pages/LoginPage';

describe('LoginPage', () => {
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
