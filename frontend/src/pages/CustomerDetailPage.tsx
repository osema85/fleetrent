import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Customer, Page, Reservation } from '../api/types';
import { MANAGERS, useAuth } from '../auth/AuthContext';
import { Alert, Badge, Empty, Field, Loading, PageHeader } from '../components/ui';
import { dateTime, money, useAsync } from '../utils';
import { CUSTOMER_FIELDS, CustomerFields, customerBody, type CustomerForm } from './CustomersPage';

function toForm(c: Customer): CustomerForm {
  const f = { ...CUSTOMER_FIELDS };
  (Object.keys(f) as (keyof CustomerForm)[]).forEach((k) => (f[k] = (c[k] as string | null) ?? ''));
  return f;
}

export default function CustomerDetailPage() {
  const { id } = useParams();
  const { hasRole } = useAuth();
  const customer = useAsync(() => api<Customer>(`/customers/${id}`), [id]);
  const history = useAsync(() => api<Page<Reservation>>('/reservations', { query: { customer_id: id, limit: 50 } }), [id]);
  const [form, setForm] = useState<CustomerForm>(CUSTOMER_FIELDS);
  const [reason, setReason] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (customer.data) setForm(toForm(customer.data));
  }, [customer.data]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setError('');
    try {
      customer.setData(await api<Customer>(`/customers/${id}`, { method: 'PATCH', body: customerBody(form) }));
      setMsg('Saved.');
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function setBlacklist(value: boolean) {
    setError('');
    try {
      customer.setData(
        await api<Customer>(`/customers/${id}`, {
          method: 'PATCH',
          body: { is_blacklisted: value, blacklist_reason: value ? reason || 'No reason given' : null },
        }),
      );
      setMsg(value ? 'Customer blacklisted.' : 'Customer removed from blacklist.');
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (customer.loading) return <Loading />;
  if (!customer.data) return <Alert>{customer.error}</Alert>;
  const c = customer.data;

  return (
    <>
      <PageHeader
        title={`${c.first_name} ${c.last_name}`}
        actions={<Link className="btn btn-primary" to={`/reservations/new?customer=${c.id}`}>New reservation</Link>}
      />
      <Alert>{error}</Alert>
      <Alert kind="success">{msg}</Alert>
      {c.is_blacklisted && <Alert>Blacklisted: {c.blacklist_reason}</Alert>}

      <form className="card" onSubmit={save}>
        <h2>Details</h2>
        <CustomerFields form={form} setForm={setForm} />
        <div className="form-actions"><button className="btn btn-primary">Save changes</button></div>
      </form>

      {hasRole(...MANAGERS) && (
        <section className="card">
          <h2>Blacklist</h2>
          {c.is_blacklisted ? (
            <button className="btn" onClick={() => setBlacklist(false)}>Remove from blacklist</button>
          ) : (
            <div className="inline-form">
              <Field label="Reason"><input maxLength={255} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
              <button className="btn btn-danger" onClick={() => setBlacklist(true)}>Blacklist customer</button>
            </div>
          )}
        </section>
      )}

      <section className="card">
        <h2>Rental history</h2>
        {!history.data?.items.length ? <Empty>No reservations yet.</Empty> : (
          <table className="table">
            <thead><tr><th>Code</th><th>Car</th><th>From</th><th>To</th><th>Total</th><th>Status</th></tr></thead>
            <tbody>
              {history.data.items.map((r) => (
                <tr key={r.id}>
                  <td><Link to={`/reservations/${r.id}`}>{r.code}</Link></td>
                  <td>{r.car.make} {r.car.model}</td>
                  <td>{dateTime(r.start_at)}</td>
                  <td>{dateTime(r.end_at)}</td>
                  <td>{money(r.estimated_total)}</td>
                  <td><Badge value={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
