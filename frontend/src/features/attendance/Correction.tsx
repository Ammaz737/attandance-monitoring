import { useState } from 'react';
import type { Attendance } from '../../types';
import { patch } from '../../lib/api/client';
import { ErrorMessage, Modal } from '../../components/ui/shared';

function inputTime(value: string | null) {
  if (!value) return '';
  const date = new Date(Date.parse(value) + 5 * 3600000);
  return date.toISOString().slice(0, 16);
}

export default function Correction({ sessions, close, done }: { sessions: Attendance[]; close: () => void; done: () => void }) {
  const [selected, setSelected] = useState(sessions[0]?.id || '');
  const session = sessions.find(item => item.id === selected);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    const entry = form.get('in_at') as string;
    const exit = form.get('out_at') as string;
    try {
      await patch(`/attendance/${selected}`, { in_at: new Date(`${entry}+05:00`).toISOString(), out_at: exit ? new Date(`${exit}+05:00`).toISOString() : null, reason: form.get('reason') });
      done(); close();
    } catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  return <Modal title="Correct an attendance session" close={close}><form className="form" onSubmit={submit}><ErrorMessage message={error} /><div className="notice">Enter times in PKT. Original events stay unchanged; before/after values and your reason are saved in the audit trail.</div><label>Session<select value={selected} onChange={e => setSelected(e.target.value)}>{sessions.map(item => <option key={item.id} value={item.id}>{item.name} · {inputTime(item.in_at).replace('T', ' ')}</option>)}</select></label><div className="form-grid" key={selected}><label>Check-in · PKT<input name="in_at" type="datetime-local" required defaultValue={inputTime(session?.in_at || null)} /></label><label>Check-out · PKT<input name="out_at" type="datetime-local" defaultValue={inputTime(session?.out_at || null)} /></label></div><label>Correction reason<textarea name="reason" minLength={5} maxLength={500} required rows={3} /></label><span className="small muted">Leave check-out empty only if the person still has an open session.</span><div className="form-footer"><button type="button" className="button secondary" onClick={close}>Cancel</button><button className="button primary" disabled={busy || !session}>{busy ? 'Saving…' : 'Save correction'}</button></div></form></Modal>;
}
