import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Edit3, Plus, ScanFace, Search, UserRound } from 'lucide-react';
import { useUser } from '../../app/App';
import Enrollment from '../enrollment/Enrollment';
import { useResource } from '../../hooks/useResource';
import { api, patch, post } from '../../lib/api/client';
import type { Person } from '../../types';
import { Badge, Empty, ErrorMessage, Initials, Loading, Modal, PageHeading } from '../../components/ui/shared';

export default function People() {
  const { data, loading, error, reload } = useResource<Person[]>('/people', []);
  const [search, setSearch] = useState('');
  const [params, setParams] = useSearchParams();
  const [edit, setEdit] = useState<Person | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [enrollment, setEnrollment] = useState<Person | null>(null);
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);
  const user = useUser();
  const canEdit = user.role !== 'operator';
  const selected = data.find(person => person.id === params.get('person'));
  const filtered = data.filter(person => `${person.name} ${person.employee_id} ${person.department}`.toLowerCase().includes(search.toLowerCase()));
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFailure('');
    const form = new FormData(event.currentTarget);
    const body = { ...Object.fromEntries(form), consent: form.get('consent') === 'on' };
    try { if (edit) await patch(`/people/${edit.id}`, body); else await post('/people', body); setFormOpen(false); await reload(); }
    catch (error) { setFailure((error as Error).message); } finally { setBusy(false); }
  }
  async function toggle(person: Person) {
    setFailure('');
    try { await post(`/people/${person.id}/toggle`); await reload(); } catch (error) { setFailure((error as Error).message); }
  }
  async function removeEnrollment(person: Person) {
    setFailure('');
    try { await api(`/people/${person.id}/enrollment`, { method: 'DELETE' }); await reload(); }
    catch (error) { setFailure((error as Error).message); }
  }
  return <><PageHeading eyebrow="THE PEOPLE IN YOUR WORKSPACE" title="People" description="Register your team and keep every identity connected." action={canEdit && <button className="button primary" onClick={() => { setEdit(null); setFailure(''); setFormOpen(true); }}><Plus size={17} />Register person</button>} /><ErrorMessage message={error || (!formOpen && failure) || ''} />
    <section className="panel"><div className="table-toolbar"><div className="tabs"><span className="tab active">All people <b>{data.length}</b></span><span className="muted small">{data.filter(p => p.template_count > 0).length} face-enrolled</span></div><div className="search-input"><Search size={17} /><input aria-label="Search people" placeholder="Search name, ID or department…" value={search} onChange={e => setSearch(e.target.value)} /></div></div>
    {loading ? <Loading /> : filtered.length ? <div className="table-wrap"><table><thead><tr><th>Person</th><th>Employee ID</th><th>Department</th><th>Enrollment</th><th>Status</th><th /></tr></thead><tbody>{filtered.map(person => <tr key={person.id}><td><button className="person-cell" onClick={() => setParams({ person: person.id })}><Initials name={person.name} /><span><strong>{person.name}</strong><small>{person.contact || 'No contact added'}</small></span></button></td><td><span className="mono">{person.employee_id}</span></td><td>{person.department}</td><td><Badge tone={person.template_count ? 'green' : 'amber'}>{person.template_count ? `${person.template_count} samples` : 'Not enrolled'}</Badge></td><td><Badge tone={!person.active ? 'gray' : person.open_session ? 'green' : 'blue'}>{!person.active ? 'Inactive' : person.open_session ? 'Present' : 'Registered'}</Badge></td><td><button className="icon-button" aria-label={`View ${person.name}`} onClick={() => setParams({ person: person.id })}><ArrowUpRight size={18} /></button></td></tr>)}</tbody></table></div> : <Empty title={search ? 'No matching people' : 'Your team starts here'} description={search ? 'Try a different name or employee ID.' : 'Register your first person, then enroll their face for recognition.'} />}</section>
    {selected && <Modal title="Person profile" close={() => setParams({})} wide><div className="profile-head"><Initials name={selected.name} /><div><h2>{selected.name}</h2><p>{selected.employee_id} · {selected.department}</p></div><Badge tone={selected.active ? 'green' : 'gray'}>{selected.active ? 'Active' : 'Inactive'}</Badge></div><div className="form"><div className="detail-grid"><div><span>Contact</span><strong>{selected.contact || 'Not provided'}</strong></div><div><span>Face enrollment</span><strong>{selected.template_count ? `${selected.template_count} templates` : 'Not enrolled'}</strong></div><div><span>Attendance</span><strong>{selected.open_session ? 'Open session' : 'Checked out / no session'}</strong></div><div><span>Consent</span><strong>{selected.consent ? 'Recorded' : 'Not recorded'}</strong></div></div><div className="profile-links"><Link className="button secondary" to={`/tracking?person=${selected.id}`}>Movement timeline <ArrowUpRight size={16} /></Link><Link className="button secondary" to={`/recordings?person=${selected.id}`}>Recordings <ArrowUpRight size={16} /></Link></div>{canEdit && <div className="profile-actions"><button className="button primary" disabled={!selected.active} onClick={() => { setEnrollment(selected); setParams({}); }}><ScanFace size={17} />Enroll face</button><button className="button secondary" onClick={() => { setEdit(selected); setFormOpen(true); setParams({}); }}><Edit3 size={16} />Edit details</button><button className="button secondary" onClick={() => toggle(selected)}>{selected.active ? 'Deactivate' : 'Reactivate'}</button>{selected.template_count > 0 && <button className="button danger" onClick={() => removeEnrollment(selected)}>Delete face templates</button>}</div>}</div></Modal>}
    {formOpen && <Modal title={edit ? 'Edit person' : 'Register a person'} close={() => setFormOpen(false)}><form className="form" onSubmit={submit}><ErrorMessage message={failure} /><label>Full name<input name="name" required minLength={2} maxLength={100} defaultValue={edit?.name} placeholder="e.g. Ali Ahmed" /></label><div className="form-grid"><label>Employee ID<input name="employee_id" required maxLength={40} defaultValue={edit?.employee_id} placeholder="EMP-001" /></label><label>Department<input name="department" required maxLength={80} defaultValue={edit?.department} placeholder="Operations" /></label></div><label>Contact<input name="contact" maxLength={80} defaultValue={edit?.contact} placeholder="Phone or email" /></label><label className="checkbox"><input name="consent" type="checkbox" required defaultChecked={!!edit?.consent} /><span>The person has agreed to face enrollment, attendance and camera-based sightings for this workspace.</span></label><div className="notice"><UserRound size={18} /><span>Save the profile first. Face samples can then be captured from their profile.</span></div><div className="form-footer"><button type="button" className="button secondary" onClick={() => setFormOpen(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? 'Saving…' : 'Save person'}</button></div></form></Modal>}
    {enrollment && <Enrollment person={enrollment} close={() => setEnrollment(null)} done={() => void reload()} />}
  </>;
}
