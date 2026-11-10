import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Alert, Field } from '../components/ui';

const EMPTY = {
  email: '',
  password: '',
  confirm: '',
  first_name: '',
  last_name: '',
  phone: '',
  date_of_birth: '',
  driver_license_number: '',
  license_country: '',
  license_expiry: '',
};

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError('Passwords do not match');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const { confirm: _confirm, ...body } = form;
      await api('/auth/register', { method: 'POST', body });
      await login(form.email, form.password);
      navigate('/browse', { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card wide" onSubmit={submit}>
        <h1 className="brand-lg">Create your account</h1>
        <p className="muted">Book cars online and manage your reservations.</p>
        <Alert>{error}</Alert>
        <div className="grid-2">
          <Field label="First name">
            <input required maxLength={100} value={form.first_name} onChange={set('first_name')} />
          </Field>
          <Field label="Last name">
            <input required maxLength={100} value={form.last_name} onChange={set('last_name')} />
          </Field>
          <Field label="Email">
            <input type="email" required autoComplete="email" value={form.email} onChange={set('email')} />
          </Field>
          <Field label="Phone">
            <input type="tel" required value={form.phone} onChange={set('phone')} placeholder="+1 555 0100" />
          </Field>
          <Field label="Date of birth">
            <input type="date" required value={form.date_of_birth} onChange={set('date_of_birth')} />
          </Field>
          <Field label="Driver license number">
            <input required maxLength={50} value={form.driver_license_number} onChange={set('driver_license_number')} />
          </Field>
          <Field label="License issuing country">
            <input required maxLength={100} value={form.license_country} onChange={set('license_country')} />
          </Field>
          <Field label="License expiry date">
            <input type="date" required value={form.license_expiry} onChange={set('license_expiry')} />
          </Field>
          <Field label="Password" hint="12+ characters with upper & lower case, a digit and a symbol">
            <input type="password" required minLength={12} maxLength={128} autoComplete="new-password"
              value={form.password} onChange={set('password')} />
          </Field>
          <Field label="Confirm password">
            <input type="password" required minLength={12} maxLength={128} autoComplete="new-password"
              value={form.confirm} onChange={set('confirm')} />
          </Field>
        </div>
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted center">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
