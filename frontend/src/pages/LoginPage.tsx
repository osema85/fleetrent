import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { Alert, Field } from '../components/ui';

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={user.role === 'customer' ? '/browse' : '/'} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const u = await login(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      // Only same-app paths: blocks open redirects like "//evil.com" or "/\evil.com"
      const safe = typeof from === 'string' && /^\/(?![/\\])/.test(from) && from !== '/login';
      navigate(safe ? from : u.role === 'customer' ? '/browse' : '/', { replace: true });
    } catch (err) {
      setError((err as Error).message);
      setPassword('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={submit}>
        <h1 className="brand-lg">FleetRent</h1>
        <p className="muted">Sign in to your account</p>
        <Alert>{error}</Alert>
        <Field label="Email">
          <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password">
          <input
            type="password"
            autoComplete="current-password"
            required
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="muted center">
          New customer? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </div>
  );
}
