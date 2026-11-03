# Running Presence locally

## Setup and start

Use Python 3.12 and Node.js 22.12+ (Node 24 is used here). From the repository root:

```powershell
./scripts/setup.ps1 -Python python
./scripts/start.ps1 backend
```

In another terminal: `./scripts/start.ps1 frontend`.
Open http://127.0.0.1:5173 and create your administrator. No default production
password or test data is installed. API docs: http://127.0.0.1:8000/docs.
If Python is not on PATH, pass its full executable path to `-Python`.

For a single local process, build with `npm.cmd --prefix frontend run build`, restart
the backend and open http://127.0.0.1:8000. It serves the built SPA and media.
If setting `FRONTEND_ORIGIN`, include the origin you use.

## First workspace journey

1. Create the initial administrator from this computer and sign in.
2. Add a building/floor/zone under Locations.
3. Register a camera: Webcam automatically lists connected built-in/USB cameras
   by name and selects the first available device. Use Rescan after connecting a
   camera, or choose IP / network camera for an RTSP/HTTP source. Discovery lists
   server-connected devices without opening video; Preview webcam tests a frame.
4. Test connection, configure purpose and vertical crossing line, save and activate.
5. Open Live Monitoring. Health reflects received frames, not just a saved URL.
   Use Detection view for exact analyzed frames and their capture timestamps;
   live capture continues independently when inference is slower.
6. Register a person with consent; enroll 3–8 clear samples from their profile.
   Enrollment defaults to Workspace camera, which captures through Python without
   browser camera permissions. A running registered feed is reused. Browser camera
   remains an alternative with specific permission/device error messages. Stop or
   close the preview to release it; abandoned previews expire automatically.
7. Configure models following `model-setup.md`; restart the backend.
8. Confirm sightings in Tracking. Crossings create review items until automatic
   attendance is explicitly enabled in backend configuration.
9. Manual attendance records IN/OUT now. Correct a session fixes historical times
   with an audit reason. Re-entry creates another daily session.
10. Enable recording for 60-second segments. Project-local FFmpeg encodes browser
    MP4 files in the background; playback becomes available after encoding.

## Storage and backup

`backend/storage/attendance.sqlite3` stores records. Camera credentials and face
templates are encrypted using `backend/storage/encryption.key`. Back up both
together while the API is stopped. Losing the key makes encrypted records unusable.
Protect this directory using OS permissions. Runtime data is ignored by Git.
Raw enrollment images are not persisted.

Videos are stored once by camera/date. Person/date views link to these files
through sightings. Retention deletes files and marks metadata expired. Interrupted
recording/encoding jobs are marked unavailable at startup.

## Verification

Run `./scripts/check.ps1`. Tests use an isolated temporary database.
`backend/tests/manual_preview.py` is an optional disposable UI QA server; never run
it alongside the real backend on port 8000. Its test account is not a production account.

## Deployment limits

This local pilot uses one API process, SQLite and per-camera threads. Do not run
multiple API workers against the same camera manager. SSE events are transient;
clients refetch state on reconnect and periodically. MJPEG is bandwidth-intensive.
Production scale needs measured hardware capacity, a media gateway, WebRTC/HLS and
durable worker queues.

Liveness, global appearance-based re-identification, map calibration, shifts,
payroll rules, automated backups and production identity recovery are not implemented.
Camera-to-camera history requires independent face confirmation; blind spots stay
unknown. Real camera accuracy must be measured using a representative on-site pilot.

Keep the default loopback binding. Network deployment needs HTTPS, secure cookies,
explicit allowed origins and secure initial-admin provisioning. Those deployment
changes are not automatically applied by setup.
