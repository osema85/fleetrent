import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { DashboardStats, Reservation } from '../api/types';
import { Alert, Badge, Empty, Loading, PageHeader, Stat } from '../components/ui';
import { dateTime, money, useAsync } from '../utils';

function ReservationTable({ rows, dateField }: { rows: Reservation[]; dateField: 'start_at' | 'end_at' }) {
  if (!rows.length) return <Empty>Nothing here.</Empty>;
  return (
    <table className="table">
      <thead>
        <tr>
          <th>Code</th>
          <th>Customer</th>
          <th>Car</th>
          <th>{dateField === 'start_at' ? 'Pickup' : 'Due back'}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id}>
            <td><Link to={`/reservations/${r.id}`}>{r.code}</Link></td>
            <td>{r.customer.first_name} {r.customer.last_name}</td>
            <td>{r.car.make} {r.car.model} <span className="muted">{r.car.plate_number}</span></td>
            <td>{dateTime(r[dateField])}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DashboardPage() {
  const { data, error, loading } = useAsync(() => api<DashboardStats>('/dashboard'), []);
  if (loading) return <Loading />;
  if (error || !data) return <Alert>{error}</Alert>;
  const max = Math.max(1, ...data.revenue_by_month.map((m) => Number(m.amount)));

  return (
    <>
      <PageHeader title="Dashboard" actions={<Link className="btn btn-primary" to="/reservations/new">New reservation</Link>} />
      <div className="stats">
        <Stat title="Pickups today" value={data.pickups_today} />
        <Stat title="Returns today" value={data.returns_today} />
        <Stat title="Active rentals" value={data.active_rentals} />
        <Stat title="Overdue" value={data.overdue_rentals} tone={data.overdue_rentals ? 'danger' : undefined} />
        <Stat title="Pending approval" value={data.pending_reservations} tone={data.pending_reservations ? 'warn' : undefined} />
        <Stat title="Fleet utilization" value={`${data.utilization_pct}%`} />
        <Stat title="Revenue this month" value={money(data.revenue_month, data.currency)} tone="ok" />
        <Stat title="Open maintenance" value={data.open_maintenance} />
      </div>

      <div className="grid-2">
        <section className="card">
          <h2>Fleet status</h2>
          <ul className="status-list">
            {Object.entries(data.cars_by_status).map(([status, n]) => (
              <li key={status}><Badge value={status} /> <strong>{n}</strong></li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2>Revenue (last 6 months)</h2>
          {data.revenue_by_month.length === 0 ? (
            <Empty>No payments recorded yet.</Empty>
          ) : (
            <ul className="bars">
              {data.revenue_by_month.map((m) => (
                <li key={m.month}>
                  <span className="bar-label">{m.month}</span>
                  <span className="bar-track"><span className="bar" style={{ width: `${(Number(m.amount) / max) * 100}%` }} /></span>
                  <span className="bar-value">{money(m.amount, data.currency)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <h2>Upcoming pickups</h2>
          <ReservationTable rows={data.upcoming_pickups} dateField="start_at" />
        </section>
        <section className="card">
          <h2 className={data.overdue.length ? 'text-danger' : ''}>Overdue returns</h2>
          <ReservationTable rows={data.overdue} dateField="end_at" />
        </section>
      </div>
    </>
  );
}
