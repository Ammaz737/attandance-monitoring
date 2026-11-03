export const API = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options, credentials: 'include',
    headers: options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message = Array.isArray(detail) ? detail.map((item: any) => `${item.loc?.at(-1)}: ${item.msg}`).join('; ') : detail;
    if (response.status === 401 && path !== '/auth/login' && path !== '/auth/me') window.dispatchEvent(new Event('session-expired'));
    throw new Error(typeof message === 'string' ? message : 'Request failed. Please try again.');
  }
  return response.json();
}

export const post = (path: string, body?: unknown) => api(path, { method: 'POST', body: JSON.stringify(body) });
export const patch = (path: string, body: unknown) => api(path, { method: 'PATCH', body: JSON.stringify(body) });

export function today() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Karachi', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
}

export function time(value: string | null | undefined, full = false) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Karachi', hour: '2-digit', minute: '2-digit',
    ...(full ? { day: '2-digit', month: 'short' } : {}),
  }).format(new Date(value));
}
