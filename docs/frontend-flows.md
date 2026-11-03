# Frontend routes and journeys

The core journeys are implemented. The current app uses dialogs for person creation,
profile/enrollment and camera configuration instead of separate detail routes below.
`/people?person=<id>` opens a profile; enrollment opens from that profile.
Live event transport is SSE; live media and exact analyzed frames are separate MJPEG views.

| Route | Feature | Required experience |
| --- | --- | --- |
| /login | auth | Sign in, expired session and access denied |
| / | dashboard | Present count, sessions, camera health, recent events |
| /people | people | Search, filters, add and deactivate |
| /people/new | people | Details and consent followed by enrollment |
| /people/:personId | people | Attendance, enrollment, last seen and recordings |
| /people/:personId/enrollment | enrollment | Guided quality-checked capture and review |
| /locations | locations | Building/floor/zone configuration |
| /cameras | cameras | Health list and location filters |
| /cameras/new | cameras | Registration wizard |
| /cameras/:cameraId | cameras | Preview, role, zones, recording and diagnostics |
| /attendance | attendance | Date/person filters, IN/OUT sessions and review |
| /monitoring | monitoring | Camera grid, focused preview and event panel |
| /tracking | tracking | Person search, last confirmed location and timeline |
| /recordings | recordings | Search, timestamp playback and export |
| /reports | reports | Attendance and sighting summaries |
| /settings | settings | Access, shifts, model configuration and retention |

## Camera registration

Location -> source details -> backend connection test -> actual preview -> role
-> ROI and directional crossing line -> recording/retention -> activate -> health.
Allow retry without losing input. Validate configuration before activation.

## Person enrollment

Details -> consent -> camera permission -> guided captures -> quality feedback
-> duplicate check -> encrypted templates -> active profile.
Handle denied camera permission, no face, multiple faces, blur, low light,
duplicate candidate and failed enrollment without claiming success.

## Attendance and tracking

Confirmed entry -> open session -> dashboard update -> person profile -> sightings
timeline -> selected camera/time -> recording playback -> confirmed exit closes session.
Corrections require authorization and a reason. Unknown/uncertain detections do not
create named attendance. Show uncertain observations in the review workflow.

## Live monitoring

Location filter -> 1/4/9 camera grid -> focus camera -> synchronized overlays
and recent events -> select person -> tracking/profile.
Video frames and detection metadata need compatible timestamps. Hide stale boxes.
Show connecting, live, degraded, reconnecting, offline and frozen-frame states.
WebRTC failure may offer HLS with an explicit increased-delay indicator.

## Shared UI rules

- Every data view has loading, empty, error and permission states.
- Last seen always includes time; unknown location remains unknown.
- Camera reconnect and event reconnect are separate visible states.
- Use keyboard-accessible controls and labeled forms; status cannot rely on color.
- Dates and durations use consistent timezone labeling.
- Expired recordings keep their event context and explain missing playback.
- Persisted configuration changes show server confirmation or actionable failure.
