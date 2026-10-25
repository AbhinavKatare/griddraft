# Notebooks Directory (`/notebooks`)

This directory houses exploratory research, exploratory data analysis (EDA), and prototype model evaluations for quantitative energy traders and analysts.

## Workflow & Conventions

1. **Self-Contained & Reproducible:** Notebooks should read directly from `../data/cache/` using relative paths or instantiate services directly from `backend.app.services`.
2. **Naming Convention:** Numbered prefixes to establish a logical narrative:
   * `01_point_in_time_alignment.ipynb`: Exploratory validation of D-1 cutoffs and information leakage checks.
   * `02_forecast_horizon_decay.ipynb`: Statistical analysis of error contraction from 48h to gate closure.
   * `03_imbalance_cashout_risk.ipynb`: Evaluating signed shortfall risks against historical System Buy Prices.
3. **Clean Checkpoints:** Clear all outputs before committing notebooks, or configure `nbstripout` via git filters to prevent bloating git diffs.
