# Manifest

**Regenerated 2026-08-24 from the actual tree.** Every file below was enumerated with `git ls-files --cached --others --exclude-standard`, so this list cannot name a file that does not exist or miss one that does. Line counts are read from the files, not carried forward.

The previous version of this file claimed **200 files total** and was stale by seven: `RUNBOOK.md`, `WHAT_WORKS.md`, `WHAT_FAILED.md`, `METHODOLOGY_TRAPS.md`, `DATA.md`, `INDEX.md` and `build_indexes.py` all existed and none was listed.

**What is deliberately not here.** The 16 GB of market data (see [06_data_guide/DATA.md](06_data_guide/DATA.md)), the virtualenv, `__pycache__`, build metadata and `.env`. All are gitignored, and none is reconstructible from this repo.

**245 files, 56,999 lines.**

## Repo root

*8 files, 836 lines*

| file | lines | size |
|---|---:|---:|
| `.env.example` | 18 | 810 B |
| `.gitignore` | 20 | 251 B |
| `AGENTS.md` | 143 | 8 KB |
| `CLAUDE.md` | 143 | 8 KB |
| `MANIFEST.md` | 349 | 11 KB |
| `README.md` | 108 | 6 KB |
| `pyproject.toml` | 44 | 980 B |
| `requirements.txt` | 11 | 261 B |

## 01_START_HERE — orientation

*5 files, 1,487 lines*

| file | lines | size |
|---|---:|---:|
| `ENGINE.md` | 237 | 14 KB |
| `HANDOFF.md` | 958 | 58 KB |
| `MES_STRATEGY.md` | 85 | 5 KB |
| `README.md` | 128 | 6 KB |
| `RUNBOOK.md` | 79 | 3 KB |

## 02_findings — the current verdicts

*5 files, 674 lines*

| file | lines | size |
|---|---:|---:|
| `FINDINGS.md` | 209 | 13 KB |
| `FINDINGS_BLACKSWAN.md` | 207 | 11 KB |
| `METHODOLOGY_TRAPS.md` | 94 | 4 KB |
| `WHAT_FAILED.md` | 75 | 3 KB |
| `WHAT_WORKS.md` | 89 | 4 KB |

## 03_research — literature and repo sweeps

*27 files, 17,948 lines*

| file | lines | size |
|---|---:|---:|
| `INDEX.md` | 87 | 14 KB |
| `RESEARCH_0DTE_EDGE.md` | 642 | 47 KB |
| `RESEARCH_BLACKSWAN.md` | 652 | 92 KB |
| `RESEARCH_BLOWUPS.md` | 718 | 46 KB |
| `RESEARCH_BOTS.md` | 74 | 13 KB |
| `RESEARCH_CONDOR_BUTTERFLY.md` | 1,020 | 71 KB |
| `RESEARCH_COSTS.md` | 632 | 33 KB |
| `RESEARCH_DIRECTION.md` | 1,065 | 68 KB |
| `RESEARCH_EXOTIC_STRUCTURES.md` | 795 | 49 KB |
| `RESEARCH_FEES.md` | 494 | 34 KB |
| `RESEARCH_GITHUB_RETURNS.md` | 243 | 62 KB |
| `RESEARCH_GITHUB_SWEEP.md` | 665 | 44 KB |
| `RESEARCH_MACRO_SWING.md` | 823 | 50 KB |
| `RESEARCH_MANAGEMENT.md` | 388 | 42 KB |
| `RESEARCH_MOVE_PREDICTION.md` | 976 | 63 KB |
| `RESEARCH_OPTIONS_EXPRESSION.md` | 1,089 | 63 KB |
| `RESEARCH_PAPERS_SWEEP.md` | 540 | 38 KB |
| `RESEARCH_REALCHAIN_REPOS.md` | 479 | 27 KB |
| `RESEARCH_RUIN_SIZING.md` | 923 | 46 KB |
| `RESEARCH_SPINOFFS.md` | 558 | 37 KB |
| `RESEARCH_SPINOFF_REPOS.md` | 438 | 28 KB |
| `RESEARCH_STRADDLE_STRANGLE.md` | 776 | 56 KB |
| `RESEARCH_SWING_ACADEMIC.md` | 1,312 | 98 KB |
| `RESEARCH_SWING_REPOS.md` | 522 | 35 KB |
| `RESEARCH_SWING_REPOS_MACRO.md` | 800 | 57 KB |
| `RESEARCH_TALEB.md` | 402 | 35 KB |
| `RESEARCH_UW_API.md` | 835 | 51 KB |

## 04_live_system — the dashboard and its engines

*53 files, 13,871 lines*

| file | lines | size |
|---|---:|---:|
| `INDEX.md` | 61 | 6 KB |
| `ai_desk.py` | 370 | 19 KB |
| `ai_trader.py` | 620 | 36 KB |
| `analyst.py` | 193 | 10 KB |
| `audit_dash.py` | 343 | 15 KB |
| `blackswan_panel.py` | 324 | 14 KB |
| `build_snapshot.py` | 197 | 9 KB |
| `committee.py` | 217 | 11 KB |
| `condor.py` | 127 | 6 KB |
| `confluence.py` | 52 | 3 KB |
| `daily_edges.py` | 75 | 3 KB |
| `dashboard.py` | 167 | 10 KB |
| `direction_signals.py` | 70 | 4 KB |
| `edge_panel.py` | 306 | 14 KB |
| `fetch_minutes.py` | 179 | 8 KB |
| `gap_dashboard.py` | 1,584 | 101 KB |
| `gap_gamma.py` | 53 | 3 KB |
| `gap_scanner.py` | 286 | 14 KB |
| `gex_directional.py` | 93 | 4 KB |
| `gex_periscope.py` | 427 | 22 KB |
| `gex_regime.py` | 100 | 6 KB |
| `gex_signal.py` | 376 | 21 KB |
| `graduation.py` | 413 | 21 KB |
| `growth_plan.py` | 135 | 7 KB |
| `intraday_live.py` | 105 | 5 KB |
| `lessons.py` | 196 | 9 KB |
| `macro_panel.py` | 207 | 9 KB |
| `master_call.py` | 315 | 17 KB |
| `mes_dashboard.py` | 243 | 13 KB |
| `mes_signals.py` | 116 | 4 KB |
| `monitor.py` | 68 | 2 KB |
| `option_pricer.py` | 291 | 12 KB |
| `positions.py` | 320 | 15 KB |
| `refresh_signal.py` | 79 | 3 KB |
| `risk_gates.py` | 663 | 32 KB |
| `rules.py` | 316 | 16 KB |
| `scan_all.py` | 259 | 11 KB |
| `scorecard.py` | 342 | 16 KB |
| `session.py` | 91 | 3 KB |
| `signal_tracker.py` | 392 | 20 KB |
| `signal_weights.py` | 139 | 6 KB |
| `signals_all.py` | 20 | 560 B |
| `sizing.py` | 179 | 9 KB |
| `sleeves.py` | 158 | 6 KB |
| `spx_ndx_advisor.py` | 474 | 22 KB |
| `swing_signals.py` | 442 | 23 KB |
| `ticket.py` | 241 | 12 KB |
| `uw_archive.py` | 157 | 6 KB |
| `uw_calibrate.py` | 218 | 8 KB |
| `uw_client.py` | 530 | 25 KB |
| `uw_endpoints.py` | 400 | 19 KB |
| `watch_ndx.py` | 60 | 2 KB |
| `zero_dte.py` | 82 | 4 KB |

## 05_studies — backtest and hunt harnesses

*48 files, 7,119 lines*

| file | lines | size |
|---|---:|---:|
| `INDEX.md` | 123 | 13 KB |
| `backtest_0dte_rules.py` | 943 | 48 KB |
| `backtest_daily.py` | 156 | 7 KB |
| `backtest_directional.py` | 115 | 5 KB |
| `backtest_intraday_dir.py` | 192 | 8 KB |
| `backtest_intraday_v2.py` | 203 | 9 KB |
| `backtest_swing_rules.py` | 845 | 40 KB |
| `bt_options.py` | 278 | 12 KB |
| `condor_backtest.py` | 74 | 3 KB |
| `dix_direction.py` | 69 | 4 KB |
| `dl_ensemble.py` | 152 | 7 KB |
| `final_system.py` | 40 | 2 KB |
| `fomc_research.py` | 89 | 5 KB |
| `hunt_base_rate.py` | 93 | 4 KB |
| `hunt_conditional.py` | 133 | 6 KB |
| `hunt_features.py` | 211 | 9 KB |
| `hunt_final.py` | 113 | 5 KB |
| `hunt_flow.py` | 124 | 6 KB |
| `hunt_horizons.py` | 48 | 2 KB |
| `hunt_indicators.py` | 149 | 7 KB |
| `hunt_master.py` | 159 | 6 KB |
| `hunt_patterns.py` | 200 | 11 KB |
| `hunt_patterns_spx.py` | 139 | 6 KB |
| `hunt_skew.py` | 137 | 7 KB |
| `hunt_strategy.py` | 149 | 6 KB |
| `intraday_macro.py` | 102 | 4 KB |
| `intraday_patterns.py` | 126 | 6 KB |
| `intraday_puts.py` | 77 | 4 KB |
| `live_path.py` | 34 | 1 KB |
| `merge_optimize.py` | 53 | 2 KB |
| `mes_overnight.py` | 86 | 4 KB |
| `mes_refine.py` | 67 | 3 KB |
| `minute_edges.py` | 97 | 4 KB |
| `momentum_intraday.py` | 97 | 4 KB |
| `momentum_scan.py` | 72 | 3 KB |
| `momentum_stocks.py` | 75 | 4 KB |
| `multi_edge.py` | 95 | 4 KB |
| `orb_proper.py` | 117 | 5 KB |
| `predictability.py` | 51 | 3 KB |
| `scalp_backtest.py` | 70 | 3 KB |
| `scalp_update.py` | 141 | 7 KB |
| `sizing_curve.py` | 121 | 5 KB |
| `validate_condor_real.py` | 133 | 5 KB |
| `validate_gapgo.py` | 61 | 2 KB |
| `validate_newlo_delta1.py` | 176 | 7 KB |
| `validate_newlo_real.py` | 169 | 7 KB |
| `vwap_momentum.py` | 85 | 3 KB |
| `vwap_reversion.py` | 80 | 3 KB |

## 05_studies/scripts — research harnesses

*70 files, 10,588 lines*

| file | lines | size |
|---|---:|---:|
| `_test_spinoff_regex.py` | 40 | 1 KB |
| `base_rate_check.py` | 107 | 4 KB |
| `bigmove_hunt.py` | 213 | 9 KB |
| `blackswan_flip.py` | 118 | 5 KB |
| `blackswan_select.py` | 136 | 6 KB |
| `blackswan_test.py` | 137 | 6 KB |
| `build_bundle.py` | 111 | 4 KB |
| `build_indexes.py` | 87 | 3 KB |
| `build_iv_features.py` | 111 | 5 KB |
| `bwb_and_box.py` | 164 | 8 KB |
| `cb_cboe_idx.py` | 109 | 4 KB |
| `cb_cndr_decay.py` | 49 | 2 KB |
| `cb_drag_crosscheck.py` | 153 | 7 KB |
| `cb_drag_deltawing.py` | 106 | 5 KB |
| `cb_spxw_costs.py` | 287 | 13 KB |
| `cb_spxw_manage.py` | 260 | 12 KB |
| `cb_weekly_condor.py` | 203 | 9 KB |
| `cb_weekly_manage.py` | 176 | 7 KB |
| `check_apis.py` | 89 | 3 KB |
| `combo_sweep.py` | 196 | 8 KB |
| `daily_engine.py` | 243 | 10 KB |
| `delta_hedged_gains.py` | 161 | 7 KB |
| `earnings_convexity.py` | 179 | 8 KB |
| `edge_budget.py` | 88 | 4 KB |
| `exotic_claims_test.py` | 240 | 11 KB |
| `exotic_structure_costs.py` | 263 | 11 KB |
| `fat_tail_test.py` | 126 | 6 KB |
| `leadlag_test.py` | 72 | 3 KB |
| `leadlag_trade.py` | 73 | 3 KB |
| `lit_search.py` | 59 | 3 KB |
| `macro_test.py` | 168 | 6 KB |
| `openalex_gap.py` | 74 | 3 KB |
| `openalex_lit.py` | 86 | 4 KB |
| `option_drag.py` | 71 | 3 KB |
| `option_edge.py` | 345 | 13 KB |
| `osap_spinoff_decay.py` | 105 | 4 KB |
| `osap_spinoff_ports.py` | 57 | 2 KB |
| `parse_ssi.py` | 55 | 2 KB |
| `preann_test.py` | 168 | 7 KB |
| `preswan_signals.py` | 134 | 6 KB |
| `range_matched.py` | 137 | 5 KB |
| `rate_pair_test.py` | 148 | 6 KB |
| `sa_spinoffs.py` | 49 | 2 KB |
| `signal_vs_base.py` | 167 | 7 KB |
| `smallcap_tails.py` | 167 | 7 KB |
| `spinoff_edgar_harvest.py` | 372 | 16 KB |
| `spinoff_etf_oos.py` | 113 | 4 KB |
| `stock_data.py` | 134 | 5 KB |
| `stock_direction.py` | 292 | 11 KB |
| `straddle_backtest.py` | 212 | 8 KB |
| `straddle_costs.py` | 132 | 5 KB |
| `straddle_extract.py` | 51 | 2 KB |
| `straddle_extract_full.py` | 43 | 2 KB |
| `straddle_hedged.py` | 211 | 9 KB |
| `straddle_inspect.py` | 33 | 936 B |
| `straddle_mae.py` | 88 | 4 KB |
| `straddle_program.py` | 124 | 6 KB |
| `straddle_tails.py` | 44 | 2 KB |
| `strategy_eval.py` | 333 | 14 KB |
| `stress_spread.py` | 119 | 5 KB |
| `structure_by_regime.py` | 126 | 5 KB |
| `structure_lab.py` | 415 | 18 KB |
| `swing_data.py` | 109 | 4 KB |
| `swing_lab.py` | 398 | 15 KB |
| `swing_sweep.py` | 310 | 12 KB |
| `test_intraday_momentum.py` | 124 | 6 KB |
| `test_intraday_momentum_spy.py` | 77 | 3 KB |
| `test_witching_drift.py` | 97 | 4 KB |
| `uw_backtest_weights.py` | 173 | 7 KB |
| `zebra_vs_call.py` | 171 | 8 KB |

## 06_data_guide — the data inventory

*1 files, 93 lines*

| file | lines | size |
|---|---:|---:|
| `DATA.md` | 93 | 4 KB |

## 07_superseded — retired documents, not instructions

*3 files, 725 lines*

| file | lines | size |
|---|---:|---:|
| `README.md` | 71 | 4 KB |
| `RULES.md` | 469 | 27 KB |
| `STRATEGY_0DTE.md` | 185 | 12 KB |

## docs — plan, audit, verdict log

*3 files, 943 lines*

| file | lines | size |
|---|---:|---:|
| `AUDIT.md` | 250 | 13 KB |
| `PLAN.md` | 314 | 17 KB |
| `VERDICT_LOG.md` | 379 | 19 KB |

## idt — the shared package and CLI

*5 files, 238 lines*

| file | lines | size |
|---|---:|---:|
| `__init__.py` | 9 | 367 B |
| `cli.py` | 81 | 3 KB |
| `db.py` | 22 | 773 B |
| `keys.py` | 64 | 2 KB |
| `paths.py` | 62 | 3 KB |

## scripts — repo tooling

*1 files, 203 lines*

| file | lines | size |
|---|---:|---:|
| `verify.py` | 203 | 9 KB |

---

## Repo tooling — session config, hooks and commands

Stamped by `tars adopt`, not part of the research bundle. Listed for completeness so the count above is the whole repo.

*16 files, 2,274 lines*

| file | lines | size |
|---|---:|---:|
| `.claude/settings.json` | 82 | 2 KB |
| `.claude/commands/dispatch.md` | 35 | 1 KB |
| `.claude/commands/eval.md` | 19 | 710 B |
| `.claude/commands/runs.md` | 24 | 634 B |
| `.claude/commands/tidy.md` | 19 | 738 B |
| `.claude/commands/verify.md` | 18 | 588 B |
| `.claude/skills/routing/SKILL.md` | 102 | 6 KB |
| `.tars/profile.json` | 16 | 330 B |
| `.tars/routing-policy.json` | 74 | 4 KB |
| `.tars/structure-migration.md` | 6 | 305 B |
| `.tars/structure.json` | 128 | 2 KB |
| `.tars/hooks/route-gate.cjs` | 1,182 | 58 KB |
| `.tars/hooks/sweep-report.cjs` | 223 | 9 KB |
| `.tars/hooks/tidy-gate.cjs` | 89 | 3 KB |
| `.tars/hooks/verify-gate.cjs` | 144 | 6 KB |
| `.tars/hooks/wip-autocommit.cjs` | 113 | 3 KB |
