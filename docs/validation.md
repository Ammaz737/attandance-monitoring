# Verification record

Verified locally on Windows with Python 3.12 and Node 24.

Enrollment camera fix: the complete suite now passes 22 tests, including native
preview cleanup, reuse of a running camera's unannotated frames, device/role checks
and owner-scoped preview expiry. The production frontend build passed. In the live
browser, the registered webcam produced preview frames and enabled Capture sample
through Workspace camera; the test preview was then stopped without saving samples
or changing enrollment. See `screenshots/enrollment-fixed.png` for the resulting UI.

Webcam discovery update: 5 targeted tests passed for named discovery, empty/error
states, administrator access, enumeration without video capture and registration
round-trip. A connected webcam was enumerated on both the main thread and an
async worker thread. Frontend production build passed after the update.

## Automated

- 13 backend tests passed. They cover setup/authentication, role checks, origin
  protection, registration validation, encrypted camera sources, attendance
  conflicts/re-entry/idempotency, historical corrections, model-unavailable
  enrollment, CSV export, timezone boundaries and review-only crossings.
- Synthetic video encoded to H.264 MP4 and played through authenticated file and
  byte-range responses.
- Slow synthetic AI inference did not block the independent capture loop.
- React TypeScript checking and Vite production build passed.
- Python dependency check passed; npm installation reported no vulnerabilities.
- Official RF-DETR Small and OpenCV YuNet/SFace weights initialized locally on CPU.
  A blank-frame inference through RF-DETR, ByteTrack and the face adapter returned
  no detections. Weight sources/checksums/licenses are preserved in local manifests.

## Browser checks

Used an isolated temporary database, not the real workspace database:

- Sign-in and dashboard.
- Location creation and persisted location card.
- Person registration, consent, list and enrollment status.
- Manual check-in and visible open attendance session.
- Three-step camera registration and saved camera configuration.
- Mobile navigation, hidden-menu accessibility and default viewport restoration.

`screenshots/dashboard-qa.png` is a QA preview with synthetic test records.
The real workspace starts without a default password, people or cameras.

## Not yet validated

No real camera URL, hardware capacity target or consented employee samples were
provided. Actual stream reliability, face false-match/miss rates, crossing accuracy,
spoof resistance and multi-camera identity quality need an on-site pilot. Liveness
is not implemented and automatic attendance remains off by default. Production
WebRTC/HLS, durable queueing and PostgreSQL remain deployment work.
