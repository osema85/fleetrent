import { useState } from 'react';
import { api } from '../api/client';
import type { AuditEntry, Page } from '../api/types';
import { Alert, Empty, Loading, PageHeader, Pager } from '../components/ui';
import { dateTime, useAsync } from '../utils';

const LIMIT = 50;

export default function AuditPage() {
  const [action, setAction] = useState('');
  const [offset, setOffset] = useState(0);
  const list = useAsync(() => api<Page<AuditEntry>>('/audit-logs', { query: { action, limit: LIMIT, offset } }), [action, offset]);
  return (
    <>
      <PageHeader title="Audit log" />
      <div className="filters">
        <input placeholder="Filter by action (login_failed, payment, car_…)" value={action} onChange={(e) => { setOffset(0); setAction(e.target.value); }} />
      </div>
      <Alert>{list.error}</Alert>
      {list.loading ? <Loading /> : !list.data?.items.length ? <Empty>No events.</Empty> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>When</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th><th>IP</th></tr></thead>
            <tbody>
              {list.data.items.map((a) => (
                <tr key={a.id} className={a.action.includes('failed') || a.action.includes('reuse') || a.action.includes('blocked') ? 'row-warn' : ''}>
                  <td className="nowrap">{dateTime(a.created_at)}</td>
                  <td>{a.user_email ?? '—'}</td>
                  <td className="mono">{a.action}</td>
                  <td>{a.entity_type ?? ''}</td>
                  <td className="mono small">{Object.keys(a.details).length ? JSON.stringify(a.details) : ''}</td>
                  <td className="mono">{a.ip ?? ''}</td>
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
