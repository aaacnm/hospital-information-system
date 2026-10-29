import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { AppLayout } from './components/AppLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AccessDeniedPage } from './pages/AccessDeniedPage';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { BillingPage, DispensingPage, PrescriptionsPage, RegistrationsPage, SchedulesPage } from './pages/ClinicalPages';
import { AccountsPage, AuditLogsPage, DrugsPage, ImportPage, PasswordPage, PatientsPage } from './pages/ManagementPages';
import {PatientTimelinePage, QueueBoardPage} from './pages/ClinicalExtensions';
import {AnalyticsPage, FinancialRecordsPage, InventoryCenterPage} from './pages/OperationsPages';
import {PrintDocumentPage} from './pages/PrintDocumentPage';
import { TriagePage } from './pages/ModulePages';
export default function App() {
    return <BrowserRouter><AuthProvider><Routes><Route path="/login" element={<LoginPage />}/><Route element={<ProtectedRoute />}><Route element={<AppLayout />}>
 <Route index element={<DashboardPage />}/><Route path="triage" element={<TriagePage />}/><Route path="password" element={<PasswordPage />}/><Route path="forbidden" element={<AccessDeniedPage />}/>
 <Route element={<ProtectedRoute roles={['admin', 'doctor', 'cashier']}/>}><Route path="patients" element={<PatientsPage />}/><Route path="schedules" element={<SchedulesPage />}/><Route path="registrations" element={<RegistrationsPage />}/></Route>
 <Route path="prescriptions" element={<PrescriptionsPage />}/>
 <Route path="print/prescriptions/:prescriptionId" element={<PrintDocumentPage/>}/>
 <Route element={<ProtectedRoute roles={['admin','doctor']}/>}><Route path="patients/:patientId/timeline" element={<PatientTimelinePage/>}/></Route>
 <Route element={<ProtectedRoute roles={['admin','doctor','cashier']}/>}><Route path="queue-board" element={<QueueBoardPage/>}/></Route>
 <Route element={<ProtectedRoute roles={['admin','cashier']}/>}><Route path="financial-records" element={<FinancialRecordsPage/>}/><Route path="print/receipts/:prescriptionId" element={<PrintDocumentPage receipt/>}/></Route>
 <Route element={<ProtectedRoute roles={['admin','pharmacist']}/>}><Route path="inventory-center" element={<InventoryCenterPage/>}/></Route>
 <Route element={<ProtectedRoute roles={['admin', 'cashier']}/>}><Route path="billing" element={<BillingPage />}/></Route>
 <Route element={<ProtectedRoute roles={['admin', 'pharmacist']}/>}><Route path="dispensing" element={<DispensingPage />}/><Route path="drugs" element={<DrugsPage />}/></Route>
 <Route element={<ProtectedRoute roles={['admin']}/>}><Route path="audit-logs" element={<AuditLogsPage />}/><Route path="reports" element={<AnalyticsPage />}/><Route path="import" element={<ImportPage />}/><Route path="accounts" element={<AccountsPage />}/></Route>
 </Route></Route><Route path="/404" element={<NotFoundPage />}/><Route path="*" element={<Navigate to="/404" replace/>}/></Routes></AuthProvider></BrowserRouter>;
}
