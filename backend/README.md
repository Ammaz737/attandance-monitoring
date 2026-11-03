# Backend structure

`app/main.py` composes 13 domain routers, authentication middleware, startup and the
built frontend. `app/db/database.py` creates SQLite schema v1. `app/workers/manager.py`
owns camera capture, separate AI processing, encoding and retention. Domain endpoints
are implemented in their respective `router.py` files. Run from the repository root
using `scripts/start.ps1 backend`; do not start multiple API workers.

```text
app/
  api/v1/           Versioned router composition
  core/             Configuration, security, logging and clock helpers
  db/migrations/    Database sessions, schema and migrations
  modules/          Business domains (see below)
  vision/           Detection, recognition, tracking, liveness and quality adapters
  workers/          Camera processing, recording, export and retention jobs
  streaming/        Media gateway integration and stream authorization
  events/           Event schemas, publishing and subscriptions
tests/
  unit/             Domain logic checks
  integration/      Database, events and recording integration
  fixtures/         Synthetic/non-sensitive fixtures
model_assets/       Local weights and license manifests, ignored by Git
storage/            Local runtime artifacts, ignored by Git
```

Domain directories: auth, people, enrollment, locations, cameras, attendance,
sightings, recordings, reports, audit and settings.

As each domain is implemented, add `router.py`, `schemas.py`, `service.py`,
`repository.py` and `models.py` where needed. Routers validate requests; services
own rules; repositories own persistence. Do not create empty layers solely to
match a template. Add Python package initializers when executable code is added.

Workers must not run inside API request handlers. Each camera owns an independent
tracker and reconnect lifecycle. Recognition produces evidence; attendance service
decides whether evidence and crossing direction justify a session change.

Store embeddings encrypted in the database; enrollment captures go under protected
storage only when required by the enrollment/retention policy. Never log embeddings,
RTSP credentials, face images or authentication secrets.
