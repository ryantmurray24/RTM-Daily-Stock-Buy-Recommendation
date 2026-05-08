# RTM-Daily-Stock-Buy-Recommendation
VTI/VXUS buy recommendations
# 📡 Macro-Core Investment Report

Auto-updating VTI/VXUS investment report hosted on GitHub Pages.  
Refreshes automatically at **market open (9:30 AM ET)** and **market close (4:00 PM ET)**, Monday–Friday.

---

## 🚀 Setup (5 minutes)

### Step 1 — Create the repository

1. Go to [github.com](https://github.com) and sign in (create a free account if needed)
2. Click the **+** icon → **New repository**
3. Name it `macro-report` (or anything you like)
4. Set it to **Public** ← required for free GitHub Pages
5. Click **Create repository**

---

### Step 2 — Upload the files

Drag and drop these four files into the repo (or use `git push`):

```
generate_report.py
requirements.txt
.github/
  workflows/
    update_report.yml
```

To upload via browser:
1. In your new repo, click **Add file → Upload files**
2. Upload `generate_report.py` and `requirements.txt`
3. For the workflow file, you need to create it manually:
   - Click **Add file → Create new file**
   - Name it `.github/workflows/update_report.yml`
   - Paste the contents of `update_report.yml`
   - Click **Commit new file**

---

### Step 3 — Enable GitHub Pages

1. In your repo, click **Settings** (top tab)
2. Scroll to **Pages** in the left sidebar
3. Under **Source**, select **Deploy from a branch**
4. Branch: `main` · Folder: `/ (root)`
5. Click **Save**

Your site will be live at:
```
https://YOUR-USERNAME.github.io/macro-report/
```

---

### Step 4 — Run it once manually to generate the first report

1. Click the **Actions** tab in your repo
2. Click **Update Market Report** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Wait ~30 seconds for it to complete
5. Refresh your GitHub Pages URL — the report is live!

---

## 🕐 Schedule

The workflow runs automatically on **US market weekdays only**:

| Time | Event |
|------|-------|
| 9:30 AM ET | Market open update |
| 4:00 PM ET | Market close update |

> **Note:** GitHub Actions cron jobs can run a few minutes late — this is normal and fine for a daily report.

---

## 🔧 Customization

All methodology logic lives in `generate_report.py`. Key sections:

- **`fetch_data()`** — pulls live prices via `yfinance` (free, no API key needed)
- **`get_lump_sum_rule(vix)`** — VIX-based deployment logic
- **`render_html()`** — full HTML template

To update the methodology, edit `generate_report.py` and push — the next scheduled run will use the new logic.

---

## 💰 Cost

**$0.** This uses:
- **GitHub Pages** — free static site hosting
- **GitHub Actions** — free tier gives 2,000 minutes/month; this job uses ~30 min/month
- **yfinance** — free Yahoo Finance data wrapper, no API key required

---

## ⚠️ Disclaimer

Educational framework only — not personalized financial advice.  
Consult a licensed financial advisor before making investment decisions.
