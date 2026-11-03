# Delivery checklist

The local pilot is implemented: authentication/roles, people/enrollment, cameras,
locations, independent live capture and analyzed-frame preview, face sightings,
attendance/review/corrections, recording/playback/retention, CSV export and audit.
RF-DETR Small, ByteTrack and OpenCV SFace/YuNet initialize locally. Real-camera and
on-site identity accuracy validation is pending. The phases below remain the target
for a larger production deployment; PostgreSQL/Redis/media gateway are not implemented.

1. Foundation: initialize React/TypeScript/Vite and FastAPI, configuration validation,
   PostgreSQL migrations, authentication, roles and development health checks.
2. Cameras: location CRUD, protected RTSP configuration, connection test, media
   gateway integration, actual preview, reconnect and timestamped recording.
3. Enrollment: consent, quality checks, template storage, duplicate review and
   model adapters with documented licenses.
4. Attendance: identity evidence, directional crossing, idempotent events,
   multiple sessions, missing-exit review and audited corrections.
5. Monitoring: person detection, per-camera tracking, timestamp-aligned overlays,
   live health/events and reconnect resynchronization.
6. Tracking/playback: confirmed cross-camera sightings, last-seen semantics,
   timeline, recording references and authorized seek/export.
7. Operations: reports, retention, access auditing, backups and worker recovery.
8. Pilot: one entrance and one indoor camera using representative footage.

## Pilot acceptance scenarios

- Registered entry creates exactly one session despite repeated frames.
- Exit closes the correct session; re-entry starts a new session.
- Unknown or ambiguous identity does not mark a named employee present.
- Camera loss does not create OUT; recovery does not duplicate events.
- Two cameras never share identity solely because tracker numbers match.
- Timeline plays the correct camera segment at the correct capture time.
- Frozen video/stale sighting cannot appear as current live location.
- Unauthorized users cannot fetch protected media or biometric templates.
- Retention expiry updates playback availability and preserves event context.

Measure false matches, missed matches, attendance errors, processing/preview delay,
camera recovery, recording gaps and storage usage. Set acceptance thresholds after
hardware, camera count and representative footage are available.
