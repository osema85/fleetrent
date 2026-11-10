import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Page, Rental } from '../api/types';
import { Alert, Badge, Empty, Loading, PageHeader, Pager } from '../components/ui';
import { dateTime, money, useAsync } from '../utils';

const LIMIT = 25;

export default function RentalsPage() {
  const [filter, setFilter] = useState('open');
  const [offset, setOffset] = useState(0);
  const list = useAsync(
    () =>
      api<Page<Rental>>('/rentals', {
        query: { status: filter === 'overdue' ? '' : filter, overdue: filter === 'overdue' || undefined, limit: LIMIT, offset },
      }),
    [filter, offset],
  );

  return (
    <>
      <PageHeader title="Rentals" />
      <div className="tabs">
        {[['open', 'On the road'], ['overdue', 'Overdue'], ['closed', 'Returned'], ['', 'All']].map(([v, t]) => (
          <button key={v} className={filter === v ? 'active' : ''} onClick={() => { setOffset(0); setFilter(v); }}>{t}</button>
        ))}
      </div>
      <Alert>{list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.items.length ? <Empty>No rentals.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Reservation</th><th>Customer</th><th>Car</th><th>Out</th><th>Due back</th><th>Returned</th><th className="num">Total</th><th>Status</th></tr></thead>
            <tbody>
              {list.data.items.map((rt) => {
                const r = rt.reservation!;
                const overdue = rt.status === 'open' && new Date(r.end_at) < new Date();
                return (
                  <tr key={rt.id}>
                    <td><Link to={`/reservations/${r.id}`} className="mono">{r.code}</Link></td>
                    <td>{r.customer.first_name} {r.customer.last_name}</td>
                    <td>{r.car.make} {r.car.model} <span className="muted">{r.car.plate_number}</span></td>
                    <td>{dateTime(rt.checked_out_at)}</td>
                    <td className={overdue ? 'text-danger' : ''}>{dateTime(r.end_at)}</td>
                    <td>{dateTime(rt.checked_in_at)}</td>
                    <td className="num">{rt.total_amount ? money(rt.total_amount) : '—'}</td>
                    <td>{overdue ? <Badge value="overdue" /> : <Badge value={rt.status} />}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}
