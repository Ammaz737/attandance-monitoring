import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Clock3, MapPin, Route, Video } from 'lucide-react';
import { useResource } from '../../hooks/useResource';
import { time, today } from '../../lib/api/client';
import type { Camera, Person, Sighting } from '../../types';
import { Badge, Empty, ErrorMessage, Initials, Loading, PageHeading } from '../../components/ui/shared';

export default function Tracking() {
  const [params, setParams] = useSearchParams();
  const personId = params.get('person') || '';
  const [day, setDay] = useState(today());
  const people = useResource<Person[]>('/people', []);
  const cameras = useResource<Camera[]>('/cameras', [], 5000);
  const sightings = useResource<Sighting[]>(`/sightings?day=${day}${personId ? `&person_id=${personId}` : ''}`, [], 5000);
  const person = people.data.find(p => p.id === personId);
  const latest = sightings.data[0];
  const latestCamera = cameras.data.find(camera => camera.id === latest?.camera_id);
  const fresh = latest && Date.now() - Date.parse(latest.occurred_at) < 30000 && latestCamera?.status === 'live';
  const seenNow = fresh && person?.open_session;
  return <><PageHeading eyebrow="FOLLOW THE CONFIRMED EVIDENCE" title="Location tracking" description="Camera-based sightings and a chronological view of each person’s movement." /><ErrorMessage message={people.error || cameras.error || sightings.error} />
    <section className="panel tracking-filters"><label>Person<select value={personId} onChange={e => setParams(e.target.value ? { person: e.target.value } : {})}><option value="">All people</option>{people.data.map(p => <option key={p.id} value={p.id}>{p.name} · {p.employee_id}</option>)}</select></label><label>Date<input type="date" value={day} onChange={e => e.target.value && setDay(e.target.value)} /></label><div className="tracking-note"><MapPin size={18} /><span>Locations reflect camera coverage.<br />Unobserved movement remains unknown.</span></div></section>
    {person && <div className="tracking-summary panel"><Initials name={person.name} /><div><h2>{person.name}</h2><p>{person.employee_id} · {person.department}</p></div><div className="last-location"><span>{seenNow ? 'Seen now' : 'Last confirmed sighting'}</span><strong>{latest?.location_name || 'Location unknown'}</strong><small>{latest ? `${time(latest.occurred_at, true)} PKT` : 'No sightings for this date'}</small></div><Badge tone={seenNow ? 'green' : 'gray'}>{person.open_session ? seenNow ? 'Seen now' : 'Open session · last seen only' : 'No open session'}</Badge></div>}
    <div className="tracking-columns"><section className="panel"><div className="section-title"><div><h2>Movement timeline</h2><p>{sightings.data.length} confirmed sightings · {day}</p></div><Route size={20} className="muted" /></div>{sightings.loading ? <Loading /> : sightings.data.length ? <div className="timeline">{sightings.data.map((item, index) => <div className="timeline-item" key={item.id}><span className="timeline-point"><MapPin size={16} /></span><div className="timeline-content"><div><strong>{item.location_name}</strong>{index === 0 && person && <Badge tone="green">Latest sighting</Badge>}</div><span>{item.name} · {item.camera_name}</span><small><Clock3 size={12} />{time(item.occurred_at, true)} PKT · Match score {item.confidence.toFixed(2)}</small></div><Link className="icon-button" aria-label={`Recordings for ${item.name} at ${item.location_name}`} to={`/recordings?person=${item.person_id}&camera=${item.camera_id}&day=${day}&at=${encodeURIComponent(item.occurred_at)}`}><Video size={18} /></Link></div>)}</div> : <Empty title="No confirmed movement yet" description="Sightings appear when a registered face is confirmed by an active camera. Blind spots are never inferred." />}</section>
      <section className="panel coverage-panel"><div className="section-title"><div><h2>Camera coverage</h2><p>Registered observation points</p></div></div>{cameras.data.length ? <div className="coverage-list">{cameras.data.map(camera => <div className={camera.id === latest?.camera_id ? 'coverage-item highlighted' : 'coverage-item'} key={camera.id}><span className="coverage-pin"><MapPin size={18} /></span><div><strong>{camera.location_name}</strong><span>{camera.name} · {camera.floor}</span></div><i className={camera.status === 'live' ? 'live-dot' : 'offline-dot'} /></div>)}</div> : <Empty title="No coverage points" description="Locations appear as cameras are registered." />}<Link className="text-link" to="/cameras">Manage coverage <ArrowUpRight size={15} /></Link></section></div>
  </>;
}
