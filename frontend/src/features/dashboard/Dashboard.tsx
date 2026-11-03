import { Link } from 'react-router-dom';
import { ArrowDownLeft, ArrowRight, ArrowUpRight, Camera, Check, ClipboardCheck, MapPin, Plus, ScanFace, Users } from 'lucide-react';
import { useResource } from '../../hooks/useResource';
import { Badge, Empty, ErrorMessage, Initials, Loading, PageHeading, SectionTitle } from '../../components/ui/shared';
import type { Camera as CameraType } from '../../types';
import CameraPreview from '../../components/video/CameraPreview';
import { time } from '../../lib/api/client';

export default function Dashboard() {
  const { data, loading, error } = useResource<any>('/dashboard', null, 10000);
  const cameras = useResource<CameraType[]>('/cameras', [], 5000);
  if (loading) return <Loading />;
  if (!data) return <ErrorMessage message={error} />;
  const counts = data.counts;
  const live = cameras.data.filter(camera => camera.status === 'live').length;
  const stats = [
    { title: 'Currently present', value: counts.present, detail: 'Open attendance sessions', Icon: Users, tone: 'green' },
    { title: 'Check-ins today', value: counts.entries, detail: 'Confirmed arrivals', Icon: ArrowDownLeft, tone: 'blue' },
    { title: 'Check-outs today', value: counts.exits, detail: 'Completed departures', Icon: ArrowUpRight, tone: 'orange' },
    { title: 'Cameras online', value: `${live}`, detail: `${cameras.data.length} cameras registered`, Icon: Camera, tone: 'purple' },
  ];
  return <><PageHeading eyebrow="YOUR WORKSPACE, AT A GLANCE" title="Workspace overview" description="A clear picture of your people, cameras and spaces." action={<Link className="button primary" to="/monitoring"><ScanFace size={18} />Open live monitoring</Link>} /><ErrorMessage message={error || cameras.error} />
    <div className="overview-banner"><div><Badge tone="light">WORKSPACE ACTIVITY</Badge><h2>Every arrival has a story.<br />Keep yours in view.</h2><p>Your attendance and camera activity, connected in one place.</p><Link to="/attendance">View attendance <ArrowRight size={17} /></Link></div><div className="banner-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" /><span className="art-node node-a"><Users /></span><span className="art-node node-b"><MapPin /></span><span className="art-node node-c"><Camera /></span><div className="art-center"><ScanFace size={42} /></div><span className="art-check"><Check size={16} /></span></div><div className="banner-date"><span>{new Date(`${data.date}T12:00:00`).toLocaleDateString('en-GB', { weekday: 'long' })}</span><strong>{new Date(`${data.date}T12:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}</strong><span>Asia / Karachi</span></div></div>
    <div className="stat-grid">{stats.map(({ title, value, detail, Icon, tone }) => <div className="stat-card" key={title}><div className="stat-top"><span>{title}</span><span className={`stat-icon ${tone}`}><Icon size={19} /></span></div><strong>{value}</strong><p>{detail}</p></div>)}</div>
    {counts.people === 0 && <div className="setup-strip"><span className="setup-icon"><ClipboardCheck size={24} /></span><div><strong>Let’s bring your workspace online.</strong><p>Add a location, connect a camera, then register your first person.</p></div><Link to="/locations" className="button secondary">Start setup <ArrowRight size={16} /></Link></div>}
    <div className="dashboard-columns"><section className="panel"><SectionTitle title="Live camera overview" detail="A window into your connected spaces" action={<Link className="text-link" to="/monitoring">View all <ArrowUpRight size={15} /></Link>} />{cameras.data.length ? <div className="dashboard-camera-grid">{cameras.data.slice(0, 2).map(camera => <CameraPreview key={camera.id} camera={camera} />)}</div> : <Empty title="Your spaces will appear here" description="Register a camera to see its live stream and connection status." action={<Link to="/cameras" className="button secondary"><Plus size={16} />Connect a camera</Link>} />}</section>
      <section className="panel"><SectionTitle title="Recent attendance" detail="Latest arrivals and departures" action={<Link className="text-link" to="/attendance">View all <ArrowUpRight size={15} /></Link>} />{data.events.length ? <div className="activity-list">{data.events.map((event: any) => <div className="activity-row" key={event.id}><Initials name={event.name} /><div><strong>{event.name}</strong><span>{event.camera_name || 'Manual attendance'}</span></div><div className="activity-end"><Badge tone={event.kind === 'IN' ? 'green' : 'gray'}>{event.kind === 'IN' ? 'Checked in' : 'Checked out'}</Badge><span>{time(event.occurred_at)}</span></div></div>)}</div> : <Empty title="A fresh start" description="Confirmed attendance events will appear here as your team arrives." />}</section></div>
    <div className="bottom-note"><span><span className="live-dot" />Live updates from your workspace</span><Link to="/settings">{counts.reviews ? `${counts.reviews} items need review` : 'Manage recognition and workspace settings'}<ArrowRight size={14} /></Link></div>
  </>;
}
