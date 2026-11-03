import { useEffect, useRef, type ReactNode } from 'react';
import { AlertCircle, ArrowUpRight, Camera, LoaderCircle, X } from 'lucide-react';

export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}><i />{children}</span>;
}

export function Empty({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty"><div className="empty-icon"><Camera size={25} /></div><h3>{title}</h3><p>{description}</p>{action}</div>;
}

export function ErrorMessage({ message }: { message: string }) {
  return message ? <div className="error" role="alert"><AlertCircle size={18} /><span>{message}</span></div> : null;
}

export function Loading() { return <div className="loading" role="status"><LoaderCircle className="spin" size={22} /> Loading workspace…</div>; }

export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div><div className="heading-action">{action}</div></div>;
}

export function Modal({ title, children, close, wide = false }: { title: string; children: ReactNode; close: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return <dialog ref={ref} className={`modal ${wide ? 'wide' : ''}`} onCancel={close} onClick={event => { if (event.target === event.currentTarget) close(); }}>
    <header><h2>{title}</h2><button className="icon-button" onClick={close} aria-label="Close dialog"><X size={20} /></button></header>{children}
  </dialog>;
}

export function Initials({ name }: { name: string }) {
  return <span className="avatar">{name.split(' ').map(part => part[0]).slice(0, 2).join('').toUpperCase()}</span>;
}

export function SectionTitle({ title, detail, action }: { title: string; detail?: string; action?: ReactNode }) {
  return <div className="section-title"><div><h2>{title}</h2>{detail && <p>{detail}</p>}</div>{action || <ArrowUpRight size={18} className="muted" />}</div>;
}
