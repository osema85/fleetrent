import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setAccessToken } from '../api/client';
import type { Customer } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Alert, Field, PageHeader } from '../components/ui';
import { label } from '../utils';

function ChangePassword() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (form.new_password !== form.confirm) return setError('New passwords do not match');
    try {
      await api('/auth/change-password', {
        method: 'POST',
        body: { current_password: form.current_password, new_password: form.new_password },
      });
      // All sessions were revoked by the server: sign in again with the new password
      setAccessToken(null);
      await logout().catch(() => undefined);
      navigate('/login');
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h2>Change password</h2>
      <p className="muted">You will be signed out on all devices.</p>
      <Alert>{error}</Alert>
      <div className="grid-3">
        <Field label="Current password"><input type="password" required autoComplete="current-password" value={form.current_password} onChange={(e) => setForm({ ...form, current_password: e.target.value })} /></Field>
        <Field label="New password" hint="12+ characters with upper & lower case, a digit and a symbol"><input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} /></Field>
        <Field label="Confirm new password"><input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} /></Field>
      </div>
      <button className="btn btn-primary">Change password</button>
    </form>
  );
}

function CustomerProfile() {
  const [c, setC] = useState<Customer | null>(null);
  const [form, setForm] = useState({ phone: '', address: '', city: '', country: '', driver_license_number: '', license_country: '', license_expiry: '' });
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    api<Customer>('/customers/me').then((data) => {
      setC(data);
      setForm({
        phone: data.phone, address: data.address ?? '', city: data.city ?? '', country: data.country ?? '',
        driver_license_number: data.driver_license_number, license_country: data.license_country, license_expiry: data.license_expiry,
      });
    }).catch((e: Error) => setError(e.message));
  }, []);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg('');
    setError('');
    try {
      const body = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v === '' ? null : v]));
      setC(await api<Customer>('/customers/me', { method: 'PATCH', body }));
      setMsg('Profile updated.');
    } catch (err) {
      setError((err as Error).message);
    }
  }
  if (!c) return <Alert>{error}</Alert>;
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  return (
    <form className="card" onSubmit={submit}>
      <h2>Driver profile</h2>
      <p className="muted">{c.first_name} {c.last_name} · {c.email} · born {c.date_of_birth}</p>
      <Alert>{error}</Alert>
      <Alert kind="success">{msg}</Alert>
      <div className="grid-3">
        <Field label="Phone"><input type="tel" required value={form.phone} onChange={set('phone')} /></Field>
        <Field label="Address"><input maxLength={255} value={form.address} onChange={set('address')} /></Field>
        <Field label="City"><input maxLength={100} value={form.city} onChange={set('city')} /></Field>
        <Field label="Country"><input maxLength={100} value={form.country} onChange={set('country')} /></Field>
        <Field label="Driver license no."><input required maxLength={50} value={form.driver_license_number} onChange={set('driver_license_number')} /></Field>
        <Field label="License country"><input required maxLength={100} value={form.license_country} onChange={set('license_country')} /></Field>
        <Field label="License expiry"><input type="date" required value={form.license_expiry} onChange={set('license_expiry')} /></Field>
      </div>
      <button className="btn btn-primary">Save profile</button>
    </form>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <>
      <PageHeader title="My profile" />
      <section className="card">
        <h2>Account</h2>
        <dl className="details">
          <dt>Name</dt><dd>{user.full_name}</dd>
          <dt>Email</dt><dd>{user.email}</dd>
          <dt>Role</dt><dd>{label(user.role)}</dd>
        </dl>
      </section>
      {user.role === 'customer' && <CustomerProfile />}
      <ChangePassword />
    </>
  );
}
