# Quantitative Methodology: Point-in-Time Forecast Evaluation & Trading Risk Management

This document details the mathematical formulations, market domain context, and statistical assumptions behind the UK Day-Ahead Wind Forecast Monitoring & Trading Analytics application.

---

## 1. Domain Context: GB Day-Ahead Electricity Market

In Great Britain (GB), day-ahead physical wholesale electricity trading occurs primarily through auction gate closures on exchanges (EPEX SPOT and Nord Pool):
- **09:00 GMT / London Time (D-1)**: Proprietary trading desks finalize physical positions, run fundamental dispatch and weather-risk models, and submit preliminary orders.
- **11:00 GMT (EPEX SPOT Day-Ahead Auction)** / **12:00 GMT (Nord Pool Day-Ahead Auction)**: Exchange auction gate closures where equilibrium clearing prices and physical volumes are fixed.
- **Delivery Day (D)**: Power is delivered across 48 half-hourly settlement periods (Period 1 starting at 00:00 GMT, Period 48 ending at 24:00 GMT).

### The Causal Information Invariant
To prevent **information leakage (lookahead bias)** in algorithmic backtests and monitoring dashboards:
$$\text{publishTime} \le \text{cutoff\_time} \le \text{startTime}$$
Where:
- $\text{startTime}$ is the target delivery settlement interval.
- $\text{cutoff\_time}$ is the trader's decision cutoff (e.g. 09:00 on D-1).
- $\text{publishTime}$ is the exact timestamp when Elexon / National Grid ESO published the forecast revision.

---

## 2. Point-in-Time Revision Selection

Given a historical stream of forecast revisions $\mathcal{F} = \{(\text{startTime}_i, \text{publishTime}_i, \hat{y}_i)\}$:
1. For each target $\text{startTime}$, determine the effective cutoff:
   $$\tau = \min(\text{cutoff\_timestamp},\, \text{startTime})$$
2. Filter strictly for available information:
   $$\mathcal{F}_{\le \tau} = \{f \in \mathcal{F} \mid \text{publishTime} \le \tau\}$$
3. Sort stably by $(\text{startTime}, \text{publishTime})$ and execute row-wise selection:
   $$\hat{y}^*(\text{startTime}) = \text{drop\_duplicates}(\text{subset}=[\text{startTime}],\, \text{keep}=\text{last})$$
This row-wise selection preserves official revisions with `NaN` generation if the system operator published missing or incomplete telemetry.

---

## 3. Forecast Accuracy Metrics & Sign Conventions

### 3.1 Signed Error & Imbalance Direction
$$\text{error}_t = \hat{y}_t - y_t = \text{forecast}_t - \text{actual}_t$$
- $\text{error}_t > 0$ (**Over-Forecast**): Nominal forecast exceeds actual outturn.
- $\text{error}_t < 0$ (**Under-Forecast**): Actual outturn exceeds nominal forecast.

### 3.2 Shortfall Error (Deficit Relative to Forecast)
$$\text{shortfall}_t = \max(0,\, \hat{y}_t - y_t) = \max(0,\, \text{error}_t)$$
Shortfall quantifies intervals where generation fell below forecast expectations.

### 3.3 Core Summary Statistics
- **Mean Absolute Error (MAE)**:
  $$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |\hat{y}_t - y_t|$$
- **Root Mean Squared Error (RMSE)**:
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N (\hat{y}_t - y_t)^2}$$
- **Mean Bias Error**:
  $$\text{Bias} = \frac{1}{N} \sum_{t=1}^N (\hat{y}_t - y_t)$$

---

## 4. Empirical Outturn Normalisation (No External Capacity Assumptions)

Standard Mean Absolute Percentage Error ($\text{MAPE} = \frac{1}{N}\sum \frac{|\hat{y}_t - y_t|}{y_t}$) suffers from division by near-zero during calm wind periods. 

Rather than assuming an unmeasured external installed capacity figure, this service normalises strictly by empirical outturn in the dataset:
1. **Mean Generation Normalisation**:
   $$\text{NMAE}_{\text{mean}} = \frac{\text{MAE}}{\overline{y}} \times 100\% \quad (\text{January 2026: } \frac{2,145.17}{11,580.74} = \mathbf{18.52\%})$$
2. **Peak Observed Generation Normalisation**:
   $$\text{NMAE}_{\text{max}} = \frac{\text{MAE}}{\max(y)} \times 100\% \quad (\text{January 2026: } \frac{2,145.17}{17,805.00} = \mathbf{12.05\%})$$
3. **Symmetric MAPE (sMAPE)**:
   $$\text{sMAPE} = \frac{1}{N} \sum_{t=1}^N \frac{2 \cdot |\hat{y}_t - y_t|}{|\hat{y}_t| + |y_t| + \epsilon} \times 100\% \in [0\%, 200\%]$$
4. **Threshold-Masked Safe MAPE**:
   $$\text{MAPE}_{\ge 100\text{MW}} = \frac{1}{|T_{100}|} \sum_{t \in T_{100}} \frac{|\hat{y}_t - y_t|}{y_t} \times 100\%, \quad T_{100} = \{t \mid y_t \ge 100\text{ MW}\}$$

---

## 5. Risk Analytics: Safe Wind, Decomposition, & Backtest

To derate volume commitments against shortfall risk, traders compute a conservative **"Safe Wind to Count On"** volume:

1. **Shortfall Quantile Buffer**:
   For a desired confidence level $\alpha \in [0.50, 0.999]$ (typically $\alpha = 0.90$, i.e. P90):
   $$Q_\alpha = \text{Quantile}_\alpha(\{\text{shortfall}_t\})$$
2. **Buffer Decomposition**:
   The total buffer is decomposed into systematic bias and stochastic residual:
   $$\text{systematic\_bias} = \text{mean}(\text{shortfall})$$
   $$\text{residual\_quantile} = \max(0.0,\, Q_\alpha - \text{systematic\_bias})$$
   $$\text{total\_buffer} = \text{systematic\_bias} + \text{residual\_quantile}$$
3. **Safe Wind Volume**:
   $$\text{safe\_wind}_t = \max(0.0,\, \hat{y}_t - Q_\alpha)$$
4. **Implied Backup Thermal Procurement**:
   $$\text{thermal\_procurement}_t = \hat{y}_t - \text{safe\_wind}_t = \min(\hat{y}_t,\, Q_\alpha)$$
   Guarantees the identity: $\text{safe\_wind}_t + \text{thermal\_procurement}_t \equiv \hat{y}_t$.
5. **In-Sample vs Prior-Days Toggle**:
   - `in_sample`: Uses the complete month calibration sample.
   - `prior_days`: Uses strictly preceding days ($d < D$) to construct the shortfall distribution out-of-sample.
6. **Empirical Backtest of Buffer Coverage**:
   Evaluates whether outturn covered the derated safe wind:
   $$\text{breach}_t = \mathbb{I}(y_t < \text{safe\_wind}_t)$$
   $$\text{empirical\_coverage\_pct} = \frac{\sum (1 - \text{breach}_t)}{N} \times 100\%$$

---

## 6. Statistical Assumptions & Limitations

1. **Stationarity Assumption**:
   - Assumes that the historical shortfall distribution remains representative in subsequent delivery windows.
   - Limitation: Macro weather regime transitions alter the distribution.
2. **Homoskedastic Quantile Buffering**:
   - Subtracting a constant buffer $Q_\alpha$ treats shortfall uncertainty as additive and uniform across all forecast magnitudes.
3. **Finite Sample Uncertainty**:
   - A 1-month evaluation window comprises 1,488 half-hourly settlement periods. Tail quantiles (P95, P99) have wider confidence intervals than median (P50).
