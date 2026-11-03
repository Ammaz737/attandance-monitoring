# Frontend structure

Implemented with React, TypeScript and Vite. `src/main.tsx` starts the application,
`src/app/App.tsx` composes authentication, navigation and routes. Product pages live
inside feature directories. Run `npm run dev` or `npm run build` here.

```text
src/
  app/providers/       Authentication, query client and shared context
  app/router/          Route definitions and access guards
  layouts/             App shell and authentication layout
  components/ui/       Shared accessible controls
  components/video/    Stream player, detection overlay and playback controls
  components/feedback/ Loading, empty, error and connection states
  features/            Product screens and domain-specific interactions
  lib/api/             HTTP client and error normalization
  lib/realtime/        Event connection, resync and subscriptions
  hooks/               Cross-feature hooks
  types/               Shared transport types
  styles/              Tokens and global styles
tests/e2e/             Critical end-to-end journeys
```

Each implemented feature can contain `pages/`, `components/`, `api.ts`, `types.ts`
and `hooks/` as needed. Keep feature-only components inside that feature.

The UI shows API/worker state; it never manufactures attendance or sightings.
Video uses authenticated MJPEG and events use SSE in this local version. Live
capture and analyzed-frame views are separate to preserve timestamp alignment.
Browser configuration must never contain RTSP passwords or model service keys.
