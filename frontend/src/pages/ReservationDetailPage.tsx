import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Balance, Payment, PaymentKind, PaymentMethod, Rental, Reservation } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Alert, Badge, Empty, Field, Loading, PageHeader } from '../components/ui';
import { dateTime, label, localToIso, money, toLocalInput, useAsync } from '../utils';

interface Detail {
  reservation: Reservation;
  rental: Rental | null;
  payments: Payment[];
  balance: Balance;
}

function CheckoutForm({ r, onDone }: { r: Reservation; onDone: () => void }) {
  const [mileage, setMileage] = useState('');
  const [fuel, setFuel] = useState('100');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api('/rentals/checkout', {
        method: 'POST',
        body: { reservation_id: r.id, start_mileage: Number(mileage), start_fuel_level: Number(fuel), notes: notes || null },
      });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h2>Check-out (hand over the car)</h2>
      <p className="muted">Verify the driver license and ID, collect the deposit, inspect the car with the customer.</p>
      <Alert>{error}</Alert>
      <div className="grid-3">
        <Field label="Odometer (km)"><input type="number" min={0} required value={mileage} onChange={(e) => setMileage(e.target.value)} /></Field>
        <Field label="Fuel / charge level (%)"><input type="number" min={0} max={100} required value={fuel} onChange={(e) => setFuel(e.target.value)} /></Field>
      </div>
      <Field label="Condition notes (existing scratches, etc.)"><textarea maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      <button className="btn btn-primary">Confirm check-out</button>
    </form>
  );
}

function CheckinForm({ rental, onDone }: { rental: Rental; onDone: () => void }) {
  const [form, setForm] = useState({
    end_mileage: '', end_fuel_level: String(rental.start_fuel_level), returned_at: toLocalInput(new Date()),
    damage_notes: '', damage_fee: '0', send_to_maintenance: false,
  });
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api(`/rentals/${rental.id}/checkin`, {
        method: 'POST',
        body: {
          end_mileage: Number(form.end_mileage),
          end_fuel_level: Number(form.end_fuel_level),
          returned_at: localToIso(form.returned_at),
          damage_notes: form.damage_notes || null,
          damage_fee: form.damage_fee || '0',
          send_to_maintenance: form.send_to_maintenance,
        },
      });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form className="card" onSubmit={submit}>
      <h2>Check-in (car returned)</h2>
      <p className="muted">Started at {rental.start_mileage.toLocaleString()} km with {rental.start_fuel_level}% fuel.</p>
      <Alert>{error}</Alert>
      <div className="grid-3">
        <Field label="Odometer (km)"><input type="number" min={rental.start_mileage} required value={form.end_mileage} onChange={(e) => setForm({ ...form, end_mileage: e.target.value })} /></Field>
        <Field label="Fuel / charge level (%)"><input type="number" min={0} max={100} required value={form.end_fuel_level} onChange={(e) => setForm({ ...form, end_fuel_level: e.target.value })} /></Field>
        <Field label="Returned at"><input type="datetime-local" required value={form.returned_at} onChange={(e) => setForm({ ...form, returned_at: e.target.value })} /></Field>
        <Field label="Damage fee"><input type="number" min={0} step="0.01" value={form.damage_fee} onChange={(e) => setForm({ ...form, damage_fee: e.target.value })} /></Field>
      </div>
      <Field label="Damage notes"><textarea maxLength={2000} value={form.damage_notes} onChange={(e) => setForm({ ...form, damage_notes: e.target.value })} /></Field>
      <label className="check"><input type="checkbox" checked={form.send_to_maintenance} onChange={(e) => setForm({ ...form, send_to_maintenance: e.target.checked })} /> Send the car to maintenance after return</label>
      <button className="btn btn-primary">Close rental & compute final bill</button>
    </form>
  );
}

function PaymentForm({ r, balance, onDone }: { r: Reservation; balance: Balance; onDone: () => void }) {
  const suggested = Number(balance.balance) > 0 ? balance.balance : '';
  const [form, setForm] = useState({ amount: suggested, method: 'card' as PaymentMethod, kind: 'payment' as PaymentKind, reference: '' });
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api('/payments', { method: 'POST', body: { reservation_id: r.id, ...form, reference: form.reference || null } });
      onDone();
    } catch (err) {
      setError((err as Error).message);
    }
  }
  return (
    <form onSubmit={submit}>
      <Alert>{error}</Alert>
      <div className="grid-4">
        <Field label="Type">
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as PaymentKind })}>
            <option value="payment">Payment</option>
            <option value="deposit">Deposit received</option>
            <option value="deposit_refund">Deposit returned</option>
            <option value="refund">Refund</option>
          </select>
        </Field>
        <Field label="Amount"><input type="number" min={0.01} step="0.01" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
        <Field label="Method">
          <select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value as PaymentMethod })}>
            <option value="card">Card</option>
            <option value="cash">Cash</option>
            <option value="bank_transfer">Bank transfer</option>
          </select>
        </Field>
        <Field label="Reference"><input maxLength={100} value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} placeholder="Terminal receipt no." /></Field>
      </div>
      <button className="btn btn-primary">Record</button>
    </form>
  );
}

export default function ReservationDetailPage() {
  const { id } = useParams();
  const { isStaff } = useAuth();
  const [error, setError] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  const detail = useAsync<Detail>(async () => {
    const [reservation, payments, balance] = await Promise.all([
      api<Reservation>(`/reservations/${id}`),
      api<Payment[]>(`/payments/reservation/${id}`),
      api<Balance>(`/payments/reservation/${id}/balance`),
    ]);
    let rental: Rental | null = null;
    if (['active', 'completed'].includes(reservation.status)) {
      const inv = await api<{ rental: Rental | null }>(`/reservations/${id}/invoice`);
      rental = inv.rental;
    }
    return { reservation, payments, balance, rental };
  }, [id]);

  async function action(path: string, body?: unknown) {
    setError('');
    try {
      await api(`/reservations/${id}/${path}`, { method: 'POST', body });
      detail.reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (detail.loading && !detail.data) return <Loading />;
  if (!detail.data) return <Alert>{detail.error}</Alert>;
  const { reservation: r, rental, payments, balance } = detail.data;
  const canCancel = ['pending', 'confirmed'].includes(r.status) && (isStaff || new Date(r.start_at) > new Date());
  const extras = [r.gps && 'GPS', r.child_seat && 'Child seat', r.additional_driver && 'Additional driver'].filter(Boolean);

  return (
    <>
      <PageHeader
        title={`Reservation ${r.code}`}
        actions={<><Badge value={r.status} /><Link className="btn" to={`/reservations/${r.id}/invoice`}>Invoice</Link></>}
      />
      <Alert>{error}</Alert>
      {r.status === 'pending' && !isStaff && <Alert kind="info">Your request was received and is waiting for confirmation by our staff.</Alert>}

      <div className="grid-2">
        <section className="card">
          <h2>Booking</h2>
          <dl className="details">
            <dt>Customer</dt>
            <dd>{isStaff ? <Link to={`/customers/${r.customer.id}`}>{r.customer.first_name} {r.customer.last_name}</Link> : `${r.customer.first_name} ${r.customer.last_name}`}<br /><span className="muted">{r.customer.email} · {r.customer.phone}</span></dd>
            <dt>Car</dt><dd>{r.car.make} {r.car.model} <span className="mono muted">{r.car.plate_number}</span></dd>
            <dt>Pickup</dt><dd>{dateTime(r.start_at)}</dd>
            <dt>Return</dt><dd>{dateTime(r.end_at)}</dd>
            <dt>Insurance</dt><dd>{label(r.insurance)}</dd>
            <dt>Extras</dt><dd>{extras.length ? extras.join(', ') : '—'}</dd>
            <dt>Daily rate</dt><dd>{money(r.daily_rate)}</dd>
            {r.notes && <><dt>Notes</dt><dd>{r.notes}</dd></>}
            {r.cancel_reason && <><dt>Cancel reason</dt><dd>{r.cancel_reason}</dd></>}
          </dl>
        </section>
        <section className="card">
          <h2>Money</h2>
          <dl className="details">
            <dt>{balance.is_final ? 'Final total' : 'Estimated total'}</dt><dd><strong>{money(balance.total_due)}</strong></dd>
            <dt>Paid</dt><dd>{money(balance.paid)}</dd>
            <dt>Balance due</dt><dd className={Number(balance.balance) > 0 ? 'text-danger' : 'text-ok'}>{money(balance.balance)}</dd>
            <dt>Deposit required</dt><dd>{money(balance.deposit_required)}</dd>
            <dt>Deposit held</dt><dd>{money(balance.deposit_held)}</dd>
          </dl>
          {rental?.status === 'closed' && (
            <dl className="details compact">
              <dt>Late fee</dt><dd>{money(rental.late_fee)}</dd>
              <dt>Extra mileage</dt><dd>{money(rental.mileage_fee)}</dd>
              <dt>Fuel</dt><dd>{money(rental.fuel_fee)}</dd>
              <dt>Damage</dt><dd>{money(rental.damage_fee)}</dd>
            </dl>
          )}
        </section>
      </div>

      {isStaff && (
        <div className="action-bar">
          {r.status === 'pending' && <button className="btn btn-primary" onClick={() => action('confirm')}>Confirm reservation</button>}
          {r.status === 'confirmed' && new Date(r.start_at) < new Date() && (
            <button className="btn" onClick={() => action('no-show')}>Mark as no-show</button>
          )}
        </div>
      )}
      {canCancel && (
        <section className="card">
          <h2>Cancel reservation</h2>
          <div className="inline-form">
            <Field label="Reason (optional)"><input maxLength={255} value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} /></Field>
            <button className="btn btn-danger" onClick={() => window.confirm('Cancel this reservation?') && action('cancel', { reason: cancelReason })}>Cancel reservation</button>
          </div>
        </section>
      )}

      {isStaff && r.status === 'confirmed' && <CheckoutForm r={r} onDone={detail.reload} />}
      {isStaff && rental?.status === 'open' && <CheckinForm rental={rental} onDone={detail.reload} />}

      {rental && (
        <section className="card">
          <h2>Rental contract</h2>
          <dl className="details">
            <dt>Checked out</dt><dd>{dateTime(rental.checked_out_at)} · {rental.start_mileage.toLocaleString()} km · {rental.start_fuel_level}% fuel</dd>
            {rental.checkout_notes && <><dt>Condition at pickup</dt><dd>{rental.checkout_notes}</dd></>}
            <dt>Checked in</dt><dd>{rental.checked_in_at ? `${dateTime(rental.checked_in_at)} · ${rental.end_mileage?.toLocaleString()} km · ${rental.end_fuel_level}% fuel` : 'Not yet returned'}</dd>
            {rental.damage_notes && <><dt>Damage</dt><dd>{rental.damage_notes}</dd></>}
          </dl>
        </section>
      )}

      <section className="card">
        <h2>Payments</h2>
        {!payments.length ? <Empty>No payments recorded.</Empty> : (
          <table className="table">
            <thead><tr><th>Date</th><th>Type</th><th>Method</th><th>Reference</th><th className="num">Amount</th></tr></thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id}>
                  <td>{dateTime(p.created_at)}</td>
                  <td>{label(p.kind)}</td>
                  <td>{label(p.method)}</td>
                  <td>{p.reference ?? '—'}</td>
                  <td className="num">{['refund', 'deposit_refund'].includes(p.kind) ? '−' : ''}{money(p.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {isStaff && (
          <>
            <h3>Record a payment</h3>
            <PaymentForm key={balance.balance} r={r} balance={balance} onDone={detail.reload} />
          </>
        )}
      </section>
    </>
  );
}
