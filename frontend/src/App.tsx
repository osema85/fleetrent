import { Navigate, Route, Routes } from 'react-router-dom';
import { MANAGERS, STAFF, useAuth } from './auth/AuthContext';
import Layout from './components/Layout';
import RequireRole from './components/RequireRole';
import AuditPage from './pages/AuditPage';
import BookingPage from './pages/BookingPage';
import BranchesPage from './pages/BranchesPage';
import CarsPage from './pages/CarsPage';
import CustomerDetailPage from './pages/CustomerDetailPage';
import CustomersPage from './pages/CustomersPage';
import DashboardPage from './pages/DashboardPage';
import HelpPage from './pages/HelpPage';
import InvoicePage from './pages/InvoicePage';
import LoginPage from './pages/LoginPage';
import MaintenancePage from './pages/MaintenancePage';
import PaymentsPage from './pages/PaymentsPage';
import ProfilePage from './pages/ProfilePage';
import RegisterPage from './pages/RegisterPage';
import RentalsPage from './pages/RentalsPage';
import ReservationDetailPage from './pages/ReservationDetailPage';
import ReservationsPage from './pages/ReservationsPage';
import UsersPage from './pages/UsersPage';

function Home() {
  const { user } = useAuth();
  return user?.role === 'customer' ? <Navigate to="/browse" replace /> : <DashboardPage />;
}

export default function App() {
  const staff = (el: JSX.Element) => <RequireRole roles={STAFF}>{el}</RequireRole>;
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<RequireRole><Layout /></RequireRole>}>
        <Route index element={<Home />} />
        <Route path="browse" element={<RequireRole roles={['customer']}><BookingPage /></RequireRole>} />
        <Route path="reservations" element={<ReservationsPage />} />
        <Route path="reservations/new" element={staff(<BookingPage />)} />
        <Route path="reservations/:id" element={<ReservationDetailPage />} />
        <Route path="reservations/:id/invoice" element={<InvoicePage />} />
        <Route path="rentals" element={staff(<RentalsPage />)} />
        <Route path="customers" element={staff(<CustomersPage />)} />
        <Route path="customers/:id" element={staff(<CustomerDetailPage />)} />
        <Route path="cars" element={staff(<CarsPage />)} />
        <Route path="maintenance" element={staff(<MaintenancePage />)} />
        <Route path="payments" element={staff(<PaymentsPage />)} />
        <Route path="branches" element={<RequireRole roles={MANAGERS}><BranchesPage /></RequireRole>} />
        <Route path="users" element={<RequireRole roles={['admin']}><UsersPage /></RequireRole>} />
        <Route path="audit" element={<RequireRole roles={['admin']}><AuditPage /></RequireRole>} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="help" element={<HelpPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
