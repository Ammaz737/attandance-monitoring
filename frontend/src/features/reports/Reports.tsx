import { useState } from 'react';
import { Download, FileBarChart2 } from 'lucide-react';
import { useResource } from '../../hooks/useResource';
import { API, today } from '../../lib/api/client';
import type { Attendance } from '../../types';
import { ErrorMessage, PageHeading } from '../../components/ui/shared';
import { useUser } from '../../app/App';

export default function Reports() {
  const [day, setDay] = useState(today());
  const { data, error } = useResource<Attendance[]>(`/attendance?day=${day}`, []);
  const completed = data.filter(item => item.out_at);
  const minutes = completed.reduce((sum, item) => sum + (Date.parse(item.out_at!) - Date.parse(item.in_at)) / 60000, 0);
  return <><PageHeading eyebrow="TURN RECORDS INTO CLARITY" title="Reports" description="Daily attendance summaries built from recorded sessions." /><ErrorMessage message={error} /><section className="panel report-card"><span className="report-icon"><FileBarChart2 size={33} /></span><div><span className="small-kicker">ATTENDANCE REPORT</span><h2>A day in your workspace.</h2><p>Export person IDs, departments, entry and exit timestamps. CSV timestamps are UTC.</p></div><label>Report date<input type="date" value={day} onChange={e => e.target.value && setDay(e.target.value)} /></label>{useUser().role !== 'operator' && <a className="button primary" href={`${API}/reports/attendance.csv?day=${day}`}><Download size={17} />Download CSV</a>}</section><div className="stat-grid report-stats">{[['People with sessions', new Set(data.map(item => item.person_id)).size], ['Total sessions', data.length], ['Completed sessions', completed.length], ['Completed session hours', (minutes / 60).toFixed(1)]].map(([label, value]) => <div className="stat-card" key={label}><span className="muted small">{label}</span><strong>{value}</strong><p>Selected date · PKT</p></div>)}</div></>;
}
