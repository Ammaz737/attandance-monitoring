import { createContext, useContext, useEffect, useState } from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { Activity, ArrowUpRight, Building2, Camera, ChevronRight, CircleHelp, ClipboardCheck, Clock3, FileBarChart2, Fingerprint, LayoutDashboard, LogOut, MapPin, Menu, Radio, Settings2, ShieldCheck, Users, Video, X } from 'lucide-react';
import { api, API, post } from '../lib/api/client';
import type { User } from '../types';
import { Badge, ErrorMessage, Loading } from '../components/ui/shared';
import Dashboard from '../features/dashboard/Dashboard';
import People from '../features/people/People';
import Cameras from '../features/cameras/Cameras';
import AttendancePage from '../features/attendance/Attendance';
import Monitoring from '../features/monitoring/Monitoring';
import Tracking from '../features/tracking/Tracking';
import Recordings from '../features/recordings/Recordings';
import Locations from '../features/locations/Locations';
import Settings from '../features/settings/Settings';
import Reports from '../features/reports/Reports';

const UserContext = createContext<User | null>(null);
export function useUser() { return useContext(UserContext)!; }

const navigation = [
  ['Overview', '/', LayoutDashboard], ['People', '/people', Users], ['Attendance', '/attendance', ClipboardCheck],
  ['Live monitoring', '/monitoring', Radio], ['Location tracking', '/tracking', MapPin], ['Recordings', '/recordings', Video],
  ['Reports', '/reports', FileBarChart2],
] as const;

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [setup, setSetup] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api('/auth/status').then(value => { setSetup(value.setup_required); setReady(true); }).catch(error => setError(error.message)); }, []);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    const credentials = { username: form.get('username'), password: form.get('password') };
    try {
      if (setup) await post('/auth/setup', credentials);
      onLogin(await post('/auth/login', credentials));
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><div className="login-story"><Link to="/" className="brand"><span className="brand-mark"><Fingerprint /></span>presence<span className="brand-period">.</span></Link><div><span className="eyebrow">A CLEARER VIEW OF YOUR WORKSPACE</span><h1>Every arrival.<br />Every space.<br /><em>Connected.</em></h1><p>Attendance, camera monitoring and person timelines, in one considered workspace.</p></div><span className="login-foot"><ShieldCheck size={17} /> Local processing. Protected records.</span></div>
    <div className="login-panel"><form onSubmit={submit} className="login-form"><span className="small-kicker">PRESENCE WORKSPACE</span><h2>{setup ? 'Make it your workspace.' : 'Welcome back.'}</h2><p>{setup ? 'Create your first administrator to get started.' : 'Sign in to see what’s happening across your spaces.'}</p><ErrorMessage message={error} />
      <label>Username<input name="username" autoComplete="username" minLength={3} maxLength={60} pattern="[a-zA-Z0-9_.-]+" required placeholder="Your username" /></label>
      <label>Password<input name="password" type="password" autoComplete={setup ? 'new-password' : 'current-password'} minLength={10} maxLength={128} required placeholder="At least 10 characters" /></label>
      <button className="button primary" disabled={busy || !ready}>{busy ? 'Please wait…' : setup ? 'Create workspace' : 'Sign in'}<ArrowUpRight size={18} /></button>
      <span className="muted small">{setup ? 'Initial setup is available from this computer only.' : 'Access is limited to authorized workspace users.'}</span>
    </form></div></main>;
}

function Shell({ user, logout }: { user: User; logout: () => void }) {
  const [connected, setConnected] = useState(false);
  const [menu, setMenu] = useState(false);
  const location = useLocation();
  useEffect(() => { setMenu(false); }, [location.pathname]);
  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') setMenu(false); };
    const resize = () => { if (window.innerWidth > 700) setMenu(false); };
    window.addEventListener('keydown', escape); window.addEventListener('resize', resize);
    return () => { window.removeEventListener('keydown', escape); window.removeEventListener('resize', resize); };
  }, []);
  useEffect(() => {
    const events = new EventSource(`${API}/events`, { withCredentials: true });
    const refresh = () => window.dispatchEvent(new Event('workspace-update'));
    events.onopen = () => { setConnected(true); refresh(); };
    events.addEventListener('ready', refresh);
    events.onmessage = refresh;
    events.onerror = () => setConnected(false);
    return () => events.close();
  }, []);
  const current = [...navigation, ['Cameras', '/cameras'], ['Locations', '/locations'], ['Settings', '/settings']].find(item => item[1] === location.pathname)?.[0] || 'Workspace';
  return <UserContext value={user}><div className="app-shell">
    <aside className={`sidebar ${menu ? 'open' : ''}`}><Link to="/" className="brand"><span className="brand-mark"><Fingerprint /></span>presence<span className="brand-period">.</span></Link>
      <div className="workspace-label"><span className="workspace-icon"><Building2 size={18} /></span><div><strong>My workspace</strong><span>Attendance & monitoring</span></div><ChevronRight size={15} /></div>
      <span className="nav-label">WORKSPACE</span><nav>{navigation.map(([label, path, Icon]) => <NavLink key={path} to={path} end={path === '/'}><Icon size={19} /><span>{label}</span>{path === '/monitoring' && <span className="nav-live" />}</NavLink>)}</nav>
      <span className="nav-label management">MANAGEMENT</span><nav><NavLink to="/cameras"><Camera size={19} />Cameras</NavLink><NavLink to="/locations"><Building2 size={19} />Locations</NavLink><NavLink to="/settings"><Settings2 size={19} />Settings</NavLink></nav>
      <div className="sidebar-bottom"><div className="local-card"><ShieldCheck size={21} /><strong>Your workspace, protected.</strong><p>Role-based access and an audit trail for every change.</p><Link to="/settings">Workspace settings <ArrowUpRight size={15} /></Link></div><div className="user-row"><span className="user-avatar">{user.username[0].toUpperCase()}</span><div><strong>{user.username}</strong><span>{user.role}</span></div><button className="icon-button" aria-label="Sign out" onClick={logout}><LogOut size={18} /></button></div></div>
    </aside>
    {menu && <button className="sidebar-scrim" aria-label="Close menu" onClick={() => setMenu(false)} />}
    <div className="main-shell" inert={menu || undefined}><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-menu" aria-label="Toggle navigation" aria-expanded={menu} onClick={() => setMenu(!menu)}>{menu ? <X size={20} /> : <Menu size={20} />}</button><span>Workspace</span><ChevronRight size={14} /><strong>{current}</strong></div><div className="topbar-right"><Badge tone={connected ? 'green' : 'amber'}>{connected ? 'Events connected' : 'Reconnecting events'}</Badge><span className="timezone"><Clock3 size={15} />Asia / Karachi</span><Link to="/settings" className="icon-button" aria-label="Workspace help and settings"><CircleHelp size={19} /></Link></div></header>
      <main className="page"><Routes><Route path="/" element={<Dashboard />} /><Route path="/people/*" element={<People />} /><Route path="/cameras" element={<Cameras />} /><Route path="/attendance" element={<AttendancePage />} /><Route path="/monitoring" element={<Monitoring />} /><Route path="/tracking" element={<Tracking />} /><Route path="/recordings" element={<Recordings />} /><Route path="/locations" element={<Locations />} /><Route path="/reports" element={<Reports />} /><Route path="/settings" element={<Settings />} /><Route path="*" element={<div className="empty"><h1>Page not found</h1><Link to="/">Return to overview</Link></div>} /></Routes></main>
      <footer className="app-footer"><span><Activity size={13} /> Presence workspace</span><span>All times shown in PKT · v0.1.0</span></footer>
    </div></div></UserContext>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api<User>('/auth/me').then(setUser).catch(() => {}).finally(() => setLoading(false));
    const expired = () => setUser(null);
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, []);
  if (loading) return <Loading />;
  if (!user) return <Login onLogin={setUser} />;
  return <Shell user={user} logout={async () => { try { await post('/auth/logout'); setUser(null); } catch { /* session remains visible on network failure */ } }} />;
}
