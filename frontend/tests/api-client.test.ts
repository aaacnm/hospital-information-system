import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiClient, ApiError, TOKEN_STORAGE_KEY } from '../src/api/client';

const userPayload = { id: 'u-1', username: 'cashier', display_name: '收费员', roles: ['cashier'] };

afterEach(() => vi.unstubAllGlobals());

describe('apiClient', () => {
  it('adds the bearer token and normalizes login user fields', async () => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, 'token-123');
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ access_token: 'new-token', token_type: 'bearer', user: userPayload }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await apiClient.login('cashier', 'secret');

    expect(result.user).toEqual({ id: 'u-1', username: 'cashier', displayName: '收费员', roles: ['cashier'] });
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
      method: 'POST',
      headers: expect.any(Headers),
    }));
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(new Headers(request.headers).get('Authorization')).toBe('Bearer token-123');
    expect(request.body).toBeInstanceOf(URLSearchParams);
    expect((request.body as URLSearchParams).toString()).toBe('username=cashier&password=secret');
  });

  it('maps 401 to an ApiError with a re-login message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ code: 'AUTH_EXPIRED' }), { status: 401 })));
    await expect(apiClient.me()).rejects.toMatchObject({ status: 401, message: '登录已失效，请重新登录。' });
    await expect(apiClient.me()).rejects.toBeInstanceOf(ApiError);
  });

  it('preserves structured 403 messages', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ message: '需要管理员角色' }), { status: 403 })));
    await expect(apiClient.me()).rejects.toMatchObject({ status: 403, message: '需要管理员角色' });
  });

  it('returns a clear status-zero error when the API cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')));
    await expect(apiClient.me()).rejects.toMatchObject({ status: 0, message: expect.stringContaining('无法连接后端服务') });
  });
});
