import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import type { Invoice } from '../api/types';
import { Alert, Loading } from '../components/ui';
import { dateOnly, dateTime, label, money, useAsync } from '../utils';

export default function InvoicePage() {
  const { id } = useParams();
  const { data: inv, error, loading } = useAsync(() => api<Invoice>(`/reservations/${id}/invoice`), [id]);
  if (loading) return <Loading />;
  if (!inv) return <Alert>{error}</Alert>;
  const r = inv.reservation;
  const cur = inv.currency;

  return (
    <>
      <div className="no-print action-bar">
        <Link className="btn" to={`/reservations/${r.id}`}>← Back</Link>
        <button className="btn btn-primary" onClick={() => window.print()}>Print / Save as PDF</button>
      </div>
      <article className="card invoice">
        <header className="invoice-head">
          <div>
            <h1>{inv.company_name}</h1>
            <p className="muted">{inv.balance.is_final ? 'Invoice' : 'Booking estimate'}</p>
          </div>
          <div className="right">
            <div><strong>{inv.invoice_number}</strong></div>
            <div className="muted">Issued {dateOnly(inv.issued_at)}</div>
            <div className="muted">Reservation {r.code}</div>
          </div>
        </header>
        <div className="grid-2">
          <div>
            <h3>Billed to</h3>
            <p>{r.customer.first_name} {r.customer.last_name}<br />{r.customer.email}<br />{r.customer.phone}</p>
          </div>
          <div>
            <h3>Vehicle</h3>
            <p>{r.car.make} {r.car.model} ({r.car.plate_number})<br />{dateTime(r.start_at)} → {dateTime(r.end_at)}<br />Insurance: {label(r.insurance)}</p>
            {inv.rental?.checked_in_at && <p className="muted">Returned {dateTime(inv.rental.checked_in_at)}</p>}
          </div>
        </div>
        <table className="table">
          <thead><tr><th>Description</th><th className="num">Amount</th></tr></thead>
          <tbody>
            {inv.line_items.map((li) => <tr key={li.label}><td>{li.label}</td><td className="num">{money(li.amount, cur)}</td></tr>)}
            <tr><td className="right">Subtotal</td><td className="num">{money(inv.subtotal, cur)}</td></tr>
            <tr><td className="right">Tax ({(Number(inv.tax_rate) * 100).toFixed(0)}%)</td><td className="num">{money(inv.tax_amount, cur)}</td></tr>
            <tr className="total"><td className="right">Total</td><td className="num">{money(inv.total, cur)}</td></tr>
            <tr><td className="right">Paid</td><td className="num">{money(inv.balance.paid, cur)}</td></tr>
            <tr className="total"><td className="right">Balance due</td><td className="num">{money(inv.balance.balance, cur)}</td></tr>
          </tbody>
        </table>
        <p className="muted small">
          Security deposit held: {money(inv.balance.deposit_held, cur)} (required {money(inv.balance.deposit_required, cur)}).
          {!inv.balance.is_final && ' Final amount is calculated at vehicle return.'}
        </p>
      </article>
    </>
  );
}
