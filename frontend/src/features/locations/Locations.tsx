import { useState } from 'react';
import { Building2, MapPin, Plus } from 'lucide-react';
import { useResource } from '../../hooks/useResource';
import { post } from '../../lib/api/client';
import { Empty, ErrorMessage, Loading, Modal, PageHeading } from '../../components/ui/shared';
import type { Location } from '../../types';
import { useUser } from '../../app/App';

export default function Locations() {
  const { data, loading, error, reload } = useResource<Location[]>('/locations', []);
  const [open, setOpen] = useState(false);
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);
  const user = useUser();
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setFailure('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try { await post('/locations', values); setOpen(false); await reload(); } catch (error) { setFailure((error as Error).message); } finally { setBusy(false); }
  }
  return <><PageHeading eyebrow="ORGANIZE YOUR SPACES" title="Locations" description="Give every camera and sighting a place in your workspace." action={user.role === 'admin' && <button className="button primary" onClick={() => { setFailure(''); setOpen(true); }}><Plus size={17} />Add location</button>} /><ErrorMessage message={error} />{loading ? <Loading /> : data.length ? <div className="location-grid">{data.map(location => <article className="panel location-card" key={location.id}><span className="location-icon"><Building2 size={27} /></span><span className="small-kicker">{location.building}</span><h2>{location.name}</h2><p><MapPin size={15} />{location.floor}</p></article>)}</div> : <section className="panel"><Empty title="Map out your workspace" description="Add your first building, floor and zone before registering cameras." /></section>}
    {open && <Modal title="Add a location" close={() => setOpen(false)}><form onSubmit={submit} className="form"><ErrorMessage message={failure} /><label>Zone / location name<input name="name" required maxLength={100} placeholder="e.g. Main reception" /></label><div className="form-grid"><label>Building<input name="building" required defaultValue="Main building" maxLength={100} /></label><label>Floor<input name="floor" required defaultValue="Ground floor" maxLength={100} /></label></div><div className="form-footer"><button type="button" className="button secondary" onClick={() => setOpen(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? 'Saving…' : 'Save location'}</button></div></form></Modal>}
  </>;
}
