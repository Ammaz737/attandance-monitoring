export interface Person {
  id: string; employee_id: string; name: string; contact: string; department: string;
  active: number; consent: number; template_count: number; open_session: string | null;
}
export interface Camera {
  id: string; name: string; location_id: string; location_name: string; building: string; floor: string;
  role: string; recording: number; enabled: number; status: string; fps: number;
  last_frame_at: string | null; last_analysis_at: string | null; detections: number; message: string; recording_error: string;
  line_x: number; entry_direction: string; retention_days: number;
  source_type: 'webcam' | 'network'; webcam_source: string | null;
}
export interface Location { id: string; name: string; building: string; floor: string }
export interface Sighting {
  id: string; person_id: string; name: string; employee_id: string; camera_id: string;
  camera_name: string; location_name: string; confidence: number; occurred_at: string;
}
export interface Attendance {
  id: string; person_id: string; name: string; employee_id: string; department: string;
  in_at: string; out_at: string | null;
}
export interface Recording {
  id: string; camera_id: string; camera_name: string; location_name: string;
  started_at: string; ended_at: string | null; status: string; bytes: number;
}
export interface User { id: string; username: string; role: string }
