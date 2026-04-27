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
│   │   │   ├── etl/
│   │   │   │   └── page.tsx           # ETL em dois passos (NER → Obrigação/Recomendação)
│   │   │   ├── reviews/
│   │   │   │   ├── page.tsx           # lista de pendentes
│   │   │   │   └── [kind]/[id]/       # detalhe + revisão
│   │   │   └── layout.tsx             # auth-guarded layout
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/              # shadcn/ui primitives
│   │   ├── etl/             # EtlStepper, EtlDateRangePicker, EtlProgressCard
│   │   └── review/          # span editor, review form, claim banner
│   ├── lib/
│   │   ├── api-client.ts    # axios instance + JWT interceptor
│   │   ├── auth.ts          # token storage, refresh logic
│   │   └── query-client.ts  # TanStack Query setup
│   ├── hooks/
│   │   ├── useEtlNerDecisao.ts          # POST /etl/ner-decisao
│   │   ├── useEtlObrigacaoRecomendacao.ts # POST /etl/obrigacao-recomendacao
│   │   └── useReviews.ts, useClaim.ts, useApprove.ts, useReject.ts
│   └── schemas/             # zod schemas matching backend DTOs
└── tests/
    ├── unit/                # Vitest + React Testing Library
    └── e2e/                 # Playwright
```

## ETL — Página de extração em dois passos

A rota `(app)/etl/page.tsx` permite que usuários autorizados disparem o pipeline de extração LLM
diretamente pela interface, sem precisar executar o notebook manualmente.

### Fluxo lógico (espelha `notebooks/etl.ipynb`)

```
Passo 1 — Extração NER de Decisões
  └─ backend: POST /etl/ner-decisao
       → run_ner_pipeline_for_dataframe(df, extractor, ...)
       → persiste NERDecisao no banco (BdDIP)

Passo 2 — Extração de Obrigações e Recomendações
  └─ backend: POST /etl/obrigacao-recomendacao
       → run_obrigacao_pipeline(extractor_obrigacao, extractor_responsible)
       → run_recomendacao_pipeline(extractor_recomendacao, extractor_responsible)
       → persiste Obrigacao e Recomendacao a partir dos NERDecisao ainda não processados
       → estes itens ficam disponíveis na fila de revisão
```

O Passo 2 só pode ser disparado **após** o Passo 1 ter sido concluído com sucesso na sessão
atual **ou** quando já existem `NERDecisao` pendentes de processamento no banco (o backend
informa essa contagem no GET `/etl/status`).

### UX da página ETL

- **Seleção de intervalo de datas** (start_date / end_date): usada pelo backend para
  `get_decisions_by_dates(start_date, end_date)` no Passo 1. Obrigatório antes de iniciar.
- **Stepper visual** com dois passos claramente rotulados em português:
  - *Passo 1 — Extração NER de Decisões*
  - *Passo 2 — Extração de Obrigações e Recomendações*
- Cada passo exibe:
  - Estado: `idle` | `em andamento` | `concluído` | `erro`
  - Contadores retornados pelo backend: decisões processadas, obrigações geradas, recomendações
    geradas, erros.
  - Botão de ação desabilitado enquanto o passo anterior não terminar ou enquanto o mesmo passo
    estiver em andamento.
- **Polling de progresso**: após disparar um passo, o frontend faz polling em
  `GET /etl/jobs/{job_id}/status` a cada 3 s até o job terminar (`status: "done" | "error"`).
  Usar `useQuery` com `refetchInterval` condicional — **não** usar `useEffect` + `setInterval`.
- **Tratamento de erro**: exibir a mensagem mapeada em português; nunca exibir `detail` cru do
  backend. Botão "Tentar novamente" reinicia apenas o passo com falha.
- Acesso restrito: renderizar a página apenas para usuários com role `admin` ou `etl_operator`
  (checar claim do JWT); redirecionar os demais para `/reviews`.

### Hooks ETL

```typescript
// src/hooks/useEtlNerDecisao.ts
// Mirrors: run_ner_pipeline_for_dataframe(df, extractor, model_name, prompt_version, run_id)
// POST /etl/ner-decisao  body: { start_date, end_date, model_name?, prompt_version? }
// Retorna: { job_id, decisoes_processadas, erros }
useMutation → useEtlNerDecisao()

// src/hooks/useEtlObrigacaoRecomendacao.ts
// Mirrors: run_obrigacao_pipeline() + run_recomendacao_pipeline()
// POST /etl/obrigacao-recomendacao  body: { run_id? }
// Retorna: { job_id, obrigacoes_geradas, recomendacoes_geradas, erros }
useMutation → useEtlObrigacaoRecomendacao()
```

### Componentes ETL

Colocar em `src/components/etl/` — mantê-los burros; lógica fica nos hooks.

- `EtlStepper` — estado visual dos dois passos; recebe props de estado externo, não faz fetch.
- `EtlDateRangePicker` — `react-hook-form` + `zod` para start/end date; emite `onSubmit`.
- `EtlProgressCard` — mostra contadores e barra de progresso indeterminada enquanto polling ativo.

### Zod schemas ETL

```typescript
// src/schemas/etl.ts
// Mirrors backend DTOs de /etl/*
export const EtlNerDecisaoRequestSchema = z.object({
  start_date: z.string().date(),   // "YYYY-MM-DD"
  end_date: z.string().date(),
  model_name: z.string().optional(),
  prompt_version: z.string().optional(),
});
// Adicionar comentário: "mirrors backend EtlNerDecisaoRequest (FastAPI DTO)"

export const EtlJobStatusSchema = z.object({
  job_id: z.string().uuid(),
  status: z.enum(["pending", "running", "done", "error"]),
  decisoes_processadas: z.number().int().optional(),
  obrigacoes_geradas: z.number().int().optional(),
  recomendacoes_geradas: z.number().int().optional(),
  erros: z.number().int().optional(),
  detail: z.string().optional(),
});
```

---

## Revisão — Definição de itens pendentes

**Pendente** significa: `Obrigacao` **sem** registro correspondente em `ObrigacaoStaging`, ou
`Recomendacao` **sem** registro correspondente em `RecomendacaoStaging`.

O backend implementa isso com LEFT JOIN + filtro `WHERE staging.id IS NULL` nas queries de
listagem. O frontend **não** precisa inferir pendência — confiar no campo `status: "pending"`
retornado pela API.

```
GET /reviews?status=pending&kind=obrigacao   → Obrigacao sem ObrigacaoStaging
GET /reviews?status=pending&kind=recomendacao → Recomendacao sem RecomendacaoStaging
GET /reviews?status=pending                  → ambos combinados, ordenados por data_sessao desc
```

A página de lista (`reviews/page.tsx`) deve:
- Usar o parâmetro `status=pending` em todas as chamadas de listagem — nunca filtrar no cliente.
- Exibir abas ou filtro `kind` (Obrigações / Recomendações / Todos) que apenas altera o query
  param, não re-implementa a lógica de "pendente".
- Após aprovação ou rejeição bem-sucedida, o item desaparece da lista porque o backend passa a
  retornar um `ObrigacaoStaging` / `RecomendacaoStaging` vinculado, saindo do filtro `IS NULL`.

---

## Review flow UX

- **Claim on detail page mount, release on unmount.** Use `useEffect` cleanup +
  `navigator.sendBeacon` for the release on tab close. The backend has a 15-minute TTL, so a
  missed release is recoverable.
- **Show the claim state clearly**: who has it, how long until expiry. If the current user's
  claim is lost (another reviewer claimed after expiry), block the form and show a "re-claim or
  return to list" banner.
- **Span editor behavior**:
  - Full `texto_acordao` rendered in a scrollable container with the matched span highlighted
    (via `span_match_status` from the API).
  - If `span_match_status === "not_found"`, show a clear empty state and let the reviewer
    highlight the correct span, or approve with a blank `descricao`.
  - The approved span is sent as a plain string (the substring the reviewer highlighted).
    **No character offsets leave the frontend.**
- **Form layout**: span editor on the left (or top on mobile), field form on the right. Every
  field from the backend DTO is present; no hidden fields that silently forward `original_payload`.
- **Approve/reject buttons** are disabled while the claim is not held by the current user or
  while a mutation is in flight. Toast on success, inline error on failure.

---

## Architecture rules

### App Router
- **App Router only.** No `pages/`. Server Components by default; mark `"use client"` only
  where needed (forms, TanStack Query hooks, span editor, ETL stepper, anything using browser APIs).
- **Data fetching via TanStack Query hooks**, not bare `fetch` in components. Every server
  interaction goes through a hook under `src/hooks/`.
- **Single API client**: `src/lib/api-client.ts` holds the axios instance. Attaches JWT from
  storage, handles 401 → refresh → retry, redirects to login on refresh failure.
- **Auth tokens in HTTP-only cookies preferred** (set by backend); if localStorage is used,
  document the XSS trade-off in the PR and keep the refresh token out of JS-readable storage.
- **Zod schemas align one-to-one with backend Pydantic DTOs.** Field names and types must match —
  mismatches cause silent data loss on approve. Add a comment on each schema pointing to the
  backend DTO it mirrors.

### Components
- **shadcn/ui components live in `src/components/ui/`** as copies (per shadcn convention).
  Don't add a second component library (Chakra, Mantine, MUI).
- **Composite review components go in `src/components/review/`** — span editor, review form,
  claim banner. Keep them dumb where possible; business logic lives in hooks.
- **ETL components go in `src/components/etl/`** — stepper, date range picker, progress card.
  Mesma regra: lógica nos hooks, componentes burros.

### Localization
- Reviewer-facing strings in **Portuguese**. Code identifiers in **English**.
- Error messages from the backend arrive with a code; the frontend maps the code to a Portuguese
  message. Never render raw English `detail` strings to reviewers.
- Isso inclui mensagens de erro do ETL — mapear códigos como `etl_ner_failed`,
  `etl_obrigacao_failed`, `job_not_found` para textos em português.

---

## Testing

- **Unit**: Vitest + React Testing Library for hooks and composite components. Mock the API
  with MSW. Inclui testes para `useEtlNerDecisao` e `useEtlObrigacaoRecomendacao` (estado de
  polling, erro, conclusão).
- **E2E**: one Playwright happy-path test — login → list pending → open detail → claim → edit
  span → approve → item gone from list. Hits a running backend.
- **ETL E2E** (opcional, marcado `@slow`): login como `etl_operator` → ETL page → selecionar
  datas → Passo 1 → aguardar conclusão → Passo 2 → verificar contador de obrigações/recomendações
  geradas > 0 → navegar para `/reviews` e confirmar itens na lista.
- Run `pnpm test` for units, `pnpm test:e2e` for E2E.

---

## Formatting

`pnpm lint` (ESLint, Next.js config) + `pnpm format` (Prettier) before committing.

---

## What NOT to do

- **Don't reintroduce Streamlit** or any second web framework.
- **Don't store the refresh token in JS-readable storage.** HTTP-only cookie or nothing.
- **Don't bypass TanStack Query** with ad-hoc `useEffect` + `fetch` — the 401-refresh-retry
  flow lives in one place. Isso vale também para o polling do ETL.
- **Don't add character offsets to the API contract.** Spans are strings end-to-end.
- **Don't filter "pending" on the client.** A definição de pendente (sem staging) é responsabilidade
  do backend; o frontend apenas passa `status=pending` como query param.
- **Don't allow Passo 2 to run without Passo 1 completing first** (na mesma sessão ou via
  contagem de NERDecisao pendentes retornada por `GET /etl/status`).