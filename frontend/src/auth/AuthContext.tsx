/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren } from 'react';
import { apiClient, ApiError, TOKEN_STORAGE_KEY } from '../api/client';
import type { User } from '../api/types';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setUser(null);
    setError(null);
  }, []);

  useEffect(() => {
    window.addEventListener('his:unauthorized', logout);
    const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) { setIsLoading(false); return () => window.removeEventListener('his:unauthorized', logout); }
    apiClient.me().then(setUser).catch((reason: unknown) => {
      if (reason instanceof ApiError && reason.status === 401) logout();
      else setError(reason instanceof Error ? reason.message : '无法恢复登录状态。');
    }).finally(() => setIsLoading(false));
    return () => window.removeEventListener('his:unauthorized', logout);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    setError(null);
    setIsLoading(true);
    try {
      const response = await apiClient.login(username, password);
      window.localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
      setUser(response.user ? response.user as User : await apiClient.me());
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : '登录失败，请稍后重试。');
      throw reason;
    } finally { setIsLoading(false); }
  }, []);

  const value = useMemo(() => ({ user, isLoading, error, login, logout, clearError: () => setError(null) }), [user, isLoading, error, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
