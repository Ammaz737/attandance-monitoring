import { useEffect, useState } from 'react';
import { Camera as CameraIcon, Check, Edit3, Play, Plus, Power, RefreshCw, Wifi } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useResource } from '../../hooks/useResource';
import { api, patch, post } from '../../lib/api/client';
import type { Camera, Location } from '../../types';
import { Badge, Empty, ErrorMessage, Loading, Modal, PageHeading } from '../../components/ui/shared';
import { useUser } from '../../app/App';

export default function Cameras() {
  const cameras = useResource<Camera[]>('/cameras', [], 5000);
  const locations = useResource<Location[]>('/locations', []);
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Camera | null>(null);
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [tested, setTested] = useState('');
  const [preview, setPreview] = useState('');
  const [sourceType, setSourceType] = useState<'webcam' | 'network'>('webcam');
  const [webcams, setWebcams] = useState<{ source: string; name: string }[]>([]);
  const [scanning, setScanning] = useState(false);
  const [discoveryError, setDiscoveryError] = useState('');
  const [scanRevision, setScanRevision] = useState(0);
  const [form, setForm] = useState({ name: '', location_id: '', source: '', role: 'monitoring', recording: false, line_x: 0.5, entry_direction: 'right', retention_days: 7 });
  const user = useUser();
  useEffect(() => {
    if (!open || sourceType !== 'webcam') { setScanning(false); return; }
    const controller = new AbortController();
    setScanning(true); setDiscoveryError(''); setWebcams([]);
    api<{ devices: { source: string; name: string }[] }>('/cameras/webcams', { signal: controller.signal })
      .then(({ devices }) => {
        if (controller.signal.aborted) return;
        setWebcams(devices);
        setForm(current => {
          if (current.source || !devices.length) return current;
          return { ...current, source: devices[0].source, name: current.name || devices[0].name };
        });
      })
      .catch(error => { if (!controller.signal.aborted) setDiscoveryError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setScanning(false); });
    return () => controller.abort();
  }, [open, sourceType, scanRevision]);
  const set = (name: string, value: unknown) => { setForm(current => ({ ...current, [name]: value })); if (name === 'source') { setTested(''); setPreview(''); } };
  function launch(camera: Camera | null = null) {
    setEdit(camera); setStep(0); setTested(''); setPreview(''); setError('');
    setSourceType(camera ? camera.source_type || 'network' : 'webcam');
    setForm(camera ? { name: camera.name, location_id: camera.location_id, source: camera.webcam_source || '', role: camera.role, recording: !!camera.recording, line_x: camera.line_x, entry_direction: camera.entry_direction, retention_days: camera.retention_days } : { name: '', location_id: locations.data[0]?.id || '', source: '', role: 'monitoring', recording: false, line_x: 0.5, entry_direction: 'right', retention_days: 7 });
    setOpen(true);
  }
  async function test() {
    setBusy(true); setError(''); setTested('');
    try { const result = await post('/cameras/test', form); setTested(`Connected · ${result.width} × ${result.height} frame received`); setPreview(result.preview ? `data:image/jpeg;base64,${result.preview}` : ''); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function save() {
    setBusy(true); setError('');
    try { if (edit) await patch(`/cameras/${edit.id}`, form); else await post('/cameras', form); setOpen(false); await cameras.reload(); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  async function toggle(camera: Camera) {
    setError(''); setBusy(true);
    try { await post(`/cameras/${camera.id}/toggle`); await cameras.reload(); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }
  return <><PageHeading eyebrow="CONNECT YOUR WORKSPACE" title="Cameras" description="Register streams, configure entry points and keep every camera healthy." action={user.role === 'admin' && <button className="button primary" onClick={() => launch()}><Plus size={17} />Register camera</button>} /><ErrorMessage message={cameras.error || (!open && error) || ''} />
    <div className="mini-stats"><span><i className="live-dot" />{cameras.data.filter(c => c.status === 'live').length} live</span><span>{cameras.data.length} registered cameras</span><Link to="/monitoring">Open monitoring <Play size={13} /></Link></div>
    {cameras.loading ? <Loading /> : cameras.data.length ? <div className="camera-config-grid">{cameras.data.map(camera => <article className="panel camera-config" key={camera.id}><div className="camera-config-top"><span className="location-icon"><CameraIcon size={24} /></span><Badge tone={camera.status === 'live' ? 'green' : camera.status === 'reconnecting' ? 'amber' : 'gray'}>{camera.status}</Badge></div><h2>{camera.name}</h2><p>{camera.location_name} · {camera.floor}</p><div className="camera-specs"><span>Purpose<strong>{camera.role}</strong></span><span>Recording<strong>{camera.recording ? `${camera.retention_days} day retention` : 'Off'}</strong></span><span>Stream<strong>{camera.fps} FPS · MJPEG preview</strong></span></div>{camera.message && <p className="small muted">{camera.message}</p>}{camera.recording_error && <p className="small amber-text">{camera.recording_error}</p>}{user.role === 'admin' && <div className="card-actions"><button className="button secondary" disabled={!!camera.enabled || busy} onClick={() => launch(camera)}><Edit3 size={15} />Configure</button><button className={`button ${camera.enabled ? 'secondary' : 'primary'}`} disabled={busy} onClick={() => toggle(camera)}><Power size={15} />{camera.enabled ? 'Stop' : 'Activate'}</button></div>}</article>)}</div> : <section className="panel"><Empty title="Connect your first camera" description="Add an RTSP camera, HTTP stream or a webcam on the backend computer." action={<Link to="/locations" className="text-link">Manage locations first</Link>} /></section>}
    {open && <Modal title={edit ? 'Configure camera' : 'Register a camera'} close={() => setOpen(false)} wide><div className="wizard-steps">{['Source & location', 'Detection rules', 'Recording & finish'].map((name, i) => <span key={name} className={step === i ? 'current' : step > i ? 'complete' : ''}><b>{step > i ? <Check size={13} /> : i + 1}</b>{name}</span>)}</div><div className="form"><ErrorMessage message={error} />
      {preview && <div className="camera-test-preview"><img src={preview} alt="Camera connection test frame" />{step === 1 && form.role !== 'monitoring' && <span style={{ left: `${form.line_x * 100}%` }}>Attendance crossing line</span>}</div>}
      {step === 0 && <>
        <div className="source-switch" role="group" aria-label="Camera source">
          <button className="button secondary" aria-pressed={sourceType === 'webcam'} onClick={() => { if (sourceType !== 'webcam') { setSourceType('webcam'); set('source', ''); } }}><CameraIcon size={18} />Webcam</button>
          <button className="button secondary" aria-pressed={sourceType === 'network'} onClick={() => { if (sourceType !== 'network') { setSourceType('network'); set('source', ''); } }}><Wifi size={18} />IP / network camera</button>
        </div>
        {sourceType === 'webcam' ? <>
          <div className="webcam-picker"><label>Detected webcam<select aria-label="Detected webcam" value={form.source} disabled={scanning || !webcams.length} onChange={event => {
            const device = webcams.find(item => item.source === event.target.value);
            set('source', event.target.value);
            setForm(current => ({ ...current, name: !current.name || webcams.some(item => item.name === current.name) ? device?.name || current.name : current.name }));
          }}>
            {!form.source && <option value="">{scanning ? 'Detecting connected webcams…' : 'No webcam selected'}</option>}
            {form.source && !webcams.some(device => device.source === form.source) && <option value={form.source}>Previously selected webcam (not detected)</option>}
            {webcams.map(device => <option key={device.source} value={device.source}>{device.name}</option>)}
          </select></label><button className="button secondary" aria-label="Rescan webcams" disabled={scanning} onClick={() => setScanRevision(value => value + 1)}><RefreshCw size={16} className={scanning ? 'spin' : ''} />Rescan</button></div>
          <div className="webcam-status" role="status">{scanning ? 'Looking for built-in and USB webcams…' : discoveryError ? <ErrorMessage message={discoveryError} /> : webcams.length ? `${webcams.length} webcam${webcams.length === 1 ? '' : 's'} detected. Choose one, then test its preview.` : 'No webcams detected. Connect a webcam, check system camera permissions, then rescan.'}</div>
          <span className="small muted">These webcams are connected to the computer running Presence. No camera index or stream URL is needed.</span>
        </> : <label>RTSP / HTTP stream URL<input type="password" autoComplete="off" value={form.source} onChange={e => set('source', e.target.value)} placeholder={edit ? 'Leave blank to keep the existing network source' : 'rtsp://user:password@camera/stream'} /></label>}
        <div className="form-grid"><label>Camera name<input value={form.name} minLength={2} maxLength={100} required placeholder="e.g. Main entrance" onChange={e => set('name', e.target.value)} /></label><label>Location<select value={form.location_id} onChange={e => set('location_id', e.target.value)}><option value="">Select a location</option>{locations.data.map(location => <option key={location.id} value={location.id}>{location.name} · {location.floor}</option>)}</select></label></div>
        {!locations.data.length && <div className="notice">Add a location from the Locations screen before registering this camera. You can test its preview first.</div>}
        <button className="button secondary align-start" disabled={busy || scanning || !form.source || form.name.trim().length < 2} onClick={test}><Play size={15} />{busy ? 'Testing connection…' : sourceType === 'webcam' ? 'Preview webcam' : 'Test connection'}</button>
        {tested && <div className="success"><Check size={17} />{tested}</div>}
      </>}
      {step === 1 && <><label>Camera purpose<select value={form.role} onChange={e => set('role', e.target.value)}><option value="monitoring">Monitoring only</option><option value="entry">Entry only</option><option value="exit">Exit only</option><option value="both">Entry and exit</option></select></label>{form.role !== 'monitoring' && <><label>Vertical line position · {Math.round(form.line_x * 100)}%<input type="range" min="0.05" max="0.95" step="0.01" value={form.line_x} onChange={e => set('line_x', Number(e.target.value))} /></label><div className="line-diagram"><span>Camera frame</span><div style={{ left: `${form.line_x * 100}%` }}><b>Attendance line</b></div></div><label>Entry direction<select value={form.entry_direction} onChange={e => set('entry_direction', e.target.value)}><option value="right">Left → right</option><option value="left">Right → left</option></select></label></>}<div className="notice"><ScanNotice />Identity confirmation and directional crossing are both required. Automatic attendance is controlled by the backend model configuration.</div></>}
      {step === 2 && <><label className="checkbox"><input type="checkbox" checked={form.recording} onChange={e => set('recording', e.target.checked)} /><span>Record continuous video in 60-second segments</span></label>{form.recording && <label>Retention (days)<input type="number" min={1} max={90} value={form.retention_days} onChange={e => set('retention_days', Number(e.target.value))} /></label>}<div className="notice">Recording requires FFmpeg with H.264 support. Camera activation is a separate step after saving.</div><div className="summary-box"><strong>{form.name}</strong><span>{locations.data.find(l => l.id === form.location_id)?.name} · {form.role}</span><span>{tested || (edit ? 'Existing protected source retained unless replaced' : 'Connection not tested')}</span></div></>}
      <div className="form-footer"><button className="button secondary" onClick={() => step ? setStep(step - 1) : setOpen(false)}>{step ? 'Back' : 'Cancel'}</button>{step < 2 ? <button className="button primary" disabled={form.name.trim().length < 2 || !form.location_id || scanning || (!form.source && (sourceType === 'webcam' || !edit || edit.source_type !== 'network'))} onClick={() => setStep(step + 1)}>Continue</button> : <button className="button primary" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save camera'}</button>}</div>
    </div></Modal>}
  </>;
}
function ScanNotice() { return <CameraIcon size={20} />; }
