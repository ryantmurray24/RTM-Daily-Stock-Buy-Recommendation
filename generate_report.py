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

def fetch_market_data():
    tickers = yf.Tickers("VTI VXUS ^VIX")
    vti  = tickers.tickers["VTI"]
    vxus = tickers.tickers["VXUS"]
    vix  = tickers.tickers["^VIX"]

    vti_fast  = vti.fast_info
    vxus_fast = vxus.fast_info
    vix_fast  = vix.fast_info

    vti_price  = round(vti_fast.last_price,  2)
    vxus_price = round(vxus_fast.last_price, 2)
    vix_level  = round(vix_fast.last_price,  2)

    vti_52wk_high  = round(vti_fast.year_high,  2)
    vxus_52wk_high = round(vxus_fast.year_high, 2)
    vti_prev       = round(vti_fast.previous_close,  2)
    vxus_prev      = round(vxus_fast.previous_close, 2)
    vix_prev       = round(vix_fast.previous_close,  2)

    def pct(p, prev): return round(((p - prev) / prev) * 100, 2) if prev else 0.0

    vti_chg  = pct(vti_price,  vti_prev)
    vxus_chg = pct(vxus_price, vxus_prev)
    vix_chg  = pct(vix_level,  vix_prev)

    vti_dd  = round(((vti_price  - vti_52wk_high)  / vti_52wk_high)  * 100, 2)
    vxus_dd = round(((vxus_price - vxus_52wk_high) / vxus_52wk_high) * 100, 2)

    try:
        vti_pe  = round(float(vti.info.get("trailingPE")),  1)
    except Exception:
        vti_pe  = None
    try:
        vxus_pe = round(float(vxus.info.get("trailingPE")), 1)
    except Exception:
        vxus_pe = None

    try:
        et  = pytz.timezone("America/New_York")
        now = datetime.datetime.now(et)
        jan2      = datetime.datetime(now.year, 1, 2).strftime("%Y-%m-%d")
        today_str = now.strftime("%Y-%m-%d")
        vh  = vti.history(start=jan2,  end=today_str)
        vxh = vxus.history(start=jan2, end=today_str)
        vti_ytd  = round(((vti_price  - vh["Close"].iloc[0])  / vh["Close"].iloc[0])  * 100, 1) if not vh.empty  else None
        vxus_ytd = round(((vxus_price - vxh["Close"].iloc[0]) / vxh["Close"].iloc[0]) * 100, 1) if not vxh.empty else None
    except Exception:
        vti_ytd = vxus_ytd = None

    return {
        "vti_price": vti_price, "vti_prev": vti_prev, "vti_chg_pct": vti_chg,
        "vti_52wk_high": vti_52wk_high, "vti_drawdown": vti_dd,
        "vti_pe": vti_pe, "vti_ytd": vti_ytd,
        "vxus_price": vxus_price, "vxus_prev": vxus_prev, "vxus_chg_pct": vxus_chg,
        "vxus_52wk_high": vxus_52wk_high, "vxus_drawdown": vxus_dd,
        "vxus_pe": vxus_pe, "vxus_ytd": vxus_ytd,
        "vix_level": vix_level, "vix_prev": vix_prev, "vix_chg_pct": vix_chg,
    }


# ── PORTFOLIO ──────────────────────────────────────────────────────────────────

def load_portfolio():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "portfolio.json")
    with open(path) as f:
        return json.load(f)

def calc_portfolio(portfolio):
    """Returns allocation totals, drift, and rebalance action."""
    total_us    = 0.0
    total_intl  = 0.0
    total_other = 0.0
    rows = []  # per-account summary

    # Account type priority for rebalancing
    type_order = {"401k": 0, "roth_ira": 1, "taxable": 2}

    for acct in portfolio["accounts"]:
        acct_us    = sum(p["value"] for p in acct["positions"] if p["role"] == "us_equity")
        acct_intl  = sum(p["value"] for p in acct["positions"] if p["role"] == "intl_equity")
        acct_other = sum(p["value"] for p in acct["positions"] if p["role"] == "other")
        acct_total = acct_us + acct_intl
        rows.append({
            "name":  acct["name"],
            "type":  acct["type"],
            "us":    acct_us,
            "intl":  acct_intl,
            "other": acct_other,
            "total": acct_total,
        })
        total_us    += acct_us
        total_intl  += acct_intl
        total_other += acct_other

    total = total_us + total_intl
    us_pct   = (total_us   / total * 100) if total > 0 else 60.0
    intl_pct = (total_intl / total * 100) if total > 0 else 40.0
    drift    = us_pct - 60.0

    # Rebalance action
    target_us   = total * 0.60
    target_intl = total * 0.40
    sell_us     = total_us   - target_us
    buy_intl    = target_intl - total_intl

    # Which accounts to rebalance in
    abs_drift = abs(drift)
    if abs_drift >= 10:
        rebal_note = "Rebalance in tax-advantaged accounts first (401k → Roth IRA), then taxable accounts (drift >10%)."
    elif abs_drift >= 5:
        rebal_note = "Rebalance in tax-advantaged accounts only (401k → Roth IRA). Drift in taxable is below 10% threshold."
    else:
        rebal_note = None

    return {
        "total_us":    total_us,
        "total_intl":  total_intl,
        "total_other": total_other,
        "total":       total,
        "us_pct":      us_pct,
        "intl_pct":    intl_pct,
        "drift":       drift,
        "sell_us":     sell_us,
        "buy_intl":    buy_intl,
        "rebal_note":  rebal_note,
        "rows":        rows,
        "last_updated": portfolio.get("last_updated", "unknown"),
    }


# ── HELPERS ────────────────────────────────────────────────────────────────────

def fp(v):  return f"${v:,.2f}" if v is not None else "N/A"
def fpe(v): return f"{v:.1f}×"  if v is not None else "N/A"

def fpct(v, plus=True):
    if v is None: return "N/A"
    s = "+" if (v > 0 and plus) else ""
    return f"{s}{v:.2f}%"

def vc(v):
    if v is None: return ""
    return "val-green" if v >= 0 else "val-red"

def ddc(v):
    if v is None: return ""
    if v < -5: return "val-red"
    if v < 0:  return "val-amber"
    return "val-green"

def get_lump_rule(vix):
    if vix < 20:
        return {"zone": "below_20", "deploy": 50, "hold": 50,
                "label": "Deploy 50% now · Hold 50% for next contribution cycle",
                "color": "green", "pill": f"VIX {vix:.1f} → Deploy 50% Rule"}
    elif vix <= 30:
        return {"zone": "20_to_30", "deploy": 75, "hold": 25,
                "label": "Deploy 75% now · Hold 25% in reserve",
                "color": "amber", "pill": f"VIX {vix:.1f} → Deploy 75% Rule"}
    else:
        return {"zone": "above_30", "deploy": 100, "hold": 0,
                "label": "Deploy 100% immediately — elevated fear is a historically favorable entry",
                "color": "red", "pill": f"VIX {vix:.1f} → Deploy 100% — High Fear Zone"}


# ── HTML RENDER ────────────────────────────────────────────────────────────────

def render_html(md, pf, date_str, session_label):
    vix  = md["vix_level"]
    lump = get_lump_rule(vix)

    vix_pct = min(max(vix / 45 * 100, 2), 98)
    z_green = "active" if lump["zone"] == "below_20" else ""
    z_amber = "active" if lump["zone"] == "20_to_30" else ""
    z_red   = "active" if lump["zone"] == "above_30" else ""
    ntg = "&nbsp;<span class='af'>NOW</span>" if z_green else ""
    nta = "&nbsp;<span class='af'>NOW</span>" if z_amber else ""
    ntr = "&nbsp;<span class='af'>NOW</span>" if z_red   else ""

    pill_map = {"green": "pill-green", "amber": "pill-amber", "red": "pill-red"}
    lump_pill = pill_map[lump["color"]]

    pe_gap = round(md["vti_pe"] - md["vxus_pe"], 1) if md["vti_pe"] and md["vxus_pe"] else None
    pe_gap_str = f"{pe_gap:.1f}× cheaper internationally" if pe_gap else "N/A"

    vtc  = "tc-green" if md["vti_chg_pct"]  >= 0 else "tc-red"
    vxtc = "tc-green" if md["vxus_chg_pct"] >= 0 else "tc-red"
    vitc = "tc-green" if md["vix_chg_pct"]  <= 0 else "tc-red"

    # Rebalance section
    drift     = pf["drift"]
    abs_drift = abs(drift)
    drift_str = f"{drift:+.1f}%"

    if abs_drift < 5:
        rebal_pill    = "pill-green"
        rebal_pill_lbl = "✅ On Target — No Action"
        rebal_status  = f'<div class="rebal-ok">✅ <strong>Drift {drift_str} — within 5% threshold.</strong> No rebalancing needed. Next check: January 2027.</div>'
    else:
        rebal_pill    = "pill-amber" if abs_drift < 10 else "pill-red"
        rebal_pill_lbl = f"⚠️ Drift {drift_str} — Action in January"
        acct_note = pf["rebal_note"] or ""
        rebal_status = f'''
        <div class="rebal-warn">
          ⚠️ <strong>Drift {drift_str} — Rebalancing required in January 2027.</strong><br><br>
          To reach 60/40 target:<br>
          &nbsp;• Sell <strong>{fp(pf["sell_us"])}</strong> of US equity<br>
          &nbsp;• Buy <strong>{fp(pf["buy_intl"])}</strong> of Intl equity<br><br>
          {acct_note}
        </div>'''

    # Account breakdown table rows
    type_labels = {"roth_ira": "Roth IRA", "401k": "401k", "taxable": "Taxable"}
    acct_rows = ""
    for r in pf["rows"]:
        at   = total = r["us"] + r["intl"]
        us_p = f"{r['us']/at*100:.1f}%" if at > 0 else "—"
        ix_p = f"{r['intl']/at*100:.1f}%" if at > 0 else "—"
        acct_rows += f"""
        <tr>
          <td><strong>{r['name']}</strong><br><span style="font-size:10px;color:#888;">{type_labels.get(r['type'], r['type'])}</span></td>
          <td>{fp(r['us'])}<br><span style="font-size:10px;color:#888;">{us_p}</span></td>
          <td>{fp(r['intl'])}<br><span style="font-size:10px;color:#888;">{ix_p}</span></td>
          <td>{fp(r['us'] + r['intl'])}</td>
        </tr>"""

    us_bar_w   = min(max(pf["us_pct"],   2), 96)
    intl_bar_w = 100 - us_bar_w

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Macro-Core Report · {date_str}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:#f4f5f7;color:#111;padding:20px;font-size:13px;line-height:1.5;}}
  .wrap{{max-width:900px;margin:0 auto;}}
  .hdr{{background:#fff;border-radius:8px;padding:16px 22px;margin-bottom:12px;border:1px solid #e0e0e0;display:flex;justify-content:space-between;align-items:center;}}
  .hdr h1{{font-size:17px;font-weight:800;}} .hdr p{{font-size:12px;color:#666;margin-top:2px;}}
  .hdr-r{{text-align:right;}} .hdr-r .dt{{font-size:14px;font-weight:800;}} .hdr-r .sess{{font-size:11px;color:#888;}} .hdr-r .upd{{font-size:10px;color:#bbb;}}
  .upd-link{{font-size:11px;color:#2563eb;text-decoration:none;font-weight:600;}}
  .strip{{background:#111;border-radius:8px;padding:12px 20px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:0;margin-bottom:12px;}}
  .ti{{text-align:center;padding:0 12px;}} .ti+.ti{{border-left:1px solid #2a2a2a;}}
  .ti-sym{{font-size:10px;font-weight:700;letter-spacing:1px;color:#666;margin-bottom:2px;}}
  .ti-px{{font-size:20px;font-weight:800;color:#fff;}}
  .ti-chg{{font-size:11px;font-weight:600;margin-top:2px;}}
  .tc-green{{color:#4ade80;}} .tc-red{{color:#f87171;}} .tc-amber{{color:#fbbf24;}}
  .sec{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:10px;overflow:hidden;}}
  .sec-h{{display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid #ebebeb;background:#fafafa;}}
  .sec-n{{font-size:11px;font-weight:800;color:#fff;background:#111;border-radius:50%;width:22px;height:22px;flex-shrink:0;display:flex;align-items:center;justify-content:center;}}
  .sec-t{{font-size:13px;font-weight:700;flex:1;}}
  .sec-b{{padding:14px 16px;}}
  .pill{{display:inline-block;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;}}
  .pill-green{{background:#e6f4ea;color:#1a6b35;border:1px solid #86c99a;}}
  .pill-amber{{background:#fef9e6;color:#7a5800;border:1px solid #e8c96a;}}
  .pill-red{{background:#fde8e8;color:#8b0000;border:1px solid #f5b0b0;}}
  .pill-grey{{background:#f0f0f0;color:#555;border:1px solid #ccc;}}
  .sl{{font-size:13px;font-weight:700;margin-bottom:6px;}}
  .green{{color:#1a6b35;}} .amber{{color:#7a5800;}} .red{{color:#8b0000;}} .grey{{color:#555;}}
  .bt{{font-size:12px;color:#444;line-height:1.6;}} .bt strong{{color:#111;}}
  .vix-track{{height:12px;border-radius:6px;position:relative;margin:10px 0 4px;background:linear-gradient(to right,#bbf7d0 0%,#bbf7d0 33%,#fde68a 33%,#fde68a 66%,#fecaca 66%,#fecaca 100%);border:1px solid #ddd;}}
  .vix-dot{{position:absolute;top:-4px;width:20px;height:20px;border-radius:50%;background:#111;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3);transform:translateX(-50%);}}
  .vix-lbl{{display:flex;justify-content:space-between;font-size:10px;color:#888;margin-bottom:10px;}}
  .vix-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;}}
  .vr{{border-radius:6px;padding:10px 12px;border:1.5px solid;font-size:11px;line-height:1.5;}}
  .vr.active{{border-width:2.5px;box-shadow:0 0 0 2px rgba(0,0,0,.07);}}
  .vr.vg{{background:#f0faf2;border-color:#2a9d8f;}} .vr.va{{background:#fffbf0;border-color:#d4a017;}} .vr.vr2{{background:#fff5f5;border-color:#cc3333;}}
  .rr{{font-weight:800;font-size:12px;margin-bottom:3px;}} .ra{{font-weight:700;}}
  .vg .rr,.vg .ra{{color:#1a7a6e;}} .va .rr,.va .ra{{color:#9a6700;}} .vr2 .rr,.vr2 .ra{{color:#cc0000;}}
  .af{{font-size:9px;font-weight:700;background:#111;color:#fff;padding:1px 5px;border-radius:3px;margin-left:4px;vertical-align:middle;}}
  .tbl{{width:100%;border-collapse:collapse;margin-top:6px;}}
  .tbl thead tr{{border-bottom:2px solid #e0e0e0;}}
  .tbl th{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;padding:5px 8px;text-align:left;}}
  .tbl td{{font-size:12px;padding:8px 8px;border-bottom:1px solid #f0f0f0;vertical-align:top;}}
  .tbl tr:last-child td{{border-bottom:none;}}
  .tbl td:first-child{{color:#444;}}
  .val-green{{color:#1a7a38;font-weight:700;}} .val-red{{color:#cc2200;font-weight:700;}} .val-amber{{color:#9a6700;font-weight:700;}}
  .alloc-bar{{display:flex;height:24px;border-radius:4px;overflow:hidden;margin:8px 0;}}
  .alloc-us{{background:#2563eb;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;}}
  .alloc-intl{{background:#16a34a;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;}}
  .rebal-ok{{background:#f0faf2;border:1px solid #86c99a;border-left:4px solid #1a6b35;border-radius:5px;padding:10px 12px;font-size:12px;color:#1a4d28;margin-top:10px;line-height:1.6;}}
  .rebal-warn{{background:#fff8e6;border:1px solid #e8c96a;border-left:4px solid #d4a017;border-radius:5px;padding:10px 12px;font-size:12px;color:#5a3e00;margin-top:10px;line-height:1.7;}}
  .ni{{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #f0f0f0;font-size:12px;}}
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
    <div class="upd">Auto-updated · <a href="update_portfolio.html" class="upd-link">Update Balances →</a></div>
  </div>
</div>

<div class="strip">
  <div class="ti"><div class="ti-sym">VTI</div><div class="ti-px">{fp(md['vti_price'])}</div><div class="ti-chg {vtc}">{fpct(md['vti_chg_pct'])} · 52wk H: {fp(md['vti_52wk_high'])}</div></div>
  <div class="ti"><div class="ti-sym">VXUS</div><div class="ti-px">{fp(md['vxus_price'])}</div><div class="ti-chg {vxtc}">{fpct(md['vxus_chg_pct'])} · 52wk H: {fp(md['vxus_52wk_high'])}</div></div>
  <div class="ti"><div class="ti-sym">VIX</div><div class="ti-px tc-amber">{vix:.2f}</div><div class="ti-chg {vitc}">{fpct(md['vix_chg_pct'])} · Prev: {md['vix_prev']:.2f}</div></div>
</div>

<!-- 1: CONTRIBUTIONS -->
<div class="sec">
  <div class="sec-h"><div class="sec-n">1</div><div class="sec-t">Regular Contribution Status</div><span class="pill pill-green">✅ Execute as Normal</span></div>
  <div class="sec-b">
    <div class="sl green">Scheduled contributions proceed on time, at full amount — no conditions.</div>
    <div class="bt">Regular monthly contributions are never held back or delayed based on price, VIX, moving averages, RSI, or proximity to highs. <strong>No signal is required and no signal can pause it.</strong></div>
  </div>
</div>

<!-- 2: LUMP SUM -->
<div class="sec">
  <div class="sec-h"><div class="sec-n">2</div><div class="sec-t">Lump Sum Deployment Status</div><span class="pill {lump_pill}">{lump['pill']}</span></div>
  <div class="sec-b">
    <div class="sl {lump['color']}">{lump['label']}</div>
    <div class="vix-track"><div class="vix-dot" style="left:{vix_pct:.1f}%;"></div></div>
    <div class="vix-lbl"><span>0 — Low Fear</span><span>20</span><span>30</span><span>45+ Max Fear</span></div>
    <div class="vix-grid">
      <div class="vr vg {z_green}"><div class="rr">VIX &lt; 20{ntg}</div><div class="ra">Deploy 50% immediately</div><div style="font-size:11px;color:#555;margin-top:3px;">Hold 50% for next cycle</div></div>
      <div class="vr va {z_amber}"><div class="rr">VIX 20–30{nta}</div><div class="ra">Deploy 75% immediately</div><div style="font-size:11px;color:#555;margin-top:3px;">Hold 25% in reserve</div></div>
      <div class="vr vr2 {z_red}"><div class="rr">VIX &gt; 30{ntr}</div><div class="ra">Deploy 100% immediately</div><div style="font-size:11px;color:#555;margin-top:3px;">Elevated fear = favorable entry</div></div>
    </div>
    <div class="bt">Applies to <strong>unscheduled capital only</strong> — bonuses, ESPP, tax refunds, unspent buffer. Maintain 60/40. Regular contributions unaffected by VIX.</div>
  </div>
</div>

<!-- 3: REBALANCING — REAL DATA -->
<div class="sec">
  <div class="sec-h"><div class="sec-n">3</div><div class="sec-t">Rebalancing Status</div><span class="pill {rebal_pill}">{rebal_pill_lbl}</span></div>
  <div class="sec-b">
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#888;margin-bottom:4px;">
      <span>US Equity: <strong>{pf['us_pct']:.1f}%</strong></span>
      <span>Intl Equity: <strong>{pf['intl_pct']:.1f}%</strong></span>
    </div>
    <div class="alloc-bar">
      <div class="alloc-us"   style="width:{us_bar_w:.1f}%;">{pf['us_pct']:.1f}%</div>
      <div class="alloc-intl" style="width:{intl_bar_w:.1f}%;">{pf['intl_pct']:.1f}%</div>
    </div>
    <div style="font-size:11px;color:#888;margin-bottom:10px;">Target: 60% US / 40% Intl &nbsp;·&nbsp; Drift: <strong style="color:{'#cc2200' if abs_drift>=5 else '#1a7a38'};">{drift_str}</strong></div>

    <table class="tbl">
      <thead><tr><th>Account</th><th>US Equity</th><th>Intl Equity</th><th>Total</th></tr></thead>
      <tbody>
        {acct_rows}
        <tr style="border-top:2px solid #e0e0e0;">
          <td><strong>Total</strong></td>
          <td><strong>{fp(pf['total_us'])}</strong></td>
          <td><strong>{fp(pf['total_intl'])}</strong></td>
          <td><strong>{fp(pf['total'])}</strong></td>
        </tr>
      </tbody>
    </table>
    {rebal_status}
    <div style="font-size:11px;color:#aaa;margin-top:8px;">Balances last updated: {pf['last_updated']} · <a href="update_portfolio.html" style="color:#2563eb;">Update now →</a></div>
  </div>
</div>

<!-- 4: VALUATION -->
<div class="sec">
  <div class="sec-h"><div class="sec-n">4</div><div class="sec-t">Valuation Context</div><span class="pill pill-grey">ℹ️ Informational Only</span></div>
  <div class="sec-b">
    <table class="tbl">
      <tbody>
        <tr><td>VTI Price</td>              <td>{fp(md['vti_price'])} ({fpct(md['vti_chg_pct'])} today)</td></tr>
        <tr><td>VTI Drawdown from High</td> <td class="{ddc(md['vti_drawdown'])}">{fpct(md['vti_drawdown'],plus=False)}</td></tr>
        <tr><td>VTI YTD Return</td>         <td class="{vc(md['vti_ytd'])}">{fpct(md['vti_ytd'])}</td></tr>
        <tr><td>VTI P/E (Trailing)</td>     <td>{fpe(md['vti_pe'])}</td></tr>
        <tr><td>VXUS Price</td>             <td>{fp(md['vxus_price'])} ({fpct(md['vxus_chg_pct'])} today)</td></tr>
        <tr><td>VXUS Drawdown from High</td><td class="{ddc(md['vxus_drawdown'])}">{fpct(md['vxus_drawdown'],plus=False)}</td></tr>
        <tr><td>VXUS YTD Return</td>        <td class="{vc(md['vxus_ytd'])}">{fpct(md['vxus_ytd'])}</td></tr>
        <tr><td>VXUS P/E (Trailing)</td>    <td>{fpe(md['vxus_pe'])}</td></tr>
        <tr><td>P/E Spread</td>             <td>{pe_gap_str}</td></tr>
      </tbody>
    </table>
    <div class="bt" style="margin-top:10px;">P/E spread and return data are context only. <strong>No allocation changes are made based on this data.</strong></div>
  </div>
</div>

<!-- 5: NOISE -->
<div class="sec">
  <div class="sec-h"><div class="sec-n">5</div><div class="sec-t">Noise to Ignore</div><span class="pill pill-red">Do Not Act On These</span></div>
  <div class="sec-b">
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"ETFs are near highs — wait for a pullback."</strong> Proximity to highs never pauses contributions.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"VXUS is outperforming VTI — overweight international."</strong> Return differentials don't shift the 60/40 allocation.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"Sector or macro narratives suggest tilting the portfolio."</strong> Not an input to this methodology.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"VIX is low — hold cash for a better entry."</strong> VIX only governs lump sum sizing. Contributions always execute in full.</div></div>
    <div class="ni"><div class="nx">✕</div><div class="nt"><strong>"Geopolitical uncertainty — reduce equity exposure."</strong> Macro news doesn't pause contributions or change allocation.</div></div>
  </div>
</div>

<div class="footer">
  ⚠️ Educational framework only — not personalized financial advice. Consult a licensed financial advisor.<br>
  Data via Yahoo Finance · GitHub Actions · Methodology v2
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

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S %Z')}] Fetching market data...")
    md = fetch_market_data()
    print(f"  VTI  {md['vti_price']}  ({md['vti_chg_pct']:+.2f}%)")
    print(f"  VXUS {md['vxus_price']} ({md['vxus_chg_pct']:+.2f}%)")
    print(f"  VIX  {md['vix_level']}")

    print("Loading portfolio...")
    portfolio = load_portfolio()
    pf = calc_portfolio(portfolio)
    print(f"  US   {pf['total_us']:,.2f} ({pf['us_pct']:.1f}%)")
    print(f"  Intl {pf['total_intl']:,.2f} ({pf['intl_pct']:.1f}%)")
    print(f"  Drift {pf['drift']:+.1f}%")

    html     = render_html(md, pf, date_str, session_label)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(base_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html written.")

    snapshot = {**md, "portfolio": pf, "generated_at": now.isoformat(), "session": session_label}
    with open(os.path.join(base_dir, "latest_data.json"), "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print("latest_data.json written.")


if __name__ == "__main__":
    main()
