import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { RESERVATION_STATUSES, type Page, type Reservation } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { Alert, Badge, Empty, Loading, PageHeader, Pager } from '../components/ui';
import { dateTime, label, money, useAsync } from '../utils';

const LIMIT = 25;

export default function ReservationsPage() {
  const { isStaff } = useAuth();
  const [status, setStatus] = useState('');
  const [q, setQ] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [offset, setOffset] = useState(0);
  const list = useAsync(
    () =>
      api<Page<Reservation>>('/reservations', {
        query: { status, q, from_date: fromDate, to_date: toDate, limit: LIMIT, offset },
      }),
    [status, q, fromDate, toDate, offset],
  );
  const reset = <T,>(fn: (v: T) => void) => (v: T) => { setOffset(0); fn(v); };

  return (
    <>
      <PageHeader
        title={isStaff ? 'Reservations' : 'My reservations'}
        actions={<Link className="btn btn-primary" to={isStaff ? '/reservations/new' : '/browse'}>{isStaff ? 'New reservation' : 'Book a car'}</Link>}
      />
      <div className="filters">
        {isStaff && <input placeholder="Code, customer name or email…" value={q} onChange={(e) => reset(setQ)(e.target.value)} />}
        <select value={status} onChange={(e) => reset(setStatus)(e.target.value)}>
          <option value="">All statuses</option>
          {RESERVATION_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
        <label className="inline">From <input type="date" value={fromDate} onChange={(e) => reset(setFromDate)(e.target.value)} /></label>
        <label className="inline">To <input type="date" value={toDate} onChange={(e) => reset(setToDate)(e.target.value)} /></label>
      </div>
      <Alert>{list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.items.length ? <Empty>No reservations found.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Code</th>{isStaff && <th>Customer</th>}<th>Car</th><th>Pickup</th><th>Return</th><th>Estimated total</th><th>Status</th></tr>
            </thead>
            <tbody>
              {list.data.items.map((r) => (
                <tr key={r.id}>
                  <td><Link to={`/reservations/${r.id}`} className="mono">{r.code}</Link></td>
                  {isStaff && <td>{r.customer.first_name} {r.customer.last_name}</td>}
                  <td>{r.car.make} {r.car.model}{isStaff && <span className="muted"> · {r.car.plate_number}</span>}</td>
                  <td>{dateTime(r.start_at)}</td>
                  <td>{dateTime(r.end_at)}</td>
                  <td>{money(r.estimated_total)}</td>
                  <td><Badge value={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}
