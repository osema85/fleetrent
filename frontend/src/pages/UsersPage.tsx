import { useState, type FormEvent } from 'react';
import { api } from '../api/client';
import type { Branch, Page, Role, User } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Alert, Badge, Empty, Field, Loading, Modal, PageHeader, Pager } from '../components/ui';
import { dateTime, label, useAsync } from '../utils';

const LIMIT = 25;
const ROLES: Role[] = ['admin', 'manager', 'agent', 'customer'];
const PW_HINT = '12+ characters with upper & lower case, a digit and a symbol';

function UserForm({ user, branches, onDone }: { user: User | null; branches: Branch[]; onDone: () => void }) {
  const [form, setForm] = useState({
    email: user?.email ?? '', full_name: user?.full_name ?? '', role: user?.role ?? ('agent' as Role),
    branch_id: user?.branch_id ?? '', password: '', is_active: user?.is_active ?? true,
  });
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      if (user) {
        await api(`/users/${user.id}`, {
          method: 'PATCH',
          body: { full_name: form.full_name, role: form.role, branch_id: form.branch_id || null, is_active: form.is_active },
        });
      } else {
        await api('/users', {
          method: 'POST',
          body: { email: form.email, full_name: form.full_name, role: form.role, branch_id: form.branch_id || null, password: form.password },
        });
      }
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form onSubmit={submit}>
      <Alert>{error}</Alert>
      <div className="grid-2">
        <Field label="Email"><input type="email" required disabled={!!user} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        <Field label="Full name"><input required maxLength={150} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
        <Field label="Role">
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
            {ROLES.map((r) => <option key={r} value={r}>{label(r)}</option>)}
          </select>
        </Field>
        <Field label="Branch">
          <select value={form.branch_id} onChange={(e) => setForm({ ...form, branch_id: e.target.value })}>
            <option value="">— none —</option>
            {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </Field>
        {!user && (
          <Field label="Initial password" hint={PW_HINT}>
            <input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </Field>
        )}
      </div>
      {user && <label className="check"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Account active</label>}
      <div className="form-actions"><button className="btn btn-primary">{user ? 'Save' : 'Create user'}</button></div>
    </form>
  );
}

function ResetPassword({ user, onDone }: { user: User; onDone: () => void }) {
  const [pw, setPw] = useState('');
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api(`/users/${user.id}/reset-password`, { method: 'POST', body: { new_password: pw } });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form onSubmit={submit}>
      <Alert>{error}</Alert>
      <p className="muted">All of {user.full_name}'s sessions will be signed out. Share the new password through a secure channel.</p>
      <Field label="New password" hint={PW_HINT}>
        <input type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} />
      </Field>
      <div className="form-actions"><button className="btn btn-primary">Reset password</button></div>
    </form>
  );
}

export default function UsersPage() {
  const { user: me } = useAuth();
  const [q, setQ] = useState('');
  const [role, setRole] = useState('');
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<User | null | undefined>(undefined);
  const [resetting, setResetting] = useState<User | null>(null);
  const [msg, setMsg] = useState('');
  const branches = useAsync(() => api<Branch[]>('/branches'), []);
  const list = useAsync(() => api<Page<User>>('/users', { query: { q, role, limit: LIMIT, offset } }), [q, role, offset]);

  async function unlock(u: User) {
    await api(`/users/${u.id}/unlock`, { method: 'POST' });
    setMsg(`${u.email} unlocked.`);
    list.reload();
  }

  return (
    <>
      <PageHeader title="Users" actions={<button className="btn btn-primary" onClick={() => setEditing(null)}>Add user</button>} />
      <div className="filters">
        <input placeholder="Search name or email…" value={q} onChange={(e) => { setOffset(0); setQ(e.target.value); }} />
        <select value={role} onChange={(e) => { setOffset(0); setRole(e.target.value); }}>
          <option value="">All roles</option>
          {ROLES.map((r) => <option key={r} value={r}>{label(r)}</option>)}
        </select>
      </div>
      <Alert kind="success">{msg}</Alert>
      <Alert>{list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.items.length ? <Empty>No users.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Last login</th><th>Status</th><th /></tr></thead>
            <tbody>
              {list.data.items.map((u) => {
                const locked = u.locked_until && new Date(u.locked_until) > new Date();
                return (
                  <tr key={u.id}>
                    <td>{u.full_name}{u.id === me?.id && <span className="muted"> (you)</span>}</td>
                    <td>{u.email}</td>
                    <td>{label(u.role)}</td>
                    <td>{dateTime(u.last_login_at)}</td>
                    <td>{locked ? <Badge value="locked" /> : <Badge value={u.is_active ? 'active' : 'inactive'} />}</td>
                    <td className="nowrap">
                      <button className="btn btn-sm" onClick={() => setEditing(u)}>Edit</button>
                      <button className="btn btn-sm" onClick={() => setResetting(u)}>Reset password</button>
                      {locked && <button className="btn btn-sm" onClick={() => unlock(u)}>Unlock</button>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
      {editing !== undefined && (
        <Modal title={editing ? `Edit ${editing.email}` : 'Add user'} onClose={() => setEditing(undefined)}>
          <UserForm user={editing} branches={branches.data ?? []} onDone={() => { setEditing(undefined); list.reload(); }} />
        </Modal>
      )}
      {resetting && (
        <Modal title={`Reset password — ${resetting.email}`} onClose={() => setResetting(null)}>
          <ResetPassword user={resetting} onDone={() => { setMsg(`Password reset for ${resetting.email}.`); setResetting(null); }} />
        </Modal>
      )}
    </>
  );
}
