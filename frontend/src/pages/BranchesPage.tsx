import { useState, type FormEvent } from 'react';
import { api } from '../api/client';
import type { Branch } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Alert, Badge, Empty, Field, Loading, Modal, PageHeader } from '../components/ui';
import { useAsync } from '../utils';

function BranchForm({ branch, onDone }: { branch: Branch | null; onDone: () => void }) {
  const [form, setForm] = useState({
    name: branch?.name ?? '', address: branch?.address ?? '', city: branch?.city ?? '',
    phone: branch?.phone ?? '', email: branch?.email ?? '', is_active: branch?.is_active ?? true,
  });
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    const { is_active, ...rest } = form;
    const body = { ...rest, email: form.email || null, ...(branch ? { is_active } : {}) };
    try {
      await api(branch ? `/branches/${branch.id}` : '/branches', { method: branch ? 'PATCH' : 'POST', body });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form onSubmit={submit}>
      <Alert>{error}</Alert>
      <div className="grid-2">
        <Field label="Name"><input required maxLength={120} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="City"><input required maxLength={100} value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></Field>
        <Field label="Address"><input required maxLength={255} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
        <Field label="Phone"><input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
        <Field label="Email"><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
      </div>
      {branch && (
        <label className="check"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Branch is open</label>
      )}
      <div className="form-actions"><button className="btn btn-primary">Save</button></div>
    </form>
  );
}

export default function BranchesPage() {
  const { hasRole } = useAuth();
  const isAdmin = hasRole('admin');
  const list = useAsync(() => api<Branch[]>('/branches'), []);
  const [editing, setEditing] = useState<Branch | null | undefined>(undefined);
  return (
    <>
      <PageHeader title="Branches" actions={isAdmin && <button className="btn btn-primary" onClick={() => setEditing(null)}>Add branch</button>} />
      <Alert>{list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.length ? <Empty>No branches yet.</Empty> : (
        <table className="table">
          <thead><tr><th>Name</th><th>Address</th><th>Phone</th><th>Email</th><th>Status</th>{isAdmin && <th />}</tr></thead>
          <tbody>
            {list.data.map((b) => (
              <tr key={b.id}>
                <td><strong>{b.name}</strong></td>
                <td>{b.address}, {b.city}</td>
                <td>{b.phone}</td>
                <td>{b.email ?? '—'}</td>
                <td><Badge value={b.is_active ? 'open' : 'closed'} /></td>
                {isAdmin && <td><button className="btn btn-sm" onClick={() => setEditing(b)}>Edit</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {editing !== undefined && (
        <Modal title={editing ? `Edit ${editing.name}` : 'Add branch'} onClose={() => setEditing(undefined)}>
          <BranchForm branch={editing} onDone={() => { setEditing(undefined); list.reload(); }} />
        </Modal>
      )}
    </>
  );
}
