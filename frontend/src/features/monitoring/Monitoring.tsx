import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Camera, Grid2X2, Plus, Square } from 'lucide-react';
import { useResource } from '../../hooks/useResource';
import type { Camera as CameraType, Location } from '../../types';
import CameraPreview from '../../components/video/CameraPreview';
import { Empty, ErrorMessage, Loading, PageHeading } from '../../components/ui/shared';

export default function Monitoring() {
  const { data, loading, error } = useResource<CameraType[]>('/cameras', [], 3000);
  const locations = useResource<Location[]>('/locations', []);
  const [location, setLocation] = useState('');
  const [grid, setGrid] = useState(2);
  const filtered = data.filter(camera => !location || camera.location_id === location);
  return <><PageHeading eyebrow="A LIVE VIEW OF YOUR SPACES" title="Live monitoring" description="Real camera frames with timestamped detection overlays when AI is configured." action={<Link className="button secondary" to="/cameras"><Plus size={16} />Manage cameras</Link>} /><ErrorMessage message={error || locations.error} /><div className="monitor-toolbar"><div className="mini-stats"><span><i className="live-dot" />{data.filter(c => c.status === 'live').length} live</span><span>{data.reduce((n, c) => n + c.detections, 0)} recent detections</span></div><div className="filter-actions"><select aria-label="Filter by location" value={location} onChange={e => setLocation(e.target.value)}><option value="">All locations</option>{locations.data.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button className={`icon-button ${grid === 1 ? 'selected' : ''}`} aria-label="Single column" onClick={() => setGrid(1)}><Square size={18} /></button><button className={`icon-button ${grid === 2 ? 'selected' : ''}`} aria-label="Two columns" onClick={() => setGrid(2)}><Grid2X2 size={18} /></button></div></div>
    {loading ? <Loading /> : filtered.length ? <div className={`monitor-grid columns-${grid}`}>{filtered.map(camera => <CameraPreview key={camera.id} camera={camera} />)}</div> : <section className="panel"><Empty title="Your live workspace starts here" description="Register and activate cameras to view their streams. No camera feed is simulated." action={<Link className="button primary" to="/cameras"><Camera size={17} />Connect cameras</Link>} /></section>}
    <div className="notice monitoring-note">Live preview uses authenticated MJPEG. Detection overlays appear on analyzed frames only. Offscreen and hidden-tab previews pause to conserve resources.</div>
  </>;
}
