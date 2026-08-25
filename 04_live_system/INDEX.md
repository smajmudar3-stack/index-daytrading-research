# Live system

The 53 modules behind the dashboard on port 8094. `gap_dashboard.py` is the entry point; `signal_weights.py` is the single source of truth for how much each signal counts.

| file | what it does |
|---|---|
| `ai_desk.py` | ai_desk.py — the AI desk strategist (Fable 5, Opus fallback). Reads the WHOLE board — 0DTE regime, |
| `ai_trader.py` | ai_trader.py — the AGENTIC trader. Fable 5 ingests the whole board and outputs concrete trade |
| `analyst.py` | analyst.py — Fable 5 desk-analyst for the gap-and-go scanner. |
| `audit_dash.py` | Audit every number the dashboard shows against an independent source. |
| `blackswan_panel.py` | Black Swan tab — stocks coiled for a big move, and the cheap convex play on them. |
| `build_snapshot.py` | build_snapshot.py — computes the live day-trading snapshot -> data/snapshot.json. |
| `committee.py` | committee.py — an adversarial second opinion before any trade reaches the book. |
| `condor.py` | condor.py — accurate 0DTE iron-condor play, gated by gamma regime + time of day. |
| `confluence.py` | confluence.py — does SIGNAL CONFLUENCE (how many validated bullish signals agree) improve win-rate? |
| `daily_edges.py` | Day-trading edges testable on 21 years of daily OHLC (SPY/QQQ = SPX/NDX proxies). |
| `dashboard.py` | dashboard.py — SPX/NDX day-trading dashboard (stdlib http, no deps). Port 8091. |
| `direction_signals.py` | direction_signals.py — hunt for MORE high-conviction BULLISH and BEARISH day signals. |
| `edge_panel.py` | Structure Edge panel — every structure's REAL backtested evidence, on the board. |
| `edge_rules.py` | edge_rules.py — the four things that survived testing, with live state. |
| `fetch_minutes.py` | fetch_minutes.py — pull 1-minute bars from Polygon for additional symbols. |
| `final_system.py` | Final merged index system with CLEAN locked weights (rounded, not overfit to exact |
| `gap_dashboard.py` | gap_dashboard.py — unified Day + Swing signal-giver. Port 8094. |
| `gap_gamma.py` | gap_gamma.py — does the OVERNIGHT GAP interact with gamma regime to predict intraday direction? |
| `gap_scanner.py` | gap_scanner.py — the LIVE gap-and-go signal-giver (the validated edge). |
| `gex_directional.py` | gex_directional.py — Does the opening drive CONTINUE to the close (naked long call/put |
| `gex_periscope.py` | gex_periscope.py — LIVE per-strike dealer-gamma PERISCOPE (magnet/reversal levels). |
| `gex_regime.py` | gex_regime.py — Does dealer gamma regime condition INTRADAY 0DTE behavior? |
| `gex_signal.py` | gex_signal.py — LIVE 0DTE dealer-gamma REGIME signal (the real, 15-year-robust edge). |
| `graduation.py` | graduation.py — the pre-registered paper→live graduation gate, and an honest projection of whether |
| `growth_plan.py` | growth_plan.py — the account growth curve the agent trades toward, and adaptive aggression. |
| `intraday_live.py` | intraday_live.py — live intraday pattern scanner for the signal-giver. |
| `lessons.py` | lessons.py — the self-improving loop (cobriensr/Options-Strike-Calculator pattern, RESEARCH_BOTS.md). |
| `macro_panel.py` | Macro Context tab — the rate/credit backdrop the swing signal ignores. |
| `master_call.py` | master_call.py — THE master decision, made by Fable 5, rendered at the top of the dashboard. |
| `mes_dashboard.py` | mes_dashboard.py — merged MES/MNQ system dashboard (stdlib http). Port 8092. |
| `monitor.py` | monitor.py — minute-level watch over OPEN 0DTE positions. |
| `option_pricer.py` | option_pricer.py — real option quotes and multi-leg structure pricing. |
| `positions.py` | positions.py — live position manager for YOUR actual trades. |
| `refresh_signal.py` | Keep the advisor's SIGNAL inputs fresh. |
| `risk_gates.py` | risk_gates.py — the HARD pre-trade risk layer that sits in front of the agent's decisions. |
| `rules.py` | rules.py — the VALIDATED trade rules, as executable code. |
| `scan_all.py` | Combined runner for the signals dashboard: gap-and-go (+analyst) every call; swing only |
| `scorecard.py` | One scorecard for every tab: what it said, what happened, was it right. |
| `session.py` | session.py — ONE definition of when the system is awake. Everything else imports this. |
| `signal_tracker.py` | signal_tracker.py — accountability + P&L for the SPX 0DTE reconciled signal. |
| `signal_weights.py` | ONE weighting authority for every tab. |
| `signals_all.py` | Run all signal engines for the dashboard (launchd + /refresh point here). |
| `sizing.py` | sizing.py — turn a priced structure into an actual contract count for THIS account. |
| `sizing_curve.py` | sizing_curve.py — how hard can this edge actually be sized before it destroys itself? |
| `sleeves.py` | sleeves.py — capital split into independent sleeves, each with its own risk budget and cadence. |
| `spx_ndx_advisor.py` | SPX / NDX strategy advisor — what to trade, when, at which strikes, and why. |
| `swing_signals.py` | swing_signals.py — swing-trade signal-giver (days-to-weeks). The honest research chain: |
| `ticket.py` | ticket.py — turn the validated setup into an exact, ready-to-place order ticket, and record the fill. |
| `tickets.py` | tickets.py — concrete, executable orders from the signals that survived testing. |
| `uw_archive.py` | uw_archive.py — capture Unusual Whales order flow every scan cycle so it becomes BACKTESTABLE. |
| `uw_calibrate.py` | Let each endpoint EARN its weight from realised accuracy. |
| `uw_client.py` | uw_client.py — Unusual Whales integration (READY TO ACTIVATE — just add your API key). |
| `uw_endpoints.py` | Full Unusual Whales endpoint registry, and the screener built on it. |
| `watch_ndx.py` | watch_ndx.py — one-off close watcher for the user's NDX condor short call at 29825. |
| `zero_dte.py` | 0DTE research — the intraday excursion distribution that drives every 0DTE P&L. |

**55 files.**
