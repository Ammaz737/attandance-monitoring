import { useState } from 'react';
import { Check, Cpu, LockKeyhole, Save, ShieldCheck, UserPlus } from 'lucide-react';
import { useUser } from '../../app/App';
import { useResource } from '../../hooks/useResource';
import { patch, post, time } from '../../lib/api/client';
import { Badge, ErrorMessage, Loading, Modal, PageHeading } from '../../components/ui/shared';

export default function Settings() {
  const { data, loading, error, reload } = useResource<any>('/settings', null, 10000);
  const user = useUser();
  const audit = useResource<any[]>(user.role === 'admin' ? '/audit' : '/reviews', []);
  const [message, setMessage] = useState('');
  const [failure, setFailure] = useState('');
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFailure(''); setMessage('');
    const form = new FormData(event.currentTarget);
    try { await patch('/settings', { organization: form.get('organization') }); setMessage('Workspace settings saved.'); await reload(); }
    catch (error) { setFailure((error as Error).message); } finally { setBusy(false); }
  }
  async function addUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFailure('');
    try { await post('/users', Object.fromEntries(new FormData(event.currentTarget))); setOpen(false); setMessage('Workspace user created.'); await audit.reload(); }
    catch (error) { setFailure((error as Error).message); } finally { setBusy(false); }
  }
  if (loading) return <Loading />;
  if (!data) return <ErrorMessage message={error} />;
  const vision = data.vision;
  return <><PageHeading eyebrow="MAKE YOUR WORKSPACE WORK FOR YOU" title="Settings" description="Workspace preferences, model readiness and access management." action={user.role === 'admin' && <button className="button primary" onClick={() => { setOpen(true); setFailure(''); }}><UserPlus size={17} />Add user</button>} /><ErrorMessage message={error || (!open && failure) || ''} />{message && <div className="success"><Check size={17} />{message}</div>}
    <div className="settings-grid"><section className="panel"><div className="section-title"><div><h2>Workspace details</h2><p>Your local application configuration</p></div><ShieldCheck size={21} className="muted" /></div><form className="form" onSubmit={save}><label>Organization name<input name="organization" key={data.organization} defaultValue={data.organization} required minLength={2} maxLength={100} disabled={user.role !== 'admin'} /></label><div className="detail-grid"><div><span>Timezone</span><strong>{data.timezone}</strong></div><div><span>Database</span><strong>{data.database}</strong></div><div><span>Preview transport</span><strong>{data.stream_transport}</strong></div><div><span>Recording mode</span><strong>60-second MP4 segments</strong></div></div>{user.role === 'admin' && <button className="button primary align-start" disabled={busy}><Save size={16} />Save changes</button>}</form></section>
      <section className="panel"><div className="section-title"><div><h2>AI & model readiness</h2><p>Capabilities reflect the current backend</p></div><Cpu size={21} className="muted" /></div><div className="model-list">{[['Person detection', vision.detector_ready], ['Face recognition', vision.face_ready], ['Liveness verification', vision.liveness_ready], ['Automatic attendance', vision.automatic_attendance]].map(([name, ready]) => <div key={String(name)}><span>{name}</span><Badge tone={ready ? 'green' : 'amber'}>{ready ? 'Enabled' : 'Not enabled'}</Badge></div>)}</div><div className="notice model-notice">{vision.message || 'Local models initialized.'}</div><p className="model-help">Model: {vision.model} · Match threshold: {vision.threshold}. Set backend environment values and restart to change models. Calibrate using your own footage. Liveness is not implemented in this version.</p></section></div>
    {user.role === 'admin' && <section className="panel audit-panel"><div className="section-title"><div><h2>Audit trail</h2><p>Recent changes and protected media access</p></div><LockKeyhole size={20} className="muted" /></div><ErrorMessage message={audit.error} /><div className="table-wrap"><table><thead><tr><th>Actor</th><th>Action</th><th>Notes</th><th>When · PKT</th></tr></thead><tbody>{audit.data.map(item => <tr key={item.id}><td>{item.actor}</td><td><span className="mono">{item.action}</span></td><td>{item.details || '—'}</td><td>{time(item.created_at, true)}</td></tr>)}</tbody></table></div></section>}
    {open && <Modal title="Add workspace user" close={() => setOpen(false)}><form className="form" onSubmit={addUser}><ErrorMessage message={failure} /><label>Username<input name="username" autoComplete="off" required minLength={3} maxLength={60} pattern="[a-zA-Z0-9_.-]+" /></label><label>Password<input name="password" type="password" autoComplete="new-password" required minLength={10} maxLength={128} /></label><label>Role<select name="role"><option value="operator">Operator · monitoring and read access</option><option value="attendance">Attendance · people, enrollment and attendance</option><option value="admin">Administrator · full configuration</option></select></label><div className="form-footer"><button type="button" className="button secondary" onClick={() => setOpen(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? 'Creating…' : 'Create user'}</button></div></form></Modal>}
  </>;
}
