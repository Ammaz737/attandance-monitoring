import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Download, Play, Video } from 'lucide-react';
import { useResource } from '../../hooks/useResource';
import { API, time, today } from '../../lib/api/client';
import type { Camera, Location, Person, Recording } from '../../types';
import { Badge, Empty, ErrorMessage, Loading, Modal, PageHeading } from '../../components/ui/shared';

export default function Recordings() {
  const [params, setParams] = useSearchParams();
  const day = params.get('day') || today();
  const camera = params.get('camera') || '';
  const person = params.get('person') || '';
  const location = params.get('location') || '';
  const [selected, setSelected] = useState<Recording | null>(null);
  const [playError, setPlayError] = useState('');
  const cameras = useResource<Camera[]>('/cameras', []);
  const locations = useResource<Location[]>('/locations', []);
  const visibleCameras = cameras.data.filter(item => !location || item.location_id === location);
  const people = useResource<Person[]>('/people', []);
  const { data, loading, error } = useResource<Recording[]>(`/recordings?day=${day}&camera_id=${camera}&person_id=${person}&location_id=${location}`, [], 10000);
  function filter(key: string, value: string) { const next = new URLSearchParams(params); value ? next.set(key, value) : next.delete(key); if (key === 'location') next.delete('camera'); next.delete('at'); setSelected(null); setParams(next); }
  const targetAt = params.get('at');
  return <><PageHeading eyebrow="YOUR WORKSPACE, REVISITABLE" title="Recordings" description="Find camera segments by date, location or a person’s confirmed sightings." /><ErrorMessage message={error || cameras.error || people.error || locations.error} /><section className="panel"><div className="recording-filters"><label>Date<input type="date" value={day} onChange={e => e.target.value && filter('day', e.target.value)} /></label><label htmlFor="recording-location">Location<select id="recording-location" name="location" value={location} onChange={e => filter('location', e.target.value)}><option value="">All locations</option>{locations.data.map(item => <option key={item.id} value={item.id}>{[item.name, item.building, item.floor].filter(Boolean).join(' / ')}</option>)}</select></label><label>Camera<select value={camera} onChange={e => filter('camera', e.target.value)}><option value="">All cameras</option>{visibleCameras.map(c => <option key={c.id} value={c.id}>{c.name} · {c.location_name}</option>)}</select></label><label>Person<select value={person} onChange={e => filter('person', e.target.value)}><option value="">All people</option>{people.data.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label></div>{loading ? <Loading /> : data.length ? <div className="table-wrap"><table><thead><tr><th>Camera / location</th><th>Started</th><th>Ended</th><th>Size</th><th>Status</th><th /></tr></thead><tbody>{data.map(item => <tr key={item.id}><td><div className="person-cell"><span className="avatar"><Video size={20} /></span><span><strong>{item.camera_name}</strong><small>{item.location_name}</small></span></div></td><td>{time(item.started_at, true)}</td><td>{time(item.ended_at, true)}</td><td>{item.bytes ? `${(item.bytes / 1048576).toFixed(1)} MB` : '—'}</td><td><Badge tone={item.status === 'ready' ? 'green' : item.status === 'recording' ? 'blue' : 'gray'}>{item.status}</Badge></td><td>{item.status === 'ready' && <div className="table-actions"><button className="button secondary compact" onClick={() => { setSelected(item); setPlayError(''); }}><Play size={14} />Play</button><a href={`${API}/recordings/${item.id}/file?download=true`} className="icon-button" aria-label="Download segment"><Download size={17} /></a></div>}</td></tr>)}</tbody></table></div> : <Empty title="No recordings for this selection" description="Enable recording on a camera. Completed segments appear here when FFmpeg finishes encoding." />}</section><div className="notice monitoring-note">Person filters find video associated with confirmed sightings. Playback includes the camera’s full scene. Expired segments retain their event history.</div>
    {selected && <Modal title={`${selected.camera_name} · ${time(selected.started_at, true)} PKT`} wide close={() => setSelected(null)}><div className="form"><ErrorMessage message={playError} /><video className="playback-video" controls playsInline preload="metadata" width={1280} height={720} src={`${API}/recordings/${selected.id}/file`} onError={() => setPlayError('Playback unavailable. The segment may have expired or its codec is unsupported.')} onLoadedMetadata={event => { if (targetAt) { const offset = (Date.parse(targetAt) - Date.parse(selected.started_at)) / 1000; if (offset >= 0 && offset < event.currentTarget.duration) event.currentTarget.currentTime = offset; } }} /><span className="muted small">{selected.location_name} · Video timestamps are indexed in UTC and displayed in PKT.</span><a className="button secondary align-start" href={`${API}/recordings/${selected.id}/file?download=true`}><Download size={16} />Download segment</a></div></Modal>}
  </>;
}
