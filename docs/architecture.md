# Architecture and contracts

Implementation note: this document describes the target scalable architecture.
The current local pilot uses SQLite WAL, per-camera capture/AI threads, SSE events
and authenticated MJPEG. A dedicated media gateway, PostgreSQL and Redis remain
deployment extensions. Current APIs are implemented in domain `router.py` files.
Live capture and analyzed-frame previews are separate, so AI latency does not
freeze live video or place old boxes on new frames. See `runbook.md` for limits.

## Data path

```text
Camera RTSP / development video
  -> Media gateway -> authorized WebRTC preview (HLS fallback)
  -> Python camera worker -> detector -> per-camera tracker
                                      -> quality/liveness/recognition
                                      -> sighting and crossing evidence
  -> Recording worker -> timestamped video segments

Evidence -> domain services -> PostgreSQL -> event publisher -> React
Recording metadata -> authorized playback/export API -> React
```

MediaMTX is the proposed gateway; `infra/mediamtx/` reserves its configuration.
Redis is the proposed queue/event transport; PostgreSQL is the source of truth.
No media gateway configuration is supplied yet.

## Identity and attendance rules

- Employee ID is stable; tracker IDs are scoped to camera and worker session.
- Face enrollment stores multiple quality-controlled templates and model version.
- Recognition thresholds must be calibrated on local footage, not guessed.
- An accepted face match and configured directional crossing produce an attendance
  candidate. The attendance service applies idempotency and session rules.
- Repeated detections never toggle IN/OUT. Allow multiple daily sessions.
- Missing visibility is not an exit. Conflicts and missing exits need review.
- Cross-camera identity requires new evidence. Appearance alone is not confirmation.
- Store last confirmed sighting and its timestamp. Stale location is not live location.
- Liveness is an independent adapter and must be evaluated before claiming spoof resistance.

## Persistence boundaries

| Entity | Purpose |
| --- | --- |
| users / roles | Authentication and access |
| persons | Stable registration details and active state |
| consent_records / face_templates | Enrollment evidence, encrypted templates, model version |
| locations | Building/floor/zone hierarchy and optional map position |
| cameras / camera_zones | Protected stream configuration, role, ROI and crossing lines |
| attendance_events / attendance_sessions | Immutable evidence and derived IN/OUT sessions |
| sightings | Person, camera, time interval, confidence and evidence status |
| recording_segments / sighting_recordings | Segment index and person-to-video references |
| review_items / audit_logs | Uncertainty, corrections and access history |

Use UTC timestamps in persistence and Asia/Karachi for the initial UI. Preserve
source timestamps and processing timestamps; synchronize camera/server clocks.
Link video to sightings by camera and capture time, not event arrival time.

## Planned API groups

All groups below are contracts to implement, not available endpoints.

`/api/v1/auth`, `/people`, `/enrollments`, `/locations`, `/cameras`,
`/attendance`, `/sightings`, `/recordings`, `/reports`, `/settings`, `/events`.

Camera operations include connection test, activation, health, zone configuration
and stream access. Recording operations include search, authorized playback and
export jobs. Events include `camera.health.changed`, `attendance.changed`,
`sighting.confirmed`, `review.created` and `recording.status.changed`.

Events carry event ID, schema version, capture/occurrence time and entity reference.
Use durable idempotency keys for attendance. On reconnect, fetch authoritative
state and resume events where possible; detect gaps rather than silently lose them.

## Models and runtime

- Benchmark RF-DETR Small and Nano for person detection.
- ByteTrack maintains tracks within each camera, not global employee identity.
- InsightFace can be evaluated for research prototypes; supplied weights require
  suitable licensing for commercial deployment. Record licenses for every model.
- Keep detector, embedder and liveness adapters replaceable and versioned.
- Hardware capacity and accuracy remain unverified until actual footage is tested.

## Recording and access

Write segments once under `storage/recordings/YYYY-MM-DD/CAMERA_ID/` using UTC
dates; derive person/day views through metadata in the selected display timezone.
Buffer pre-event video when event recording is enabled. Retention deletes media
and updates availability metadata. Expired media is explicitly unavailable.
Serve protected media through authorized access, never an unrestricted static folder.
Separate admin, operator and attendance-review permissions; audit corrections.
