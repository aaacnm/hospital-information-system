import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { StatusMessage } from './StatusMessage';

export function ProtectedRoute() {
  const { user, isLoading, error } = useAuth();
  const location = useLocation();
  if (isLoading) return <div className="screen-center"><StatusMessage title="正在确认登录状态" /></div>;
  if (error) return <div className="screen-center"><StatusMessage tone="error" title="登录状态不可用">{error}</StatusMessage></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}
