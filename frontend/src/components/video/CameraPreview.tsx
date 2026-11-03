import { useEffect, useRef, useState } from 'react';
import { Maximize2, ScanFace, VideoOff } from 'lucide-react';
import { API, time } from '../../lib/api/client';
import type { Camera } from '../../types';
import { Badge } from '../ui/shared';

export default function CameraPreview({ camera }: { camera: Camera }) {
  const container = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(true);
  const [failed, setFailed] = useState(false);
  const [analysis, setAnalysis] = useState(false);
  useEffect(() => {
    const observer = new IntersectionObserver(entries => setVisible(entries[0].isIntersecting && !document.hidden));
    if (container.current) observer.observe(container.current);
    const visibility = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', visibility);
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', visibility); };
  }, []);
  useEffect(() => setFailed(false), [camera.status]);
  const live = camera.status === 'live';
  return <div className="camera-card" ref={container}>
    <div className="camera-feed">
      {visible && live && !failed && (!analysis || camera.last_analysis_at) ? <img src={`${API}/cameras/${camera.id}/stream?analysis=${analysis}`} alt={`${analysis ? 'Analyzed frame' : 'Live view'} of ${camera.name}`} onError={() => setFailed(true)} /> :
        <div className="feed-placeholder"><VideoOff size={30} /><strong>{failed ? 'Preview unavailable' : live ? analysis && !camera.last_analysis_at ? 'Waiting for analyzed frames' : 'Preview paused' : camera.status === 'stopped' ? 'Camera stopped' : 'Waiting for stream'}</strong><span>{camera.message || (live ? 'Live capture and AI processing run independently.' : 'Activate this camera to start monitoring.')}</span></div>}
      <span className="feed-label"><span className={live ? 'live-dot' : 'offline-dot'} />{live ? analysis ? 'ANALYZED FRAMES' : 'LIVE' : camera.status.toUpperCase()}</span>
      <button className="fullscreen" aria-label={`Fullscreen ${camera.name}`} onClick={() => container.current?.requestFullscreen()}><Maximize2 size={16} /></button>
      {live && <><button className="analysis-toggle" aria-pressed={analysis} onClick={() => { setAnalysis(!analysis); setFailed(false); }}><ScanFace size={13} />{analysis ? 'Show live' : 'Detection view'}</button><span className="feed-timestamp">{time(analysis ? camera.last_analysis_at : camera.last_frame_at)} PKT · {analysis ? 'Analysis snapshot' : `${camera.fps} FPS`}</span></>}
    </div>
    <div className="camera-caption"><div><strong>{camera.name}</strong><span>{camera.location_name} · {camera.floor}</span></div><Badge tone={live ? 'green' : 'gray'}>{camera.role}</Badge></div>
    {camera.recording_error && <div className="camera-warning">{camera.recording_error}</div>}
  </div>;
}
