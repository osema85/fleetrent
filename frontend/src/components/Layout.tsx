import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import type { Role } from '../api/types';
import { MANAGERS, STAFF, useAuth } from '../auth/AuthContext';
import { label } from '../utils';

const NAV: { to: string; text: string; roles: Role[] }[] = [
  { to: '/', text: 'Dashboard', roles: STAFF },
  { to: '/reservations', text: 'Reservations', roles: STAFF },
  { to: '/rentals', text: 'Rentals', roles: STAFF },
  { to: '/customers', text: 'Customers', roles: STAFF },
  { to: '/cars', text: 'Fleet', roles: STAFF },
  { to: '/maintenance', text: 'Maintenance', roles: STAFF },
  { to: '/payments', text: 'Payments', roles: STAFF },
  { to: '/branches', text: 'Branches', roles: MANAGERS },
  { to: '/users', text: 'Users', roles: ['admin'] },
  { to: '/audit', text: 'Audit log', roles: ['admin'] },
  { to: '/browse', text: 'Book a car', roles: ['customer'] },
  { to: '/reservations', text: 'My reservations', roles: ['customer'] },
  { to: '/profile', text: 'My profile', roles: ['admin', 'manager', 'agent', 'customer'] },
  { to: '/help', text: 'Help', roles: ['admin', 'manager', 'agent', 'customer'] },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  if (!user) return null;

  const links = NAV.filter((n) => n.roles.includes(user.role));

  return (
    <div className="shell">
      <header className="topbar">
        <button className="btn-icon menu-toggle" onClick={() => setOpen(!open)} aria-label="Menu">
          ☰
        </button>
        <span className="brand">FleetRent</span>
        <span className="spacer" />
        <span className="user-chip">
          {user.full_name} <span className="muted">· {label(user.role)}</span>
        </span>
        <button
          className="btn"
          onClick={async () => {
            await logout();
            navigate('/login');
          }}
        >
          Log out
        </button>
      </header>
      <nav className={`sidebar ${open ? 'open' : ''}`} onClick={() => setOpen(false)}>
        {links.map((n) => (
          <NavLink key={n.to + n.text} to={n.to} end={n.to === '/'}>
            {n.text}
          </NavLink>
        ))}
      </nav>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
