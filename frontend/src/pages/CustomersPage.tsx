import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Customer, Page } from '../api/types';
import { Alert, Empty, Field, Loading, Modal, PageHeader, Pager } from '../components/ui';
import { dateOnly, useAsync } from '../utils';

const LIMIT = 25;

export const CUSTOMER_FIELDS = {
  first_name: '', last_name: '', email: '', phone: '', date_of_birth: '', address: '', city: '', country: '',
  driver_license_number: '', license_country: '', license_expiry: '', id_document_number: '', notes: '',
};
export type CustomerForm = typeof CUSTOMER_FIELDS;

export function CustomerFields({ form, setForm }: { form: CustomerForm; setForm: (f: CustomerForm) => void }) {
  const set = (k: keyof CustomerForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value });
  return (
    <>
      <div className="grid-3">
        <Field label="First name"><input required maxLength={100} value={form.first_name} onChange={set('first_name')} /></Field>
        <Field label="Last name"><input required maxLength={100} value={form.last_name} onChange={set('last_name')} /></Field>
        <Field label="Date of birth"><input type="date" required value={form.date_of_birth} onChange={set('date_of_birth')} /></Field>
        <Field label="Email"><input type="email" required value={form.email} onChange={set('email')} /></Field>
        <Field label="Phone"><input type="tel" required value={form.phone} onChange={set('phone')} /></Field>
        <Field label="ID / passport no."><input maxLength={50} value={form.id_document_number} onChange={set('id_document_number')} /></Field>
        <Field label="Address"><input maxLength={255} value={form.address} onChange={set('address')} /></Field>
        <Field label="City"><input maxLength={100} value={form.city} onChange={set('city')} /></Field>
        <Field label="Country"><input maxLength={100} value={form.country} onChange={set('country')} /></Field>
        <Field label="Driver license no."><input required maxLength={50} value={form.driver_license_number} onChange={set('driver_license_number')} /></Field>
        <Field label="License country"><input required maxLength={100} value={form.license_country} onChange={set('license_country')} /></Field>
        <Field label="License expiry"><input type="date" required value={form.license_expiry} onChange={set('license_expiry')} /></Field>
      </div>
      <Field label="Internal notes"><textarea maxLength={2000} value={form.notes} onChange={set('notes')} /></Field>
    </>
  );
}

/** Convert empty strings to null for optional fields */
export function customerBody(form: CustomerForm) {
  const out: Record<string, string | null> = {};
  Object.entries(form).forEach(([k, v]) => (out[k] = v === '' ? null : v));
  return out;
}

function NewCustomer({ onDone }: { onDone: () => void }) {
  const [form, setForm] = useState<CustomerForm>(CUSTOMER_FIELDS);
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api('/customers', { method: 'POST', body: customerBody(form) });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form onSubmit={submit}>
      <Alert>{error}</Alert>
      <CustomerFields form={form} setForm={setForm} />
      <div className="form-actions"><button className="btn btn-primary">Create customer</button></div>
    </form>
  );
}

export default function CustomersPage() {
  const [q, setQ] = useState('');
  const [blacklisted, setBlacklisted] = useState('');
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const list = useAsync(
    () => api<Page<Customer>>('/customers', { query: { q, blacklisted, limit: LIMIT, offset } }),
    [q, blacklisted, offset],
  );

  return (
    <>
      <PageHeader title="Customers" actions={<button className="btn btn-primary" onClick={() => setCreating(true)}>New customer</button>} />
      <div className="filters">
        <input placeholder="Search name, email, phone, license…" value={q} onChange={(e) => { setOffset(0); setQ(e.target.value); }} />
        <select value={blacklisted} onChange={(e) => { setOffset(0); setBlacklisted(e.target.value); }}>
          <option value="">All customers</option>
          <option value="false">In good standing</option>
          <option value="true">Blacklisted</option>
        </select>
      </div>
      <Alert>{list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.items.length ? <Empty>No customers found.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>License</th><th>License expiry</th><th>Account</th></tr></thead>
            <tbody>
              {list.data.items.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/customers/${c.id}`}>{c.first_name} {c.last_name}</Link>
                    {c.is_blacklisted && <span className="badge badge-cancelled">Blacklisted</span>}
                  </td>
                  <td>{c.email}</td>
                  <td>{c.phone}</td>
                  <td className="mono">{c.driver_license_number}</td>
                  <td className={new Date(c.license_expiry) < new Date() ? 'text-danger' : ''}>{dateOnly(c.license_expiry)}</td>
                  <td>{c.user_id ? 'Online' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
      {creating && (
        <Modal title="New customer" onClose={() => setCreating(false)}>
          <NewCustomer onDone={() => { setCreating(false); list.reload(); }} />
        </Modal>
      )}
    </>
  );
}
