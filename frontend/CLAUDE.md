# frontend/ — Next.js 15 reviewer app

Next.js 15 App Router app for TCE/RN reviewers to approve, edit, or reject LLM-extracted obrigações and recomendações. Talks only to the FastAPI backend.

## Stack

- Next.js 15 (App Router), React 19, TypeScript (strict).
- Styling: Tailwind CSS + shadcn/ui components (copied into `src/components/ui/`, not imported from a package).
- Data fetching: TanStack Query v5 + a single axios client with JWT interceptor.
- Forms: react-hook-form + zod. Zod schemas are the single source of truth for client-side validation.
- Span editor: `react-text-annotate-blend` or similar controlled component.

## Layout

```
frontend/
├── package.json             # pnpm
├── next.config.ts
├── tailwind.config.ts
├── src/
│   ├── app/                 # App Router routes
│   │   ├── (auth)/login/
│   │   ├── (app)/
│   │   │   ├── reviews/
│   │   │   │   ├── page.tsx           # list
│   │   │   │   └── [kind]/[id]/       # detail + review
│   │   │   └── layout.tsx             # auth-guarded layout
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/              # shadcn/ui primitives
│   │   └── review/          # span editor, review form, claim banner
│   ├── lib/
│   │   ├── api-client.ts    # axios instance + JWT interceptor
│   │   ├── auth.ts          # token storage, refresh logic
│   │   └── query-client.ts  # TanStack Query setup
│   ├── hooks/               # useReviews, useClaim, useApprove, useReject
│   └── schemas/             # zod schemas matching backend DTOs
└── tests/
    ├── unit/                # Vitest + React Testing Library
    └── e2e/                 # Playwright
```

## Rules for Claude Code in `frontend/`

### Architecture
- **App Router only.** No `pages/`. Server Components by default; mark `"use client"` only where needed (forms, TanStack Query hooks, span editor, anything using browser APIs).
- **Data fetching via TanStack Query hooks**, not bare `fetch` in components. Every server interaction goes through a hook under `src/hooks/`.
- **Single API client**: `src/lib/api-client.ts` holds the axios instance. Attaches JWT from storage, handles 401 → refresh → retry, redirects to login on refresh failure.
- **Auth tokens in HTTP-only cookies preferred** (set by backend); if localStorage is used, document the XSS trade-off in the PR and keep the refresh token out of JS-readable storage.
- **Zod schemas align one-to-one with backend Pydantic DTOs.** Field names and types must match — mismatches cause silent data loss on approve. Add a comment on each schema pointing to the backend DTO it mirrors.

### Review flow UX
- **Claim on detail page mount, release on unmount.** Use `useEffect` cleanup + `navigator.sendBeacon` for the release on tab close. The backend has a 15-minute TTL, so a missed release is recoverable.
- **Show the claim state clearly**: who has it, how long until expiry. If the current user's claim is lost (another reviewer claimed after expiry), block the form and show a "re-claim or return to list" banner.
- **Span editor behavior**:
  - Full `texto_acordao` rendered in a scrollable container with the matched span highlighted (via `span_match_status` from the API).
  - If `span_match_status === "not_found"`, show a clear empty state and let the reviewer highlight the correct span, or approve with a blank `descricao`.
  - The approved span is sent as a plain string (the substring the reviewer highlighted). **No character offsets leave the frontend.**
- **Form layout**: span editor on the left (or top on mobile), field form on the right. Every field from the backend DTO is present; no hidden fields that silently forward `original_payload`.
- **Approve/reject buttons** are disabled while the claim is not held by the current user or while a mutation is in flight. Toast on success, inline error on failure.

### Components
- **shadcn/ui components live in `src/components/ui/`** as copies (per shadcn convention). Don't add a second component library (Chakra, Mantine, MUI).
- **Composite components go in `src/components/review/`** — span editor, review form, claim banner. Keep them dumb where possible; business logic lives in hooks.

### Localization
- Reviewer-facing strings in **Portuguese**. Code identifiers in **English**.
- Error messages from the backend arrive with a code; the frontend maps the code to a Portuguese message. Never render raw English `detail` strings to reviewers.

### Testing
- **Unit**: Vitest + React Testing Library for hooks and composite components. Mock the API with MSW.
- **E2E**: one Playwright happy-path test — login → list pending → open detail → claim → edit span → approve → item gone from list. Hits a running backend.
- Run `pnpm test` for units, `pnpm test:e2e` for E2E.

### Formatting
- `pnpm lint` (ESLint, Next.js config) + `pnpm format` (Prettier) before committing.

### What NOT to do
- **Don't reintroduce Streamlit** or any second web framework.
- **Don't store the refresh token in JS-readable storage.** HTTP-only cookie or nothing.
- **Don't bypass TanStack Query** with ad-hoc `useEffect` + `fetch` — the 401-refresh-retry flow lives in one place.
- **Don't add character offsets to the API contract.** Spans are strings end-to-end.