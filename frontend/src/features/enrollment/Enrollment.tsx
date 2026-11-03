import { useEffect, useRef, useState } from 'react';
import { Camera, Check, RefreshCw, ScanFace, Square, Trash2 } from 'lucide-react';
import { api, post } from '../../lib/api/client';
import type { Person } from '../../types';
import { ErrorMessage, Modal } from '../../components/ui/shared';

type Device = { id: string; name: string };

function cameraError(error: unknown) {
  const name = error instanceof DOMException ? error.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Browser camera access was denied. Use Workspace camera, or allow camera access in this browser’s site settings.';
  if (name === 'NotReadableError' || name === 'AbortError') return 'The browser could not open the camera. It may already be in use. Use Workspace camera to share an active monitoring feed.';
  if (name === 'NotFoundError') return 'No browser camera was found. Try Workspace camera or connect a webcam.';
  return 'This browser could not start its camera. Use Workspace camera to capture through Presence instead.';
}

export default function Enrollment({ person, close, done }: { person: Person; close: () => void; done: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const token = useRef<string | null>(null);
  const alive = useRef(true);
  const generation = useRef(0);
  const [mode, setMode] = useState<'workspace' | 'browser'>('workspace');
  const [devices, setDevices] = useState<Device[]>([]);
  const [device, setDevice] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [discovering, setDiscovering] = useState(true);
  const [discoveryError, setDiscoveryError] = useState('');
  const [session, setSession] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState('');
  const [browserReady, setBrowserReady] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
  const [starting, setStarting] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const base = `/people/${person.id}/enrollment/preview`;

  function releasePreview(id: string) {
    return api(`${base}/${id}`, { method: 'DELETE', keepalive: true }).catch(() => {});
  }

  function stop() {
    generation.current += 1;
    stream.current?.getTracks().forEach(track => track.stop());
    stream.current = null;
    const old = token.current;
    token.current = null;
    setSession(null); setSnapshot(''); setBrowserReady(false); setVideoReady(false); setStarting(false);
    return old ? releasePreview(old) : Promise.resolve();
  }

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false; generation.current += 1;
      stream.current?.getTracks().forEach(track => track.stop());
      if (token.current) void releasePreview(token.current);
      token.current = null;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setDiscovering(true); setDiscoveryError('');
    api<{ devices: Device[]; warning: string }>('/enrollment/cameras', { signal: controller.signal })
      .then(result => {
        if (controller.signal.aborted) return;
        setDevices(result.devices); setDiscoveryError(result.warning);
        setDevice(current => result.devices.some(item => item.id === current) ? current : result.devices[0]?.id || '');
      }).catch(error => { if (!controller.signal.aborted) setDiscoveryError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setDiscovering(false); });
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const frame = await api<{ ready: boolean; image?: string; error?: string }>(`${base}/${session}`);
        if (cancelled) return;
        if (frame.error) { setError(frame.error); void stop(); return; }
        if (frame.ready && frame.image) { setSnapshot(frame.image); setStarting(false); }
      } catch (error) {
        if (cancelled) return;
        setError((error as Error).message); void stop(); return;
      }
      if (!cancelled) timer = setTimeout(poll, document.hidden ? 1500 : 350);
    }
    void poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [session, base]);

  useEffect(() => {
    if (browserReady && video.current && stream.current) {
      video.current.srcObject = stream.current;
      void video.current.play().catch(() => setError('Video could not play. Stop the camera and try Workspace camera.'));
    }
  }, [browserReady]);

  async function start() {
    const stopped = stop();
    const attempt = generation.current;
    await stopped;
    if (!alive.current || generation.current !== attempt) return;
    setError(''); setStarting(true);
    try {
      if (mode === 'workspace') {
        const result = await post(base, { device_id: device });
        if (!alive.current || generation.current !== attempt) { void releasePreview(result.id); return; }
        token.current = result.id; setSession(result.id);
      } else {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error('Browser capture unavailable');
        const media = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
        if (!alive.current || generation.current !== attempt) { media.getTracks().forEach(track => track.stop()); return; }
        stream.current = media; setBrowserReady(true); setStarting(false);
      }
    } catch (error) {
      if (!alive.current || generation.current !== attempt) return;
      setError(mode === 'workspace' ? (error as Error).message : cameraError(error)); setStarting(false);
    }
  }

  async function capture() {
    if (files.length >= 8) return;
    let blob: Blob | null = null;
    if (mode === 'workspace' && snapshot) {
      const bytes = Uint8Array.from(atob(snapshot), character => character.charCodeAt(0));
      blob = new Blob([bytes], { type: 'image/jpeg' });
    } else if (mode === 'browser' && video.current?.videoWidth) {
      const element = video.current;
      const canvas = document.createElement('canvas'); canvas.width = element.videoWidth; canvas.height = element.videoHeight;
      canvas.getContext('2d')!.drawImage(element, 0, 0);
      blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .95));
    }
    if (blob && alive.current) setFiles(current => [...current, new File([blob!], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' })].slice(0, 8));
  }

  async function submit() {
    setBusy(true); setError('');
    const body = new FormData(); files.forEach(file => body.append('files', file));
    try { await api(`/people/${person.id}/enrollment`, { method: 'POST', body }); done(); close(); }
    catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }

  const active = !!session || browserReady;
  const ready = mode === 'workspace' ? !!snapshot : videoReady;
  return <Modal title={`Face enrollment · ${person.name}`} close={close} wide><div className="form">
    <div className="notice"><ScanFace size={20} /><span>Capture 3–8 clear images: front, slight left and slight right. Existing enrollment is replaced only after every sample passes.</span></div>
    <ErrorMessage message={error} />
    <div className="source-switch" role="group" aria-label="Enrollment camera source">
      <button className="button secondary" aria-pressed={mode === 'workspace'} onClick={() => { void stop(); setMode('workspace'); setError(''); }}>Workspace camera</button>
      <button className="button secondary" aria-pressed={mode === 'browser'} onClick={() => { void stop(); setMode('browser'); setError(''); }}>Browser camera</button>
    </div>
    {mode === 'workspace' ? <><div className="webcam-picker"><label>Enrollment camera<select aria-label="Enrollment camera" disabled={discovering || active || starting} value={device} onChange={event => setDevice(event.target.value)}>
      {!device && <option value="">{discovering ? 'Finding cameras…' : 'No camera detected'}</option>}{devices.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}
    </select></label><button className="button secondary" aria-label="Refresh enrollment cameras" disabled={discovering || active || starting} onClick={() => setRefresh(value => value + 1)}><RefreshCw size={16} /></button></div>
    {discoveryError && <div className="notice">{discoveryError}</div>}<p className="small muted">Uses cameras connected to Presence. A running monitoring feed is shared, without opening the webcam twice. No browser camera permission is needed.</p></> : <p className="small muted">Uses this browser’s camera permission. If access is blocked or the camera is busy, switch to Workspace camera.</p>}
    {active ? <><div className="capture-area">
      {mode === 'workspace' ? snapshot ? <img className="enrollment-preview" src={`data:image/jpeg;base64,${snapshot}`} alt="Live enrollment camera preview" /> : <div className="enrollment-opening" role="status">Starting camera…</div> :
        <video ref={video} autoPlay muted playsInline width={1280} height={720} onLoadedData={() => setVideoReady(true)} onError={() => setError('Browser video failed. Try Workspace camera.')} />}
      <button className="button primary" onClick={capture} disabled={!ready || files.length >= 8 || busy}><Camera size={17} />Capture sample</button>
    </div><button className="button secondary align-start" onClick={() => void stop()}><Square size={14} />Stop camera</button></> :
      <button className="button secondary" disabled={starting || busy || mode === 'workspace' && (discovering || !device)} onClick={start}><Camera size={18} />{starting ? 'Starting camera…' : 'Start camera'}</button>}
    <label>Or upload clear face photos<input type="file" accept="image/jpeg,image/png,image/webp" multiple disabled={busy} onChange={event => { const selected = Array.from(event.target.files || []); setFiles(current => [...current, ...selected].slice(0, 8)); }} /></label>
    <div className="sample-list">{files.map((file, index) => <div key={`${file.name}-${index}`}><Check size={15} /><span>{file.name}</span><button className="icon-button" disabled={busy} aria-label={`Remove sample ${index + 1}`} onClick={() => setFiles(current => current.filter((_, i) => i !== index))}><Trash2 size={15} /></button></div>)}</div>
    <span className="muted small">{files.length} / 8 samples selected · At least 3 required</span>
    <div className="form-footer"><button className="button secondary" onClick={close}>Cancel</button><button className="button primary" disabled={busy || files.length < 3} onClick={submit}>{busy ? 'Checking samples…' : 'Save face enrollment'}</button></div>
  </div></Modal>;
}
