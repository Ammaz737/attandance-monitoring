import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api/client';

export function useResource<T>(path: string, initial: T, interval = 0) {
  const [data, setData] = useState<T>(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const reload = useCallback(async () => {
    try { setData(await api<T>(path)); setError(''); }
    catch (error) { setError((error as Error).message); }
    finally { setLoading(false); }
  }, [path]);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api<T>(path).then(value => { if (!cancelled) { setData(value); setError(''); } })
      .catch(error => { if (!cancelled) setError(error.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    const onChange = () => { if (!document.hidden) void reload(); };
    window.addEventListener('workspace-update', onChange);
    document.addEventListener('visibilitychange', onChange);
    const timer = interval ? window.setInterval(onChange, interval) : undefined;
    return () => { cancelled = true; clearInterval(timer); window.removeEventListener('workspace-update', onChange); document.removeEventListener('visibilitychange', onChange); };
  }, [path, interval, reload]);
  return { data, loading, error, reload };
}
