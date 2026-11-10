import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { CAR_CATEGORIES, type Branch, type Car, type Customer, type Insurance, type Page, type Quote, type Reservation } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Alert, Empty, Field, PageHeader } from '../components/ui';
import { label, localToIso, money, toLocalInput, useAsync } from '../utils';

function defaultDates() {
  const start = new Date();
  start.setDate(start.getDate() + 1);
  start.setHours(10, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 3);
  return { start: toLocalInput(start), end: toLocalInput(end) };
}

/** Used by staff (/reservations/new) and customers (/browse). */
export default function BookingPage() {
  const { isStaff } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const d = defaultDates();
  const [start, setStart] = useState(d.start);
  const [end, setEnd] = useState(d.end);
  const [category, setCategory] = useState('');
  const [branchId, setBranchId] = useState('');
  const [returnBranchId, setReturnBranchId] = useState('');
  const [cars, setCars] = useState<Car[] | null>(null);
  const [car, setCar] = useState<Car | null>(null);
  const [extras, setExtras] = useState({ insurance: 'basic' as Insurance, gps: false, child_seat: false, additional_driver: false });
  const [quote, setQuote] = useState<Quote | null>(null);
  const [notes, setNotes] = useState('');
  const [customerQ, setCustomerQ] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const branches = useAsync(() => api<Branch[]>('/branches'), []);

  // Pre-select a customer when coming from a customer page
  useEffect(() => {
    const id = params.get('customer');
    if (isStaff && id) api<Customer>(`/customers/${id}`).then(setCustomer).catch(() => undefined);
  }, [params, isStaff]);

  // Customer search (staff)
  useEffect(() => {
    if (!isStaff || customerQ.length < 2) return setCustomers([]);
    const t = setTimeout(() => {
      api<Page<Customer>>('/customers', { query: { q: customerQ, limit: 8 } }).then((p) => setCustomers(p.items)).catch(() => undefined);
    }, 250);
    return () => clearTimeout(t);
  }, [customerQ, isStaff]);

  // Live price quote
  useEffect(() => {
    if (!car) return setQuote(null);
    api<Quote>('/reservations/quote', {
      method: 'POST',
      body: { car_id: car.id, start_at: localToIso(start), end_at: localToIso(end), ...extras },
    }).then(setQuote).catch((e: Error) => setError(e.message));
  }, [car, start, end, extras]);

  async function search() {
    setError('');
    setCar(null);
    try {
      setCars(await api<Car[]>('/cars/available', {
        query: { start_at: localToIso(start), end_at: localToIso(end), category, branch_id: branchId },
      }));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function book() {
    if (!car) return;
    setBusy(true);
    setError('');
    try {
      const r = await api<Reservation>('/reservations', {
        method: 'POST',
        body: {
          car_id: car.id,
          customer_id: isStaff ? customer?.id : undefined,
          start_at: localToIso(start),
          end_at: localToIso(end),
          pickup_branch_id: branchId || null,
          return_branch_id: returnBranchId || branchId || null,
          notes: notes || null,
          ...extras,
        },
      });
      navigate(`/reservations/${r.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title={isStaff ? 'New reservation' : 'Book a car'} />
      <Alert>{error}</Alert>

      <section className="card">
        <h2>1. When and where</h2>
        <div className="grid-3">
          <Field label="Pickup"><input type="datetime-local" value={start} onChange={(e) => { setStart(e.target.value); setCars(null); }} /></Field>
          <Field label="Return"><input type="datetime-local" value={end} onChange={(e) => { setEnd(e.target.value); setCars(null); }} /></Field>
          <Field label="Category">
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">Any</option>
              {CAR_CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}
            </select>
          </Field>
          <Field label="Pickup branch">
            <select value={branchId} onChange={(e) => setBranchId(e.target.value)}>
              <option value="">Any</option>
              {branches.data?.map((b) => <option key={b.id} value={b.id}>{b.name} — {b.city}</option>)}
            </select>
          </Field>
          <Field label="Return branch">
            <select value={returnBranchId} onChange={(e) => setReturnBranchId(e.target.value)}>
              <option value="">Same as pickup</option>
              {branches.data?.map((b) => <option key={b.id} value={b.id}>{b.name} — {b.city}</option>)}
            </select>
          </Field>
        </div>
        <button className="btn btn-primary" onClick={search}>Search available cars</button>
      </section>

      {cars && (
        <section className="card">
          <h2>2. Choose a car</h2>
          {!cars.length ? <Empty>No cars available for these dates. Try other dates or another category.</Empty> : (
            <div className="car-grid">
              {cars.map((c) => (
                <button key={c.id} className={`car-card ${car?.id === c.id ? 'selected' : ''}`} onClick={() => setCar(c)}>
                  <strong>{c.make} {c.model}</strong>
                  <span className="muted">{c.year} · {c.color} · {label(c.category)}</span>
                  <span className="muted">{label(c.transmission)} · {label(c.fuel_type)} · {c.seats} seats</span>
                  <span className="price">{money(c.daily_rate)} <small>/ day</small></span>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {car && (
        <section className="card">
          <h2>3. Options{isStaff && ' & customer'}</h2>
          <div className="grid-2">
            <div>
              <Field label="Insurance">
                <select value={extras.insurance} onChange={(e) => setExtras({ ...extras, insurance: e.target.value as Insurance })}>
                  <option value="none">None (customer liable)</option>
                  <option value="basic">Basic cover (+12/day)</option>
                  <option value="full">Full cover, half deposit (+25/day)</option>
                </select>
              </Field>
              <label className="check"><input type="checkbox" checked={extras.gps} onChange={(e) => setExtras({ ...extras, gps: e.target.checked })} /> GPS (+5/day)</label>
              <label className="check"><input type="checkbox" checked={extras.child_seat} onChange={(e) => setExtras({ ...extras, child_seat: e.target.checked })} /> Child seat (+4/day)</label>
              <label className="check"><input type="checkbox" checked={extras.additional_driver} onChange={(e) => setExtras({ ...extras, additional_driver: e.target.checked })} /> Additional driver (+8/day)</label>
              <Field label="Notes"><textarea maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
              {isStaff && (
                <Field label="Customer">
                  {customer ? (
                    <div className="selected-customer">
                      <strong>{customer.first_name} {customer.last_name}</strong> <span className="muted">{customer.email}</span>
                      <button className="btn btn-sm" onClick={() => setCustomer(null)}>Change</button>
                    </div>
                  ) : (
                    <>
                      <input placeholder="Search by name, email, license…" value={customerQ} onChange={(e) => setCustomerQ(e.target.value)} />
                      <ul className="suggestions">
                        {customers.map((c) => (
                          <li key={c.id}>
                            <button onClick={() => { setCustomer(c); setCustomerQ(''); }}>
                              {c.first_name} {c.last_name} <span className="muted">{c.email}</span>
                              {c.is_blacklisted && <span className="badge badge-cancelled">Blacklisted</span>}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </Field>
              )}
            </div>
            {quote && (
              <div className="quote">
                <h3>{car.make} {car.model}</h3>
                <dl>
                  <dt>{quote.days} day(s) × {money(quote.daily_rate, quote.currency)}</dt><dd>{money(quote.base_amount, quote.currency)}</dd>
                  <dt>Insurance & extras</dt><dd>{money(quote.extras_amount, quote.currency)}</dd>
                  <dt>Tax</dt><dd>{money(quote.tax_amount, quote.currency)}</dd>
                  <dt className="total">Total</dt><dd className="total">{money(quote.total, quote.currency)}</dd>
                  <dt>Refundable deposit</dt><dd>{money(quote.deposit, quote.currency)}</dd>
                </dl>
                <p className="muted small">Includes 300 km/day. Late returns, extra mileage, missing fuel and damage are charged at return.</p>
                <button className="btn btn-primary btn-block" disabled={busy || (isStaff && !customer)} onClick={book}>
                  {isStaff ? 'Create confirmed reservation' : 'Request booking'}
                </button>
                {!isStaff && <p className="muted small">Your booking will be confirmed by our staff.</p>}
              </div>
            )}
          </div>
        </section>
      )}
    </>
  );
}
