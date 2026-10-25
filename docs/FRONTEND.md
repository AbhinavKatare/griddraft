# UK Wind Forecast Monitor — Frontend Architecture & Design Defense

This document details the architectural, design, and motion decisions implemented for the Day-Ahead Wind Forecast Decision Support tool, providing clear technical justification suitable for engineering leadership.

---

## 1. Design System & Control-Room Philosophy

### 1.1 "Quiet Control Room" Concept
Energy trading desks and control room operators handle high-frequency, safety-critical decisions under strict time constraints (e.g. British day-ahead auction closing at 11:00 UTC). 

- **Calm and Data-Dense:** The UI rejects consumer SaaS aesthetics (no vibrant purple gradients, no heavy glassmorphism, no emoji icons). Instead, it adopts an editorial, dense layout prioritizing information hierarchy, low visual fatigue, and immediate situational awareness.
- **Light & Dark Themes:** Implemented purely via CSS Custom Properties in [`src/design/tokens.css`](file:///d:/UK%20weather%20forecast/frontend/src/design/tokens.css). Honors the operating system's `prefers-color-scheme` by default, with manual toggle persistence in `localStorage`.
- **4/8px Spacing Grid:** Spacing tokens (`--space-1` = 4px, `--space-2` = 8px, `--space-4` = 16px, `--space-6` = 24px) establish vertical cadence and visual rhythm across high-density tables and metric cards.

### 1.2 Domain Semantic Color Tokens (WCAG AA Compliant)
Color conveys operational meaning and is always paired with distinct line styles, glyphs, and labels so that information is accessible under monochrome or color-blind viewing:

| Role | Semantic Meaning | Light Token | Dark Token | Line Style / Fill | WCAG AA Ratio |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Actual Generation** | Metered FUELHH outturn | `#0f766e` | `#14b8a6` | Solid 2px stroke | $> 4.8:1$ |
| **Decision Forecast** | Committed D-1 WINDFOR | `#b45309` | `#f59e0b` | Solid 2.5px stroke | $> 4.6:1$ |
| **Latest Revision (Leaky)**| Post-cutoff revision | `#64748b` | `#94a3b8` | Dashed 1.5px stroke | $> 4.5:1$ |
| **Safe Wind Band** | $(1-\alpha)$ derated volume | `#047857` | `#10b981` | Soft fill (12% opacity) | $> 4.7:1$ |
| **Shortfall / Procurement**| Required thermal reserve | `#be123c` | `#f43f5e` | Solid coral bar | $> 4.9:1$ |

### 1.3 Typography & Tabular Numerals
- **UI Typography:** Instrument Sans / IBM Plex Sans for legibility at small sizes (12px, 14px).
- **Data & Numbers:** JetBrains Mono for all timestamps, power quantities (MW), energy (MWh), and percentages.
- **Tabular Figures:** `font-variant-numeric: tabular-nums` and `font-feature-settings: 'tnum' 1` are enforced globally across table cells, metric values, and crosshairs to prevent layout jitter during data updates.

---

## 2. Motion System & Ergonomics

All motion parameters are defined in a single source of truth: [`src/design/motion.ts`](file:///d:/UK%20weather%20forecast/frontend/src/design/motion.ts).

### 2.1 Motion Tokens & Constraints
- **Micro Interactions:** $120\text{ ms}$ (`ease-in-out`) for toggles, tooltips, and badges.
- **UI Transitions:** $220\text{ ms}$ (`ease-out`) for drawers and modal backdrops.
- **View Transitions:** $350\text{ ms}$ spring (`stiffness: 380`, `damping: 32`, `mass: 0.9`).
- **Animate Only Transform & Opacity:** Ensures animations execute on the compositor thread without triggering layout recalcs or paint thrashing.
- **Bundle Optimization:** Powered by `LazyMotion` and `domAnimation` from `motion/react`, reducing Framer Motion's footprint by $> 70\%$ compared to the full feature set.

### 2.2 Key Motion Patterns
1. **Shared Layout Segments:** The segmented control uses Framer Motion's `layoutId="pill-..."` to smoothly slide a background indicator between options without layout shift.
2. **Direction-Aware View Transitions:** Navigating `Decision -> Accuracy` slides content left by $16\text{px}$; navigating in reverse slides right by $16\text{px}$.
3. **Delivery Day Stepper:** Prev/Next day buttons and keyboard arrow keys slide the timeseries while retaining previous data via TanStack Query's `keepPreviousData` until new points arrive.
4. **Number Count-Up:** `useAnimatedNumber` smoothly counts up metric figures upon load or filter changes using a cubic ease-out.
5. **Prefers-Reduced-Motion:** Swaps all slide transforms for instant or plain opacity fades, disabling number interpolation for motion-sensitive users.

---

## 3. Technology Stack & Charting Rationale

### 3.1 Recharts vs. Plotly for High-Density Timeseries
We evaluated **Recharts** vs. **Plotly.js**:

| Criterion | Recharts | Plotly.js | Decision Rationale |
| :--- | :---: | :---: | :--- |
| **Bundle Size** | **$419\text{ kB}$** ($118\text{ kB}$ gzip) | $> 2,800\text{ kB}$ ($850\text{ kB}$ gzip) | Plotly adds prohibitive payload overhead for serverless deployment. |
| **React Integration** | Native JSX component tree | Canvas/WebGL DOM wrapper | Recharts integrates cleanly with React 19 and CSS variables. |
| **Performance Strategy** | Downsampling + disabled animation | WebGL rendering | With server downsampling (`?resolution=1h|3h`) and disabling animation above 1,500 points, Recharts renders at 60fps. |

---

## 4. Folder Structure & Architecture

```
frontend/src/
├── api/
│   ├── client.ts             # Typed fetch wrapper with timeout, signal, and RFC 7807 parsing
│   ├── queries.ts            # TanStack Query hooks (staleTime, keepPreviousData, smart retry)
│   └── schema.d.ts           # Generated TypeScript types from FastAPI OpenAPI schema
├── components/
│   ├── ui/
│   │   ├── Drawer.tsx        # Slide-over drawer with focus trap & ESC handling
│   │   ├── ErrorBanner.tsx   # RFC 7807 problem detail alert banner
│   │   ├── LoadingSkeleton.tsx# Shimmer loading placeholders
│   │   ├── MetricCard.tsx    # Tabular KPI card with count-up animation and tooltip
│   │   ├── SegmentedControl.tsx# Sliding segmented control with shared layoutId pill
│   │   └── ToastContainer.tsx# Top-right animated notifications
│   ├── ControlBar.tsx        # Global filter bar (date, cutoff, mode, safe wind, downsampling)
│   └── Header.tsx            # App header with Elexon BMRS status pill and theme switch
├── design/
│   ├── motion.ts             # Central motion tokens, springs, and variants
│   └── tokens.css            # CSS custom properties (light/dark palette, typography, radii)
├── features/
│   ├── accuracy/
│   │   ├── AccuracyView.tsx  # Accuracy & Verification parent view
│   │   ├── BiasAlertBanner.tsx# Systematic bias advisory banner
│   │   ├── DailyBiasStrip.tsx# Interactive 31-day bias bar strip
│   │   ├── ErrorByHorizonChart.tsx# Lead-time horizon chart with auction window band
│   │   ├── ErrorByHourChart.tsx# Diurnal 0-23 clock hour error breakdown
│   │   ├── ErrorHistogram.tsx# 500 MW binned error distribution histogram
│   │   └── KPICards.tsx      # MAE, RMSE, Bias, and P90 shortfall cards
│   ├── decision/
│   │   ├── DayDataTable.tsx  # Sortable half-hourly ledger with CSV export
│   │   ├── DecisionView.tsx  # Decision parent view with period slide-over drawer
│   │   ├── HeroChart.tsx     # Actual vs Decision vs Safe Wind vs Leaky Line chart
│   │   ├── ProcurementBars.tsx# Required thermal backup procurement bar chart
│   │   └── SummaryStrip.tsx  # Integrated MWh volumes and peak procurement
│   └── methodology/
│       └── MethodologyDrawer.tsx# Quantitative explanation of cutoff rules and safe wind
├── hooks/
│   ├── useAnimatedNumber.ts  # Smooth number count-up hook
│   ├── useTheme.ts           # Light/dark theme hook with system listener
│   └── useUrlState.ts        # URL query parameter state synchronization
├── lib/
│   └── format.ts             # Formatting utilities (MW, MWh, %, UTC dates)
├── test/
│   ├── mocks/
│   │   ├── handlers.ts       # MSW mock handlers
│   │   └── server.ts         # MSW node server
│   ├── decision-view.test.tsx# Integration tests for Decision View
│   ├── format.test.ts        # Unit tests for formatters
│   ├── setup.ts              # JSDOM & matchMedia setup
│   └── url-state.test.tsx    # URL state synchronization tests
├── types.ts                  # Domain and UI state type exports
├── App.tsx                   # Main layout shell with direction-aware AnimatePresence
├── main.tsx                  # React DOM root with QueryClient and BrowserRouter
└── index.css                 # Global control-room reset and font configuration
```

---

## 5. Typed API Layer & State Architecture

### 5.1 OpenAPI Code Generation
Types are directly generated from the backend FastAPI OpenAPI JSON via `openapi-typescript`:
```bash
npx openapi-typescript ../backend/openapi.json -o src/api/schema.d.ts
```
This guarantees zero divergence between backend Pydantic models (`SafeWindSummary`, `MonthlyKPIs`, `ProblemDetail`) and frontend interfaces.

### 5.2 Error Normalisation (RFC 7807)
[`src/api/client.ts`](file:///d:/UK%20weather%20forecast/frontend/src/api/client.ts) detects `application/problem+json` headers on non-2xx responses and constructs an `ApiClientError` containing:
- `title`: Short title (e.g. "Validation Error")
- `status`: HTTP status code (e.g. 400, 422)
- `detail`: Human-readable error description
- `invalid_params`: Field-level validation constraints

### 5.3 URL State Synchronization
All operational parameters (`view`, `date`, `cutoff`, `mode`, `leaky`, `safe_mode`, `q`, `res`) are synchronized with the browser URL via [`src/hooks/useUrlState.ts`](file:///d:/UK%20weather%20forecast/frontend/src/hooks/useUrlState.ts):
- Every trading analysis screen is instantly shareable via URL link.
- History back/forward buttons work predictably.
- Arrow keys (`ArrowLeft`, `ArrowRight`) step through delivery days.

---

## 6. Verification & Build Metrics

### 6.1 Build Payload (Measured via Vite Production Bundle)
```
dist/index.html                             1.27 kB │ gzip:   0.57 kB
dist/assets/index-D8Yp06LT.css              4.58 kB │ gzip:   1.45 kB
dist/assets/rolldown-runtime-XKyaHtl9.js    0.72 kB │ gzip:   0.42 kB
dist/assets/query-D0YkBlv_.js              22.80 kB │ gzip:   7.59 kB
dist/assets/motion-CA4lthi6.js            139.17 kB │ gzip:  46.04 kB
dist/assets/index-BlbAPZa7.js             337.43 kB │ gzip:  99.61 kB
dist/assets/charts-BTGXyEtx.js            419.29 kB │ gzip: 118.61 kB
----------------------------------------------------------------------
Total Production Bundle (Compressed):       ~274 kB gzip
Build Execution Time:                       516 ms
```

### 6.2 Test Suite Execution
- **Vitest + Testing Library + MSW:** **15 passed** across 3 test suites.
- **Backend Pytest Suite:** **88 passed** (87% statement coverage).
