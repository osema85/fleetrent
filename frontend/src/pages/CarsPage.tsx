import { useState, type FormEvent } from 'react';
import { api } from '../api/client';
import { CAR_CATEGORIES, CAR_STATUSES, type Branch, type Car, type Page } from '../api/types';
import { MANAGERS, useAuth } from '../auth/AuthContext';
import { Alert, Badge, Empty, Field, Loading, Modal, PageHeader, Pager } from '../components/ui';
import { label, money, useAsync } from '../utils';

const LIMIT = 25;

const BLANK: Partial<Car> = {
  make: '', model: '', year: new Date().getFullYear(), plate_number: '', vin: '', color: '',
  category: 'economy', transmission: 'manual', fuel_type: 'petrol', seats: 5, mileage: 0, daily_rate: '',
  branch_id: null, notes: '', status: 'available',
};

function CarForm({ car, branches, onDone }: { car: Partial<Car> | null; branches: Branch[]; onDone: () => void }) {
  const [form, setForm] = useState<Partial<Car>>(car ?? BLANK);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const isEdit = !!car?.id;
  const set = (k: keyof Car) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.type === 'number' ? Number(e.target.value) : e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    const body: Record<string, unknown> = {
      make: form.make, model: form.model, year: form.year, plate_number: form.plate_number, vin: form.vin,
      color: form.color, category: form.category, transmission: form.transmission, fuel_type: form.fuel_type,
      seats: form.seats, mileage: form.mileage, daily_rate: form.daily_rate,
      branch_id: form.branch_id || null, notes: form.notes || null,
    };
    if (isEdit) body.status = form.status;
    try {
      await api(isEdit ? `/cars/${car!.id}` : '/cars', { method: isEdit ? 'PATCH' : 'POST', body });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <Alert>{error}</Alert>
      <div className="grid-3">
        <Field label="Make"><input required maxLength={60} value={form.make} onChange={set('make')} /></Field>
        <Field label="Model"><input required maxLength={60} value={form.model} onChange={set('model')} /></Field>
        <Field label="Year"><input type="number" required min={1990} max={2100} value={form.year} onChange={set('year')} /></Field>
        <Field label="Plate number"><input required maxLength={20} value={form.plate_number} onChange={set('plate_number')} /></Field>
        <Field label="VIN" hint="17 characters"><input required minLength={17} maxLength={17} value={form.vin} onChange={set('vin')} /></Field>
        <Field label="Color"><input required maxLength={30} value={form.color} onChange={set('color')} /></Field>
        <Field label="Category">
          <select value={form.category} onChange={set('category')}>
            {CAR_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}
          </select>
        </Field>
        <Field label="Transmission">
          <select value={form.transmission} onChange={set('transmission')}>
            <option value="manual">Manual</option>
            <option value="automatic">Automatic</option>
          </select>
        </Field>
        <Field label="Fuel">
          <select value={form.fuel_type} onChange={set('fuel_type')}>
            {['petrol', 'diesel', 'hybrid', 'electric'].map((f) => <option key={f} value={f}>{label(f)}</option>)}
          </select>
        </Field>
        <Field label="Seats"><input type="number" required min={1} max={20} value={form.seats} onChange={set('seats')} /></Field>
        <Field label="Mileage (km)"><input type="number" required min={0} value={form.mileage} onChange={set('mileage')} /></Field>
        <Field label="Daily rate"><input type="number" required min={1} step="0.01" value={form.daily_rate} onChange={(e) => setForm({ ...form, daily_rate: e.target.value })} /></Field>
        <Field label="Branch">
          <select value={form.branch_id ?? ''} onChange={set('branch_id')}>
            <option value="">— none —</option>
            {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </Field>
        {isEdit && (
          <Field label="Status">
            <select value={form.status} onChange={set('status')}>
              {CAR_STATUSES.map((s) => <option key={s} value={s} disabled={s === 'rented'}>{label(s)}</option>)}
            </select>
          </Field>
        )}
      </div>
      <Field label="Notes"><textarea maxLength={2000} value={form.notes ?? ''} onChange={set('notes')} /></Field>
      <div className="form-actions">
        <button className="btn btn-primary" disabled={busy}>{isEdit ? 'Save changes' : 'Add car'}</button>
      </div>
    </form>
  );
}

export default function CarsPage() {
  const { hasRole } = useAuth();
  const canEdit = hasRole(...MANAGERS);
  const [filters, setFilters] = useState({ q: '', status: '', category: '', branch_id: '' });
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<Partial<Car> | null | undefined>(undefined);
  const branches = useAsync(() => api<Branch[]>('/branches'), []);
  const cars = useAsync(
    () => api<Page<Car>>('/cars', { query: { ...filters, limit: LIMIT, offset } }),
    [filters, offset],
  );
  const branchName = (id: string | null) => branches.data?.find((b) => b.id === id)?.name ?? '—';
  const setF = (k: keyof typeof filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setOffset(0);
    setFilters({ ...filters, [k]: e.target.value });
  };

  return (
    <>
      <PageHeader title="Fleet" actions={canEdit && <button className="btn btn-primary" onClick={() => setEditing(null)}>Add car</button>} />
      <div className="filters">
        <input placeholder="Search make, model, plate…" value={filters.q} onChange={setF('q')} />
        <select value={filters.status} onChange={setF('status')}>
          <option value="">All statuses</option>
          {CAR_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
        <select value={filters.category} onChange={setF('category')}>
          <option value="">All categories</option>
          {CAR_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}
        </select>
        <select value={filters.branch_id} onChange={setF('branch_id')}>
          <option value="">All branches</option>
          {branches.data?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      </div>
      <Alert>{cars.error}</Alert>
      {cars.loading ? <Loading /> : !cars.data?.items.length ? <Empty>No cars found.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Car</th><th>Plate</th><th>Category</th><th>Specs</th><th>Mileage</th><th>Rate/day</th><th>Branch</th><th>Status</th>{canEdit && <th />}</tr>
            </thead>
            <tbody>
              {cars.data.items.map((c) => (
                <tr key={c.id}>
                  <td><strong>{c.make} {c.model}</strong> <span className="muted">{c.year} · {c.color}</span></td>
                  <td className="mono">{c.plate_number}</td>
                  <td>{label(c.category)}</td>
                  <td className="muted">{label(c.transmission)} · {label(c.fuel_type)} · {c.seats} seats</td>
                  <td>{c.mileage?.toLocaleString()} km</td>
                  <td>{money(c.daily_rate)}</td>
                  <td>{branchName(c.branch_id)}</td>
                  <td><Badge value={c.status!} /></td>
                  {canEdit && <td><button className="btn btn-sm" onClick={() => setEditing(c)}>Edit</button></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {cars.data && <Pager total={cars.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
      {editing !== undefined && (
        <Modal title={editing ? `Edit ${editing.make} ${editing.model}` : 'Add car'} onClose={() => setEditing(undefined)}>
          <CarForm car={editing} branches={branches.data ?? []} onDone={() => { setEditing(undefined); cars.reload(); }} />
        </Modal>
      )}
    </>
  );
}
