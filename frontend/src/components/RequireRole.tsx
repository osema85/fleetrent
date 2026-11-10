import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { Role } from '../api/types';
import { useAuth } from '../auth/AuthContext';

/**
 * UI-level guard for convenience only. Real authorization is enforced by the API on every
 * request; hiding a page here is never relied upon for security.
 */
export default function RequireRole({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="muted pad">Loading…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={user.role === 'customer' ? '/browse' : '/'} replace />;
  }
  return <>{children}</>;
}
