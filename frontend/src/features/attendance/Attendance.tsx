import { useState } from 'react';
import { ClipboardCheck, Download, Plus, Search } from 'lucide-react';
import { useUser } from '../../app/App';
import { useResource } from '../../hooks/useResource';
import { API, post, time, today } from '../../lib/api/client';
import type { Attendance, Person } from '../../types';
import { Badge, Empty, ErrorMessage, Initials, Loading, Modal, PageHeading } from '../../components/ui/shared';
import Correction from './Correction';

export default function AttendancePage() {
  const [day, setDay] = useState(today());
  const [search, setSearch] = useState('');
  const { data, loading, error, reload } = useResource<Attendance[]>(`/attendance?day=${day}`, [], 10000);
  const people = useResource<Person[]>('/people', []);
  const reviews = useResource<any[]>('/reviews', [], 10000);
  const [open, setOpen] = useState(false);
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<string | null>(null);
  const [correcting, setCorrecting] = useState(false);
  const canEdit = useUser().role !== 'operator';
  const filtered = data.filter(item => `${item.name} ${item.employee_id} ${item.department}`.toLowerCase().includes(search.toLowerCase()));
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFailure('');
    const body = Object.fromEntries(new FormData(event.currentTarget));
    try { await post(review ? `/reviews/${review}/resolve` : '/attendance', body); setOpen(false); setReview(null); await Promise.all([reload(), people.reload(), reviews.reload()]); window.dispatchEvent(new Event('workspace-update')); }
    catch (error) { setFailure((error as Error).message); } finally { setBusy(false); }
  }
  const pending = reviews.data.filter(item => item.status === 'open');
  return <><PageHeading eyebrow="EVERY ARRIVAL, ACCOUNTED FOR" title="Attendance" description="Review daily sessions, arrivals and departures. All times in PKT." action={canEdit && <><a className="button secondary" href={`${API}/reports/attendance.csv?day=${day}`}><Download size={16} />Export CSV</a><button className="button primary" onClick={() => { setFailure(''); setReview(null); setOpen(true); }}><Plus size={17} />Manual attendance</button></>} /><ErrorMessage message={error || people.error || reviews.error} />
    <div className="mini-stats"><span><ClipboardCheck size={16} />{data.length} sessions</span><span>{data.filter(item => !item.out_at).length} open</span><span>{pending.length} items need review</span>{canEdit && data.length > 0 && <button className="button secondary compact" onClick={() => setCorrecting(true)}>Correct a session</button>}</div>
    {correcting && <Correction sessions={data} close={() => setCorrecting(false)} done={() => { void reload(); window.dispatchEvent(new Event('workspace-update')); }} />}
    <section className="panel"><div className="table-toolbar"><label className="inline-label">Date<input aria-label="Attendance date" type="date" value={day} onChange={e => e.target.value && setDay(e.target.value)} /></label><div className="search-input"><Search size={17} /><input aria-label="Search attendance" placeholder="Search people…" value={search} onChange={e => setSearch(e.target.value)} /></div></div>{loading ? <Loading /> : filtered.length ? <div className="table-wrap"><table><thead><tr><th>Person</th><th>Department</th><th>Check-in</th><th>Check-out</th><th>Duration</th><th>Status</th></tr></thead><tbody>{filtered.map(item => { const minutes = item.out_at ? Math.round((Date.parse(item.out_at) - Date.parse(item.in_at)) / 60000) : null; const old = !item.out_at && Date.now() - Date.parse(item.in_at) > 18 * 3600000; return <tr key={item.id}><td><div className="person-cell"><Initials name={item.name} /><span><strong>{item.name}</strong><small>{item.employee_id}</small></span></div></td><td>{item.department}</td><td>{time(item.in_at, true)}</td><td>{time(item.out_at, true)}</td><td>{minutes === null ? 'In progress' : `${Math.floor(minutes / 60)}h ${minutes % 60}m`}</td><td><Badge tone={old ? 'amber' : item.out_at ? 'gray' : 'green'}>{old ? 'Needs review' : item.out_at ? 'Checked out' : 'Present'}</Badge></td></tr>; })}</tbody></table></div> : <Empty title="No attendance for this selection" description="Confirmed camera events and authorized manual entries appear here." />}</section>
    {pending.length > 0 && <section className="panel review-panel"><div className="section-title"><div><h2>Needs a closer look</h2><p>Review evidence before changing attendance.</p></div><Badge tone="amber">{pending.length} pending</Badge></div>{pending.map(item => <div className="review-row" key={item.id}><div><strong>{item.name || 'Unidentified person'} · {item.camera_name || 'System'}</strong><p>{item.message}</p><span className="small muted">{time(item.created_at, true)}</span></div>{canEdit && <button className="button secondary" onClick={() => { setReview(item.id); setFailure(''); setOpen(true); }}>Resolve</button>}</div>)}</section>}
    {open && <Modal title={review ? 'Resolve review item' : 'Manual attendance'} close={() => setOpen(false)}><form className="form" onSubmit={submit}><ErrorMessage message={failure} />{!review && <><div className="notice">This records attendance now. A reason and your operator identity are saved to the audit trail.</div><label>Person<select name="person_id" required defaultValue=""><option value="" disabled>Select a person</option>{people.data.filter(p => p.active).map(person => <option value={person.id} key={person.id}>{person.name} · {person.employee_id}{person.open_session ? ' · Currently in' : ''}</option>)}</select></label><label>Event<select name="kind"><option value="IN">Check in</option><option value="OUT">Check out</option></select></label></>}<label>{review ? 'Resolution notes' : 'Reason'}<textarea name="reason" required minLength={5} maxLength={500} rows={3} placeholder="Explain what was verified…" /></label>{review && <span className="small muted">Resolving this item does not automatically change attendance. Use Manual attendance for a verified IN/OUT.</span>}<div className="form-footer"><button className="button secondary" type="button" onClick={() => setOpen(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? 'Saving…' : review ? 'Resolve item' : 'Record attendance'}</button></div></form></Modal>}
  </>;
}
