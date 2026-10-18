import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../src/auth/AuthContext';
import { ProtectedRoute } from '../src/components/ProtectedRoute';

function TestRoutes() {
  return <MemoryRouter initialEntries={['/secure']}><AuthProvider><Routes><Route path="/login" element={<h1>登录页</h1>} /><Route element={<ProtectedRoute />}><Route path="/secure" element={<h1>安全页面</h1>} /></Route></Routes></AuthProvider></MemoryRouter>;
}

describe('ProtectedRoute', () => {
  it('redirects users without a token to login', async () => {
    render(<TestRoutes />);
    expect(await screen.findByRole('heading', { name: '登录页' })).toBeInTheDocument();
  });

  it('allows a valid token after /auth/me succeeds', async () => {
    window.localStorage.setItem('his_access_token', 'valid-token');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'u-1', username: 'doctor', display_name: '医生', roles: ['doctor'] }), { status: 200 })));
    render(<TestRoutes />);
    expect(await screen.findByRole('heading', { name: '安全页面' })).toBeInTheDocument();
  });

  it('clears an expired token and returns to login after a 401', async () => {
    window.localStorage.setItem('his_access_token', 'expired-token');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: 'AUTH_EXPIRED' }), { status: 401 })));
    render(<TestRoutes />);
    await waitFor(() => expect(window.localStorage.getItem('his_access_token')).toBeNull());
    expect(await screen.findByRole('heading', { name: '登录页' })).toBeInTheDocument();
  });
});
