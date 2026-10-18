import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { AppLayout } from './components/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AccessDeniedPage } from './pages/AccessDeniedPage';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { AuditLogsPage, BillingPage, DispensingPage, PrescriptionsPage, RegistrationsPage, SchedulesPage } from './pages/ModulePages';

export default function App() {
  return <BrowserRouter><AuthProvider><Routes><Route path="/login" element={<LoginPage />} /><Route element={<ProtectedRoute />}><Route element={<AppLayout />}><Route index element={<DashboardPage />} /><Route path="schedules" element={<SchedulesPage />} /><Route path="registrations" element={<RegistrationsPage />} /><Route path="prescriptions" element={<PrescriptionsPage />} /><Route path="billing" element={<BillingPage />} /><Route path="dispensing" element={<DispensingPage />} /><Route path="audit-logs" element={<AuditLogsPage />} /><Route path="forbidden" element={<AccessDeniedPage />} /></Route></Route><Route path="/404" element={<NotFoundPage />} /><Route path="*" element={<Navigate to="/404" replace />} /></Routes></AuthProvider></BrowserRouter>;
}
