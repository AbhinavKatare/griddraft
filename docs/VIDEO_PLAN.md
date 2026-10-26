# UK Wind Forecast Decision Tool — Simple & Easy Video Script

> **How to use this guide:**  
> Read the spoken lines naturally at your own pace. All hard-to-read jargon has been removed. Every button click and screen action is clearly highlighted so you know exactly where to click and what to point at on the screen.

---

## ⏱️ Fast Timing Plan (Under 10 Minutes Total)

| Section | Target Time | Who You Are Talking To | What You Are Doing |
| :--- | :--- | :--- | :--- |
| **Part 1: Customer Demo** | **~4 Minutes** | The Power Trader / Client | Show the live website, click the features, and explain the real business value. |
| **Part 2: Tech Lead Review**| **~4 Minutes** | The Senior Engineer / Tech Lead | Show how it was built, where the files are, how fast it runs, and how tests pass. |
| **Wrap Up** | **30 Seconds** | Everyone | Quick goodbye and link check. |

---

## 🛠️ Quick 1-Minute Prep Before Hitting Record

1. **Wake up the backend**: Open [https://griddraft.onrender.com/health](https://griddraft.onrender.com/health) in a browser tab. Make sure it shows `healthy`.
2. **Open the live website**: Open [https://griddraft-one.vercel.app](https://griddraft-one.vercel.app) in full screen (`F11`).
   - Zoom in slightly (press `Ctrl +` once to 110% or 125%) so cards and numbers are easy to read on video.
   - Start on the **Decision** view (the default page).
3. **Open VS Code in another window**:
   - Have two files ready in tabs:
     - `backend/app/analytics/forecast_selection.py`
     - `backend/app/analytics/risk.py`
   - Have a terminal open ready to run `python scripts/verify_numbers.py`.

---

# PART 1: Customer Demo (Simple & Fast)
**Your Goal:** Show the customer how this tool saves them money and protects them from bad forecasts.  
**Length:** ~4 minutes.

---

### Step 1: The Problem (0:00 – 0:45)
- **Where to look:** Full-screen browser on the live site (`https://griddraft-one.vercel.app`).
- **Mouse action:** Move the mouse over the main chart.
- **What to say:**
  > *"Hi everyone. Today I'm excited to walk you through the UK Wind Forecast Decision Tool, built using real UK grid data from January 2026.*  
  >  
  > *If you trade power on the UK Day-Ahead market, you have to lock in how much electricity you're going to sell by 11:00 AM on the day before delivery.*  
  >  
  > *The problem is: the official wind forecast is often way too optimistic. In January, the forecast over-estimated wind power on **27 out of 31 days**, by an average of **1,852 Megawatts**.*  
  >  
  > *If you sell what the forecast promises, you will be caught short physical energy 87% of the time, and you'll have to pay expensive penalty fees to balance your position.*  
  >  
  > *We built this portal to give traders a realistic, conservative number they can actually count on before submitting their bids."*

---

### Step 2: The Decision Screen & Top Controls (0:45 – 1:30)
- **Where to look:** Top control bar of the website.
- **Actions on screen:**
  1. Point mouse at **Delivery Date**: show `2026-01-15`.
  2. Point mouse at **Cutoff Time**: click or hover over `09:00 UTC`.
- **What to say:**
  > *"Let's look at the live platform.*  
  >  
  > *Right at the top, we have our control bar. Here you can pick any delivery day in January 2026—for this demo, we're looking at **January 15**.*  
  >  
  > *Next to it is the **Cutoff Time**. We've selected **09:00 AM on D-1**.*  
  >  
  > *Why does this matter? Because we only use forecasts that were actually published before your decision deadline. We strictly block any newer forecasts from leaking into your backtest, so you see exactly what your trader saw on their screen at 9:00 AM."*

---

### Step 3: Where is the Summary Strip & Safe Wind? (1:30 – 2:15)
- **Where it is on screen:** Look right between the top control bar and the big chart. You will see a thin grey banner and **4 large summary cards**.
- **Actions on screen:**
  1. Point mouse at the thin banner: *"Auction Decision Snapshot: Cutoff at 09:00 UTC on D-1"*.
  2. Move mouse across the 4 cards:
     - **Card 1 (Forecast Day Volume)**: points to `331,100 MWh`.
     - **Card 2 (Conservative 'Safe' Volume)**: points to `228,500 MWh`.
     - **Card 3 (Peak Extra Procurement)**: points to `2,200 MW`.
     - **Card 4 (Total Backup Energy)**: points to `102,600 MWh`.
- **What to say:**
  > *"Right below the controls and above the chart, you see our **Summary Strip**.*  
  >  
  > *The first card shows the raw forecast: **331,100 Megawatt-hours**. If your trader blindly sells that amount, they take on huge risk.*  
  >  
  > *The second card shows our **Safe Wind Volume**: **228,500 Megawatt-hours**. We've derated the forecast using a 90% confidence buffer so you don't over-promise.*  
  >  
  > *The third card tells you exactly how much backup power you need to line up in advance: **2,200 Megawatts** at peak.*  
  >  
  > *Instead of getting hit with unexpected penalty bills later, your desk knows your exact hedge requirements before the auction even starts."*

---

### Step 4: The "Leaky Baseline" Toggle (2:15 – 3:00)
- **Where it is on screen:** Back in the top control bar, look for the toggle switch labeled **"Leaky Baseline"**.
- **Actions on screen:**
  1. **Click the "Leaky Baseline" toggle switch**.
  2. Watch the dashed grey line appear on the main chart.
  3. Move mouse to hover where the dashed line is higher than the solid line.
- **What to say:**
  > *"Now watch what happens when I turn on this toggle: **Leaky Baseline**.*  
  >  
  > *A dashed grey curve appears on the chart. That dashed curve represents the last-minute forecast published right before delivery.*  
  >  
  > *Notice how much it changed from our solid decision line!*  
  >  
  > *Many trading desks make the mistake of evaluating their models against that dashed line. That's what we call **information leakage**—it makes you think the forecast was great, but that update arrived hours after your auction closed. Our solid line is the only number you actually had when you clicked submit."*

---

### Step 5: The Accuracy View & 3 Big Takeaways (3:00 – 4:15)
- **Where it is on screen:** In the top navigation bar at the very top right, click **"Accuracy"**.
- **Actions on screen:**
  1. Click **"Accuracy"**. The page changes to show the monthly KPIs.
  2. Point at **Card 1 (Mean Absolute Error - MAE)**: `2,145.2 MW`.
  3. Point at **Card 3 (Systematic Bias)**: `+1,851.9 MW`.
  4. Point at **Card 4 (P90 Shortfall Buffer)**: `4,274.9 MW`.
- **What to say:**
  > *"Now let's click on the **Accuracy** tab.*  
  >  
  > *Here are the three big takeaways from our whole month analysis:*  
  >  
  > *1. **The Average Error**: At decision time, the average error was **2,145 Megawatts**, or about 18.5% of real generation.*  
  > *2. **The Systematic Over-Forecast**: The models had a positive bias of **+1,852 Megawatts**, over-forecasting 27 out of 31 days.*  
  > *3. **The 90% Safe Buffer**: To be 90% confident you won't be caught short, you need a **4,275 Megawatt buffer**.*  
  >  
  > *The best part is that our tool splits that buffer into two parts: 1,852 Megawatts is predictable bias, and 2,423 Megawatts is real weather randomness.*  
  >  
  > *That means your desk doesn't need to buy expensive backup contracts for the whole amount—you simply adjust your bids down for the bias, and only hedge the weather risk. That's real money saved every single morning."*

---

# PART 2: Tech Lead Review (Clear, Simple & Fast)
**Your Goal:** Show the tech lead the architecture, clean code, speed, and tests without getting bogged down in complicated syntax.  
**Length:** ~4 minutes.

---

### Step 1: Architecture & Why We Didn't Use a Database (4:15 – 5:15)
- **Where to look:** Switch screen to VS Code and show `README.md` (the Mermaid diagram) or keep browser on the website.
- **What to say:**
  > *"Now let's switch gears and look at the engineering under the hood.*  
  >  
  > *First, **Deployment**: We use a clean split setup.*  
  > *- The React frontend is deployed on **Vercel**.*  
  > *- The FastAPI backend is running inside a Docker container on **Render**.*  
  > *- Vercel automatically forwards all `/api` calls directly to Render behind the scenes, so the browser sees everything as one single website with zero CORS errors.*  
  >  
  > *Second, **Storage**: You might wonder why we didn't spin up a Postgres database.*  
  > *- For January 2026, we have 18,104 forecast rows and 1,488 actual rows.*  
  > *- We saved this data as compressed **Parquet files** in the repo, which takes only **122 Kilobytes** total.*  
  > *- When the backend starts up, Python loads the entire dataset straight into memory in under **15 milliseconds**.*  
  > *- Every API request responds in under 5 milliseconds with zero database network lag and zero maintenance."*

---

### Step 2: The Core Python Logic (5:15 – 6:15)
- **Where to look:** In VS Code, open [forecast_selection.py](file:///d:/UK%20weather%20forecast/backend/app/analytics/forecast_selection.py#L110).
- **Actions on screen:**
  1. Highlight lines 110–130 (`select_decision_forecast`).
  2. Open [risk.py](file:///d:/UK%20weather%20forecast/backend/app/analytics/risk.py#L40) and highlight `decompose_shortfall_buffer`.
- **What to say:**
  > *"Let's look at the two most important Python files in `backend/app/analytics/`.*  
  >  
  > *In `forecast_selection.py`, the function `select_decision_forecast` enforces our main rule:*  
  > *The forecast publication time must be before or equal to the decision cutoff time.*  
  >  
  > *We don't use slow `for` loops. We use fast, vectorised Pandas operations—filtering out late records and taking the latest valid forecast revision.*  
  >  
  > *Next, in `risk.py`, we calculate Safe Wind. We define shortfall as only when forecast is higher than actual generation. We calculate the 90th percentile shortfall and split it cleanly into the average bias and the residual risk."*

---

### Step 3: Tests & Reliability (6:15 – 7:30)
- **Where to look:** Switch to your terminal in VS Code.
- **Actions on screen:**
  1. Run this command: `python scripts/verify_numbers.py`.
  2. Watch the 9 green `[PASS]` sections print out.
- **What to say:**
  > *"Quality and verification were top priorities.*  
  >  
  > *Notice this command: `python scripts/verify_numbers.py`. It runs 9 verification checks right against the real data:*  
  > *- It re-calculates all KPIs using pure NumPy to prove the numbers are 100% correct.*  
  > *- It confirms that the 31 daily averages equal the full-month average.*  
  > *- And it tests Daylight Saving Time clock switches for London time—including 23-hour days in March and 25-hour days in October.*  
  >  
  > *Across the whole project, we have **112 automated backend tests** and **38 frontend tests**, all enforced automatically on every commit in GitHub Actions."*

---

### Step 4: Keep-Alive & Practical Trade-Offs (7:30 – 8:30)
- **Where to look:** Switch back to the browser on `https://griddraft-one.vercel.app`.
- **What to say:**
  > *"Two quick practical engineering details:*  
  >  
  > *1. **Keep-Alive on Render**: Render's free tier spins down after 15 minutes of inactivity. To prevent cold starts, our FastAPI server runs a background task that pings its own health check every 14 minutes, and the React frontend also pings on page load.*  
  >  
  > *2. **Trade-offs**: Elexon publishes forecasts hourly, while actual generation is half-hourly. We map each hourly forecast flat across both 30-minute intervals. While this smooths out sub-hour wind changes, it keeps 100% of the data intact without making up synthetic numbers.*  
  >  
  > *The next feature on our roadmap is integrating live System Buy Prices so traders can see exact Pound Sterling penalty costs alongside Megawatt volumes."*

---

### Step 5: Wrap Up (8:30 – 9:00)
- **Where to look:** Move mouse back to the Decision view and show the live chart.
- **What to say:**
  > *"To wrap up:*  
  > *- The website is live right now at `griddraft-one.vercel.app`.*  
  > *- The backend is running on Render.*  
  > *- All tests are passing, and all code is fully documented in the GitHub repository.*  
  >  
  > *Thank you very much, and I'd be happy to answer any questions!"*

---

## 📌 Numbers You Might Need to Glance At (Cheat-Sheet)

- **Total intervals in January 2026**: 1,488 (100% complete)
- **Decision MAE**: 2,145.2 MW
- **Latest Pre-Delivery MAE**: 1,804.2 MW
- **Leakage Difference**: 341.0 MW (15.9%)
- **Systematic Bias**: +1,851.9 MW over-forecast (27 of 31 days)
- **P90 Buffer**: 4,274.9 MW (1,852 MW bias + 2,423 MW weather noise)
- **Parquet Cache Size**: 122 KB total on disk
- **Tests**: 112 Backend passed, 38 Frontend passed
