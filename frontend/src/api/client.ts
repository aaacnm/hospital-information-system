import type { ApiErrorPayload, ApiUserPayload, LoginResponse, User } from './types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
export const TOKEN_STORAGE_KEY = 'his_access_token';

function normalizeUser(payload: ApiUserPayload | User): User {
  const apiPayload = payload as ApiUserPayload;
  return {
    id: String(payload.id),
    username: payload.username,
    displayName: apiPayload.displayName ?? apiPayload.display_name ?? payload.username,
    roles: apiPayload.roles ?? (apiPayload.role ? [apiPayload.role] : []),
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: unknown;

  constructor(status: number, payload: ApiErrorPayload, fallbackMessage: string) {
    super(payload.message || fallbackMessage);
    this.name = 'ApiError';
    this.status = status;
    this.code = payload.code;
    this.details = payload.details;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload = {};
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    // Some gateways return an empty response for errors.
  }
  const detail = typeof payload.detail === 'object' && payload.detail !== null ? payload.detail : {};
  const detailMessage = typeof payload.detail === 'string' ? payload.detail : detail.message;
  const detailCode = typeof payload.detail === 'object' && payload.detail !== null ? detail.code : undefined;
  const normalizedPayload = { ...payload, code: payload.code ?? detailCode, message: payload.message ?? detailMessage };
  const fallback = response.status === 401
    ? '登录已失效，请重新登录。'
    : response.status === 403
      ? '当前账号没有执行此操作的权限。'
      : `请求失败（${response.status}）`;
  return new ApiError(response.status, normalizedPayload, fallback);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, {}, `无法连接后端服务（${API_BASE_URL}）。请先启动 API。`);
  }
  if (!response.ok) {
    if (response.status === 401) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
      window.dispatchEvent(new Event('his:unauthorized'));
    }
    throw await parseError(response);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const apiClient = {
  put<T>(path: string, body: unknown): Promise<T> { return request<T>(path, {method:'PUT',body:JSON.stringify(body)}); },
  patch<T>(path: string, body: unknown): Promise<T> { return request<T>(path, {method:'PATCH',body:JSON.stringify(body)}); },
  upload<T>(path: string, body: FormData): Promise<T> {return request<T>(path,{method:'POST',body});},
  async download(path: string, name: string) {
    const data = await request<{csv:string}>(path,{method:'POST'});
    const url = URL.createObjectURL(new Blob([data.csv.startsWith('\ufeff')?data.csv:'\ufeff'+data.csv],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download=name;link.click();URL.revokeObjectURL(url);
  },
  async login(username: string, password: string): Promise<LoginResponse> {
    const body = new URLSearchParams({ username, password });
    const response = await request<LoginResponse>('/auth/login', { method: 'POST', body, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
    return response.user ? { ...response, user: normalizeUser(response.user) } : response;
  },
  async me(): Promise<User> { return normalizeUser(await request<ApiUserPayload | User>('/auth/me')); },
  get<T>(path: string): Promise<T> { return request<T>(path); },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, body === undefined ? { method: 'POST' } : { method: 'POST', body: JSON.stringify(body) });
  },
};
