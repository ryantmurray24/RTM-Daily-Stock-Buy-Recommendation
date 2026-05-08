"""
Macro-Core Investment Report Generator
VTI / VXUS — Methodology v2
Runs at market open (9:30 AM ET) and market close (4:00 PM ET) on weekdays.
"""

import yfinance as yf
import datetime
import pytz
import json
import os


# ── DATA FETCH ─────────────────────────────────────────────────────────────────

def fetch_data():
    tickers = yf.Tickers("VTI VXUS ^VIX")

    vti  = tickers.tickers["VTI"]
    vxus = tickers.tickers["VXUS"]
    vix  = tickers.tickers["^VIX"]

    vti_fast  = vti.fast_info
    vxus_fast = vxus.fast_info
    vix_fast  = vix.fast_info

    # Prices
    vti_price  = round(vti_fast.last_price,  2)
    vxus_price = round(vxus_fast.last_price, 2)
    vix_level  = round(vix_fast.last_price,  2)

    # 52-week range
    vti_52wk_high  = round(vti_fast.year_high,  2)
    vti_52wk_low   = round(vti_fast.year_low,   2)
    vxus_52wk_high = round(vxus_fast.year_high, 2)
    vxus_52wk_low  = round(vxus_fast.year_low,  2)

    # Day change
    vti_prev  = round(vti_fast.previous_close,  2)
    vxus_prev = round(vxus_fast.previous_close, 2)
    vix_prev  = round(vix_fast.previous_close,  2)

    def pct_chg(price, prev):
        return round(((price - prev) / prev) * 100, 2) if prev else 0.0

    vti_chg_pct  = pct_chg(vti_price,  vti_prev)
    vxus_chg_pct = pct_chg(vxus_price, vxus_prev)
    vix_chg_pct  = pct_chg(vix_level,  vix_prev)

    # Drawdown from 52-wk high
    vti_drawdown  = round(((vti_price  - vti_52wk_high)  / vti_52wk_high)  * 100, 2)
    vxus_drawdown = round(((vxus_price - vxus_52wk_high) / vxus_52wk_high) * 100, 2)

    # Trailing P/E
    try:
        vti_info = vti.info
        vti_pe   = vti_info.get("trailingPE")
        vti_pe   = round(float(vti_pe), 1) if vti_pe else None
    except Exception:
        vti_pe = None

    try:
        vxus_info = vxus.info
        vxus_pe   = vxus_info.get("trailingPE")
        vxus_pe   = round(float(vxus_pe), 1) if vxus_pe else None
    except Exception:
        vxus_pe = None

    # YTD return
    try:
        et  = pytz.timezone("America/New_York")
        now = datetime.datetime.now(et)
        jan2      = datetime.datetime(now.year, 1, 2).strftime("%Y-%m-%d")
        today_str = now.strftime("%Y-%m-%d")

        vti_hist  = vti.history(start=jan2,  end=today_str)
        vxus_hist = vxus.history(start=jan2, end=today_str)

        vti_ytd  = round(((vti_price  - vti_hist["Close"].iloc[0])  / vti_hist["Close"].iloc[0])  * 100, 1) if not vti_hist.empty  else None
        vxus_ytd = round(((vxus_price - vxus_hist["Close"].iloc[0]) / vxus_hist["Close"].iloc[0]) * 100, 1) if not vxus_hist.empty else None
    except Exception:
        vti_ytd = vxus_ytd = None

    return {
        "vti_price":       vti_price,
        "vti_prev":        vti_prev,
        "vti_chg_pct":     vti_chg_pct,
        "vti_52wk_high":   vti_52wk_high,
        "vti_52wk_low":    vti_52wk_low,
        "vti_drawdown":    vti_drawdown,
        "vti_pe":          vti_pe,
        "vti_ytd":         vti_ytd,
        "vxus_price":      vxus_price,
        "vxus_prev":       vxus_prev,
        "vxus_chg_pct":    vxus_chg_pct,
        "vxus_52wk_high":  vxus_52wk_high,
        "vxus_52wk_low":   vxus_52wk_low,
        "vxus_drawdown":   vxus_drawdown,
        "vxus_pe":         vxus_pe,
        "vxus_ytd":        vxus_ytd,
        "vix_level":       vix_level,
        "vix_prev":        vix_prev,
        "vix_chg_pct":     vix_chg_pct,
    }


# ── METHODOLOGY LOGIC ──────────────────────────────────────────────────────────

def get_lump_sum_rule(vix):
    if vix < 20:
        return {
            "zone":    "below_20",
            "deploy":  50,
            "hold":    50,
            "label":   "Deploy 50% now · Hold 50% for next contribution cycle",
            "color":   "green",
            "pill":    f"VIX {vix:.1f} → Deploy 50% Rule",
        }
    elif vix <= 30:
        return {
            "zone":    "20_to_30",
            "deploy":  75,
            "hold":    25,
            "label":   "Deploy 75% now · Hold 25% in reserve",
            "color":   "amber",
            "pill":    f"VIX {vix:.1f} → Deploy 75% Rule",
        }
    else:
        return {
            "zone":    "above_30",
            "deploy":  100,
            "hold":    0,
            "label":   "Deploy 100% immediately — elevated fear is a historically favorable entry",
            "color":   "red",
            "pill":    f"VIX {vix:.1f} → Deploy 100% — High Fear Zone",
        }


def fmt_price(v):
    return f"${v:,.2f}" if v is not None else "N/A"

def fmt_pct(v, plus=True):
    if v is None:
        return "N/A"
    sign = "+" if v > 0 and plus else ""
    return f"{sign}{v:.2f}%"

def fmt_pe(v):
    return f"{v:.1f}×" if v is not None else "N/A"

def val_color(v):
    if v is None:
        return ""
    return "val-green" if v >= 0 else "val-red"

def dd_color(v):
    if v is None:
        return ""
    if v < -5:
        return "val-red"
    if v < 0:
        return "val-amber"
    return "val-green"


# ── HTML RENDER ────────────────────────────────────────────────────────────────

def render_html(d, date_str, session_label):
    vix   = d["vix_level"]
    lump  = get_lump_sum_rule(vix)

    vix_pct = min(max(vix / 45 * 100, 2), 98)

    z_green = "active" if lump["zone"] == "below_20" else ""
    z_amber = "active" if lump["zone"] == "20_to_30" else ""
    z_red   = "active" if lump["zone"] == "above_30" else ""

    now_tag_green = "&nbsp;<span class='active-flag'>NOW</span>" if z_green else ""
    now_tag_amber = "&nbsp;<span class='active-flag'>NOW</span>" if z_amber else ""
    now_tag_red   = "&nbsp;<span class='active-flag'>NOW</span>" if z_red   else ""

    pill_map = {"green": "pill-green", "amber": "pill-amber", "red": "pill-red"}
    lump_pill = pill_map[lump["color"]]

    pe_gap = round(d["vti_pe"] - d["vxus_pe"], 1) if d["vti_pe"] and d["vxus_pe"] else None
    pe_gap_str = f"{pe_gap:.1f}× cheaper internationally" if pe_gap else "N/A"

    vti_chg_tc  = "tc-green" if d["vti_chg_pct"]  >= 0 else "tc-red"
    vxus_chg_tc = "tc-green" if d["vxus_chg_pct"] >= 0 else "tc-red"
    vix_chg_tc  = "tc-green" if d["vix_chg_pct"]  <= 0 else "tc-red"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Macro-Core Report · {date_str}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:#f4f5f7;color:#111;padding:20px;font-size:13px;line-height:1.5;}}
  .wrap{{max-width:860px;margin:0 auto;}}
  /* HEADER */
  .hdr{{background:#fff;border-radius:8px;padding:18px 22px;margin-bottom:14px;border:1px solid #e0e0e0;display:flex;justify-content:space-between;align-items:center;}}
  .hdr h1{{font-size:17px;font-weight:800;}} .hdr p{{font-size:12px;color:#666;margin-top:2px;}}
  .hdr-r{{text-align:right;}} .hdr-r .dt{{font-size:14px;font-weight:800;}} .hdr-r .sess{{font-size:11px;color:#888;margin-top:2px;}} .hdr-r .upd{{font-size:10px;color:#bbb;margin-top:2px;}}
  /* TICKER STRIP */
  .strip{{background:#111;border-radius:8px;padding:14px 20px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;margin-bottom:14px;}}
  .ti{{text-align:center;padding:0 12px;}} .ti+.ti{{border-left:1px solid #2a2a2a;}}
  .ti-sym{{font-size:11px;font-weight:700;letter-spacing:1px;color:#666;margin-bottom:3px;}}
  .ti-px{{font-size:22px;font-weight:800;color:#fff;}}
  .ti-chg{{font-size:12px;font-weight:600;margin-top:2px;}}
  .tc-green{{color:#4ade80;}} .tc-red{{color:#f87171;}} .tc-amber{{color:#fbbf24;}}
  /* SECTION */
  .sec{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:12px;overflow:hidden;}}
  .sec-h{{display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid #ebebeb;background:#fafafa;}}
  .sec-n{{font-size:11px;font-weight:800;color:#fff;background:#111;border-radius:50%;width:22px;height:22px;flex-shrink:0;display:flex;align-items:center;justify-content:center;}}
  .sec-t{{font-size:13px;font-weight:700;flex:1;}}
  .sec-b{{padding:14px 16px;}}
  /* PILLS */
  .pill{{display:inline-block;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;}}
  .pill-green{{background:#e6f4ea;color:#1a6b35;border:1px solid #86c99a;}}
  .pill-amber{{background:#fef9e6;color:#7a5800;border:1px solid #e8c96a;}}
  .pill-red{{background:#fde8e8;color:#8b0000;border:1px solid #f5b0b0;}}
  .pill-grey{{background:#f0f0f0;color:#555;border:1px solid #ccc;}}
  /* TEXT */
  .sl{{font-size:13px;font-weight:700;margin-bottom:6px;}}
  .green{{color:#1a6b35;}} .amber{{color:#7a5800;}} .red{{color:#8b0000;}} .grey{{color:#555;}}
  .bt{{font-size:12px;color:#444;line-height:1.6;}} .bt strong{{color:#111;}}
  /* VIX */
  .vix-track{{height:12px;border-radius:6px;position:relative;margin:12px 0 4px;background:linear-gradient(to right,#bbf7d0 0%,#bbf7d0 33%,#fde68a 33%,#fde68a 66%,#fecaca 66%,#fecaca 100%);border:1px solid #ddd;}}
  .vix-dot{{position:absolute;top:-4px;width:20px;height:20px;border-radius:50%;background:#111;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3);transform:translateX(-50%);}}
  .vix-lbl{{display:flex;justify-content:space-between;font-size:10px;color:#888;margin-bottom:10px;}}
  .vix-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;}}
  .vr{{border-radius:6px;padding:10px 12px;border:1.5px solid;font-size:11px;line-height:1.5;}}
  .vr.active{{border-width:2.5px;box-shadow:0 0 0 2px rgba(0,0,0,.07);}}
  .vr.vg{{background:#f0faf2;border-color:#2a9d8f;}} .vr.va{{background:#fffbf0;border-color:#d4a017;}} .vr.vr2{{background:#fff5f5;border-color:#cc3333;}}
  .rr{{font-weight:800;font-size:12px;margin-bottom:3px;}}
  .vg .rr{{color:#1a7a6e;}} .va .rr{{color:#9a6700;}} .vr2 .rr{{color:#cc0000;}}
  .ra{{font-weight:700;}} .vg .ra{{color:#1a7a6e;}} .va .ra{{color:#9a6700;}} .vr2 .ra{{color:#cc0000;}}
  .af{{font-size:9px;font-weight:700;background:#111;color:#fff;padding:1px 5px;border-radius:3px;margin-left:4px;vertical-align:middle;}}
  /* TABLES */
  .tbl{{width:100%;border-collapse:collapse;margin-top:6px;}}
  .tbl thead tr{{border-bottom:2px solid #e0e0e0;}}
  .tbl th{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;padding:5px 10px;text-align:left;}}
  .tbl td{{font-size:12px;padding:8px 10px;border-bottom:1px solid #f0f0f0;}}
  .tbl tr:last-child td{{border-bottom:none;}}
  .tbl td:first-child{{color:#666;}} .tbl td:last-child{{font-weight:700;text-align:right;}}
  .val-green{{color:#1a7a38;}} .val-red{{color:#cc2200;}} .val-amber{{color:#9a6700;}}
  .ok{{color:#1a6b35;font-weight:700;}}
  /* NOISE */
  .ni{{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-bottom:1px solid #f0f0f0;font-size:12px;}}
  .ni:last-child{{border-bottom:none;}}
  .nx{{flex-shrink:0;width:18px;height:18px;border-radius:50%;background:#fde8e8;color:#cc0000;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;margin-top:1px;}}
  .nt{{color:#444;line-height:1.5;}} .nt strong{{color:#cc0000;}}
  .footer{{text-align:center;font-size:10px;color:#bbb;padding:14px;margin-top:4px;}}
</style>
</head>
<body>
<div class="wrap">

<div class="hdr">
  <div>
    <h1>📡 Macro-Core Investment Report</h1>
    <p>VTI &amp; VXUS · 60/40 Buy &amp; Hold · Methodology v2</p>
  </div>
  <div class="hdr-r">
    <div class="dt">{date_str}</div>
    <div class="sess">{session_label}</div>
    <div class="upd">Auto-updated via GitHub Actions</div>
  </div>
</div>

<div class="strip">
  <div class="ti">
    <div class="ti-sym">VTI — U.S. Total Market</div>
    <div class="ti-px">{fmt_price(d['vti_price'])}</div>
    <div class="ti-chg {vti_chg_tc}">{fmt_pct(d['vti_chg_pct'])} today &nbsp;·&nbsp; 52wk H: {fmt_price(d['vti_52wk_high'])}</div>
  </div>
  <div class="ti">
    <div class="ti-sym">VXUS — International</div>
    <div class="ti-px">{fmt_price(d['vxus_price'])}</div>
    <div class="ti-chg {vxus_chg_tc}">{fmt_pct(d['vxus_chg_pct'])} today &nbsp;·&nbsp; 52wk H: {fmt_price(d['vxus_52wk_high'])}</div>
  </div>
  <div class="ti">
    <div class="ti-sym">VIX — Fear Index</div>
    <div class="ti-px tc-amber">{vix:.2f}</div>
    <div class="ti-chg {vix_chg_tc}">{fmt_pct(d['vix_chg_pct'])} today &nbsp;·&nbsp; Prev: {d['vix_prev']:.2f}</div>
  </div>
</div>

<!-- 1: CONTRIBUTIONS -->
<div class="sec">
  <div class="sec-h">
    <div class="sec-n">1</div>
    <div class="sec-t">Regular Contribution Status</div>
    <span class="pill pill-green">✅ Execute as Normal</span>
  </div>
  <div class="sec-b">
    <div class="sl green">Scheduled contributions proceed on time, at full amount — no conditions.</div>
    <div class="bt">Regular monthly contributions are never held back or delayed based on price, VIX, moving averages, RSI, or proximity to highs. Dollar cost averaging executes automatically. <strong>No signal is required and no signal can pause it.</strong></div>
  </div>
</div>

<!-- 2: LUMP SUM -->
<div class="sec">
  <div class="sec-h">
    <div class="sec-n">2</div>
    <div class="sec-t">Lump Sum Deployment Status</div>
    <span class="pill {lump_pill}">{lump['pill']}</span>
  </div>
  <div class="sec-b">
    <div class="sl {lump['color']}">{lump['label']}</div>
    <div class="vix-track"><div class="vix-dot" style="left:{vix_pct:.1f}%;"></div></div>
    <div class="vix-lbl"><span>0 — Low Fear</span><span>20</span><span>30</span><span>45+ — Max Fear</span></div>
    <div class="vix-grid">
      <div class="vr vg {z_green}">
        <div class="rr">VIX &lt; 20{now_tag_green}</div>
        <div class="ra">Deploy 50% immediately</div>
        <div style="font-size:11px;color:#555;margin-top:3px;">Hold 50% for next contribution cycle</div>
      </div>
      <div class="vr va {z_amber}">
        <div class="rr">VIX 20–30{now_tag_amber}</div>
        <div class="ra">Deploy 75% immediately</div>
        <div style="font-size:11px;color:#555;margin-top:3px;">Hold 25% in reserve</div>
      </div>
      <div class="vr vr2 {z_red}">
        <div class="rr">VIX &gt; 30{now_tag_red}</div>
        <div class="ra">Deploy 100% immediately</div>
        <div style="font-size:11px;color:#555;margin-top:3px;">Elevated fear = historically favorable entry</div>
      </div>
    </div>
    <div class="bt">Applies to <strong>unscheduled capital only</strong> — bonuses, ESPP proceeds, tax refunds, unspent buffer. Maintain 60/40 split. Regular contributions are never affected by VIX level.</div>
  </div>
</div>

<!-- 3: REBALANCING -->
<div class="sec">
  <div class="sec-h">
    <div class="sec-n">3</div>
    <div class="sec-t">Rebalancing Status</div>
    <span class="pill pill-grey">📅 Next Check: January 2027</span>
  </div>
  <div class="sec-b">
    <div class="sl grey">No rebalancing action required — next scheduled check is January 2027.</div>
    <table class="tbl">
      <thead><tr><th>ETF</th><th>Target</th><th>Current (est.)</th><th>Drift</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td><strong>VTI</strong></td><td>60%</td><td>~60%</td><td class="ok">~0%</td><td class="ok">✅ On target</td></tr>
        <tr><td><strong>VXUS</strong></td><td>40%</td><td>~40%</td><td class="ok">~0%</td><td class="ok">✅ On target</td></tr>
      </tbody>
    </table>
    <div class="bt" style="margin-top:10px;">Rebalancing occurs <strong>once per year in January only.</strong> Threshold: 5%+ drift → rebalance inside tax-advantaged accounts (401k, Roth IRA) first. Taxable accounts only if drift exceeds 10%.</div>
  </div>
</div>

<!-- 4: VALUATION -->
<div class="sec">
  <div class="sec-h">
    <div class="sec-n">4</div>
    <div class="sec-t">Valuation Context</div>
    <span class="pill pill-grey">ℹ️ Informational Only — No Action</span>
  </div>
  <div class="sec-b">
    <table class="tbl">
      <tbody>
        <tr><td>VTI Price</td>             <td>{fmt_price(d['vti_price'])} &nbsp;({fmt_pct(d['vti_chg_pct'])} today)</td></tr>
        <tr><td>VTI 52-Wk High</td>        <td>{fmt_price(d['vti_52wk_high'])}</td></tr>
        <tr><td>VTI Drawdown from High</td><td class="{dd_color(d['vti_drawdown'])}">{fmt_pct(d['vti_drawdown'], plus=False)}</td></tr>
        <tr><td>VTI YTD Return</td>        <td class="{val_color(d['vti_ytd'])}">{fmt_pct(d['vti_ytd'])}</td></tr>
        <tr><td>VTI P/E (Trailing)</td>    <td>{fmt_pe(d['vti_pe'])}</td></tr>
        <tr><td>VXUS Price</td>            <td>{fmt_price(d['vxus_price'])} &nbsp;({fmt_pct(d['vxus_chg_pct'])} today)</td></tr>
        <tr><td>VXUS 52-Wk High</td>       <td>{fmt_price(d['vxus_52wk_high'])}</td></tr>
        <tr><td>VXUS Drawdown from High</td><td class="{dd_color(d['vxus_drawdown'])}">{fmt_pct(d['vxus_drawdown'], plus=False)}</td></tr>
        <tr><td>VXUS YTD Return</td>       <td class="{val_color(d['vxus_ytd'])}">{fmt_pct(d['vxus_ytd'])}</td></tr>
        <tr><td>VXUS P/E (Trailing)</td>   <td>{fmt_pe(d['vxus_pe'])}</td></tr>
        <tr><td>P/E Spread</td>            <td>{pe_gap_str}</td></tr>
      </tbody>
    </table>
    <div class="bt" style="margin-top:10px;">P/E spread and return data are context only. <strong>No allocation changes are made based on this data.</strong> The 60/40 split already reflects a deliberate international tilt given VXUS's structural valuation discount.</div>
  </div>
</div>

<!-- 5: NOISE -->
<div class="sec">
  <div class="sec-h">
    <div class="sec-n">5</div>
    <div class="sec-t">Noise to Ignore</div>
    <span class="pill pill-red">Do Not Act On These</span>
  </div>
  <div class="sec-b">
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"ETFs are near 52-week highs — wait for a pullback."</strong> Proximity to highs is never a reason to pause or delay regular contributions.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"VXUS is outperforming VTI — overweight international."</strong> Return differentials do not trigger allocation shifts. 60/40 is fixed until the January rebalance.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"Sector or macro narratives suggest tilting the portfolio."</strong> Sector trends and earnings momentum are not inputs to this methodology.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"VIX is low — hold cash and wait for a better entry."</strong> VIX level only governs lump sum sizing. Regular contributions always execute in full.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"Geopolitical uncertainty — consider reducing equity exposure."</strong> Macro news does not pause contributions or change allocation outside the VIX lump sum rule.</div></div>
  </div>
</div>

<div class="footer">
  ⚠️ Educational framework only — not personalized financial advice. Consult a licensed financial advisor before making investment decisions.<br>
  Data via Yahoo Finance · Auto-generated by GitHub Actions · Methodology v2
</div>

</div>
</body>
</html>"""


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    et  = pytz.timezone("America/New_York")
    now = datetime.datetime.now(et)

    session_label = "Market Open Update · 9:30 AM ET" if now.hour < 12 else "Market Close Update · 4:00 PM ET"
    date_str      = now.strftime("%B %-d, %Y")

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S %Z')}] Fetching data...")
    data = fetch_data()
    print(f"  VTI  {data['vti_price']}  ({data['vti_chg_pct']:+.2f}%)")
    print(f"  VXUS {data['vxus_price']} ({data['vxus_chg_pct']:+.2f}%)")
    print(f"  VIX  {data['vix_level']}")

    html     = render_html(data, date_str, session_label)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(base_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html written.")

    snapshot = {**data, "generated_at": now.isoformat(), "session": session_label}
    with open(os.path.join(base_dir, "latest_data.json"), "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print("latest_data.json written.")


if __name__ == "__main__":
    main()
