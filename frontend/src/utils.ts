import { useCallback, useEffect, useState } from 'react';

export const CURRENCY = 'EUR';

export function money(value: string | number | null | undefined, currency = CURRENCY): string {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(n);
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return '—';
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function dateOnly(value: string | null | undefined): string {
  if (!value) return '—';
  return new Date(value.length === 10 ? `${value}T00:00:00` : value).toLocaleDateString(undefined, {
    dateStyle: 'medium',
  });
}

export function label(value: string): string {
  return value.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}

/** <input type="datetime-local"> value -> ISO string with timezone */
export function localToIso(value: string): string {
  return new Date(value).toISOString();
}

/** Date -> value for <input type="datetime-local"> */
export function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Load data and re-load on demand. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    run()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [run]);

  useEffect(reload, [reload]);
  return { data, error, loading, reload, setData };
}
