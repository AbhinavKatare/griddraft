# Frontend Application (`/frontend`)

The frontend application is an energy trading terminal built with **React 19 + TypeScript (Vite)** and custom **Vanilla CSS** with obsidian dark mode, glassmorphism, glowing telemetry accents, and responsive SVG charts.

## Structure

```text
frontend/
├── src/
│   ├── types.ts              # TypeScript interfaces mirroring backend schemas
│   ├── api.ts                # Typed fetch API client
│   ├── components/
│   │   ├── Header.tsx        # Navigation, Elexon cache status pill, D-1 time picker
│   │   ├── KPICards.tsx      # Executive trading metrics (MAE, RMSE, Bias, P90 Risk)
│   │   ├── DayForecastChart.tsx # 48 Settlement Periods actuals vs forecast with error deltas
│   │   ├── DayDataTable.tsx  # Tabular audit with sorting and shortfall filters
│   │   ├── HorizonAnalysis.tsx # Accuracy decay curves (48h down to 3h before delivery)
│   │   ├── SettlementProfileChart.tsx # Diurnal SP 1–48 peak vs off-peak curves
│   │   ├── DailyTrendChart.tsx # Month-long daily MAE trend with click-to-inspect
│   │   └── RiskDistribution.tsx # P50/P90/P99 risk table & error histogram
│   ├── App.tsx               # Main state orchestration
│   ├── index.css             # Energy terminal design system
│   └── main.tsx              # DOM entrypoint
├── package.json
├── vite.config.ts            # Vite config with backend proxy (/api -> http://127.0.0.1:8000)
├── nginx.conf                # Nginx proxy for containerized SPA
└── Dockerfile
```

## Running Locally

```bash
# Install dependencies
npm install

# Run TypeScript build check
npm run build

# Start Vite dev server
npm run dev
```
Accessible at: `http://localhost:5173`
