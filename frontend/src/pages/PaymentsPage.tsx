import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Page, Payment } from '../api/types';
import { Alert, Empty, Loading, PageHeader, Pager } from '../components/ui';
import { dateTime, label, money, useAsync } from '../utils';

const LIMIT = 25;

export default function PaymentsPage() {
  const [kind, setKind] = useState('');
  const [method, setMethod] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [offset, setOffset] = useState(0);
  const list = useAsync(
    () => api<Page<Payment>>('/payments', { query: { kind, method, from_date: fromDate, to_date: toDate, limit: LIMIT, offset } }),
    [kind, method, fromDate, toDate, offset],
  );
  const pageTotal = (list.data?.items ?? []).reduce(
    (sum, p) => sum + (['refund', 'deposit_refund'].includes(p.kind) ? -1 : 1) * Number(p.amount), 0,
  );

  return (
    <>
      <PageHeader title="Payments" />
      <div className="filters">
        <select value={kind} onChange={(e) => { setOffset(0); setKind(e.target.value); }}>
          <option value="">All types</option>
          {['payment', 'refund', 'deposit', 'deposit_refund'].map((k) => <option key={k} value={k}>{label(k)}</option>)}
        </select>
        <select value={method} onChange={(e) => { setOffset(0); setMethod(e.target.value); }}>
          <option value="">All methods</option>
          {['cash', 'card', 'bank_transfer'].map((m) => <option key={m} value={m}>{label(m)}</option>)}
        </select>
        <label className="inline">From <input type="date" value={fromDate} onChange={(e) => { setOffset(0); setFromDate(e.target.value); }} /></label>
        <label className="inline">To <input type="date" value={toDate} onChange={(e) => { setOffset(0); setToDate(e.target.value); }} /></label>
      </div>
      <Alert>{list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.items.length ? <Empty>No payments found.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Date</th><th>Type</th><th>Method</th><th>Reference</th><th>Reservation</th><th className="num">Amount</th></tr></thead>
            <tbody>
              {list.data.items.map((p) => (
                <tr key={p.id}>
                  <td>{dateTime(p.created_at)}</td>
                  <td>{label(p.kind)}</td>
                  <td>{label(p.method)}</td>
                  <td>{p.reference ?? '—'}</td>
                  <td><Link to={`/reservations/${p.reservation_id}`}>Open</Link></td>
                  <td className="num">{['refund', 'deposit_refund'].includes(p.kind) ? '−' : ''}{money(p.amount)}</td>
                </tr>
              ))}
              <tr className="total"><td colSpan={5} className="right">Net on this page</td><td className="num">{money(pageTotal)}</td></tr>
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </>
  );
}
