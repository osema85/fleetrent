import { useState, type FormEvent } from 'react';
import { api } from '../api/client';
import type { Car, Maintenance, MaintenanceStatus, Page } from '../api/types';
import { MANAGERS, useAuth } from '../auth/AuthContext';
import { Alert, Badge, Empty, Field, Loading, Modal, PageHeader, Pager } from '../components/ui';
import { dateOnly, label, money, useAsync } from '../utils';

const LIMIT = 25;
const TYPES = ['service', 'repair', 'inspection', 'tires', 'cleaning', 'other'];

function NewRecord({ onDone }: { onDone: () => void }) {
  const cars = useAsync(() => api<Page<Car>>('/cars', { query: { limit: 100 } }), []);
  const [form, setForm] = useState({
    car_id: '', type: 'service', description: '', scheduled_date: new Date().toISOString().slice(0, 10),
    cost: '0', mileage: '', vendor: '',
  });
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api('/maintenance', {
        method: 'POST',
        body: { ...form, mileage: form.mileage ? Number(form.mileage) : null, vendor: form.vendor || null },
      });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form onSubmit={submit}>
      <Alert>{error}</Alert>
      <div className="grid-2">
        <Field label="Car">
          <select required value={form.car_id} onChange={(e) => setForm({ ...form, car_id: e.target.value })}>
            <option value="">Select a car…</option>
            {cars.data?.items.filter((c) => c.status !== 'retired').map((c) => (
              <option key={c.id} value={c.id}>{c.make} {c.model} — {c.plate_number}</option>
            ))}
          </select>
        </Field>
        <Field label="Type">
          <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            {TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}
          </select>
        </Field>
        <Field label="Scheduled date"><input type="date" required value={form.scheduled_date} onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })} /></Field>
        <Field label="Estimated cost"><input type="number" min={0} step="0.01" value={form.cost} onChange={(e) => setForm({ ...form, cost: e.target.value })} /></Field>
        <Field label="Mileage (km)"><input type="number" min={0} value={form.mileage} onChange={(e) => setForm({ ...form, mileage: e.target.value })} /></Field>
        <Field label="Garage / vendor"><input maxLength={120} value={form.vendor} onChange={(e) => setForm({ ...form, vendor: e.target.value })} /></Field>
      </div>
      <Field label="Description"><textarea required maxLength={2000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
      <div className="form-actions"><button className="btn btn-primary">Schedule</button></div>
    </form>
  );
}

export default function MaintenancePage() {
  const { hasRole } = useAuth();
  const canEdit = hasRole(...MANAGERS);
  const [status, setStatus] = useState('');
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const list = useAsync(() => api<Page<Maintenance>>('/maintenance', { query: { status, limit: LIMIT, offset } }), [status, offset]);

  async function move(m: Maintenance, next: MaintenanceStatus) {
    setError('');
    try {
      await api(`/maintenance/${m.id}`, { method: 'PATCH', body: { status: next } });
      list.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader title="Maintenance" actions={canEdit && <button className="btn btn-primary" onClick={() => setCreating(true)}>Schedule maintenance</button>} />
      <div className="filters">
        <select value={status} onChange={(e) => { setOffset(0); setStatus(e.target.value); }}>
          <option value="">All statuses</option>
          {['scheduled', 'in_progress', 'completed', 'cancelled'].map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
      </div>
      <Alert>{error || list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.items.length ? <Empty>No maintenance records.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Date</th><th>Car</th><th>Type</th><th>Description</th><th>Vendor</th><th className="num">Cost</th><th>Status</th>{canEdit && <th />}</tr></thead>
            <tbody>
              {list.data.items.map((m) => (
                <tr key={m.id}>
                  <td>{dateOnly(m.scheduled_date)}</td>
                  <td>{m.car.make} {m.car.model} <span className="muted">{m.car.plate_number}</span></td>
                  <td>{label(m.type)}</td>
                  <td>{m.description}</td>
                  <td>{m.vendor ?? '—'}</td>
                  <td className="num">{money(m.cost)}</td>
                  <td><Badge value={m.status} /></td>
                  {canEdit && (
                    <td className="nowrap">
                      {m.status === 'scheduled' && <button className="btn btn-sm" onClick={() => move(m, 'in_progress')}>Start</button>}
                      {['scheduled', 'in_progress'].includes(m.status) && <button className="btn btn-sm" onClick={() => move(m, 'completed')}>Complete</button>}
                      {['scheduled', 'in_progress'].includes(m.status) && <button className="btn btn-sm" onClick={() => move(m, 'cancelled')}>Cancel</button>}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
      {creating && (
        <Modal title="Schedule maintenance" onClose={() => setCreating(false)}>
          <NewRecord onDone={() => { setCreating(false); list.reload(); }} />
        </Modal>
      )}
    </>
  );
}
