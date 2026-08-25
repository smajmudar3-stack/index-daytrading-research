# Studies and backtests

The 113 harnesses that produced every number in the findings. All are standalone and read from `data/`. Anything here that reports a positive result should be re-checked against [../02_findings/METHODOLOGY_TRAPS.md](../02_findings/METHODOLOGY_TRAPS.md).

| file | what it does |
|---|---|
| `backtest_0dte_rules.py` | backtest_0dte_rules.py — a concrete, walk-forward-validated 0DTE rule set for SPX (SPY proxy). |
| `backtest_daily.py` | backtest_daily.py — what does the validated edge actually return DAY BY DAY? |
| `backtest_directional.py` | backtest_directional.py — directional 0DTE only, at 25% sizing, on the system's own filter. |
| `backtest_intraday_dir.py` | backtest_intraday_dir.py — the trade the owner ACTUALLY makes. |
| `backtest_intraday_v2.py` | backtest_intraday_v2.py — can we make the DIRECTION call better? |
| `backtest_swing_rules.py` | backtest_swing_rules.py — sector-rotation relative-strength swing options, rigorously validated. |
| `bt_options.py` | bt_options.py — shared, causal option-P&L machinery for the rule backtests. |
| `condor_backtest.py` | condor_backtest.py — when does a 0DTE iron condor actually survive? (entry time × width × gamma regime) |
| `dix_direction.py` | dix_direction.py — Can DIX give DIRECTION on negative-gamma days? (GEX can't — proven.) |
| `dl_ensemble.py` | dl_ensemble.py — LSTM + GRU + Temporal-CNN + Transformer ensemble for next-session SPX direction. |
| `fomc_research.py` | FOMC-day behavior + current QQQ options pricing, to ground tomorrow's play. |
| `hunt_base_rate.py` | hunt_base_rate.py — STEP 1 of the direction hunt: how often does the target move even occur? |
| `hunt_conditional.py` | hunt_conditional.py — push the FADE hit rate from ~53% toward 60%. |
| `hunt_features.py` | hunt_features.py — build the full intraday feature matrix and test EVERY feature for directional |
| `hunt_final.py` | hunt_final.py — the regime-switched directional system, tuned on TRAIN, evaluated ONCE on TEST. |
| `hunt_flow.py` | hunt_flow.py — does REAL 0DTE options order flow predict SPX direction? |
| `hunt_horizons.py` | hunt_horizons.py — every holding period from 15 min to 2 hours, both regime legs, TRAIN vs TEST. |
| `hunt_indicators.py` | hunt_indicators.py — the full technical-indicator battery, then every combination against it. |
| `hunt_master.py` | hunt_master.py — the definitive search. Every feature, every 1-3 way combination, 3-way split. |
| `hunt_patterns.py` | hunt_patterns.py — discrete PRICE-ACTION setups, not indicator deciles. |
| `hunt_patterns_spx.py` | hunt_patterns_spx.py — the pattern library on 1,919 sessions of SPX instead of 500 of QQQ. |
| `hunt_skew.py` | hunt_skew.py — intraday IV SKEW and the real GAMMA PROFILE, neither of which has been tested here. |
| `hunt_strategy.py` | hunt_strategy.py — turn the surviving signals into an actual traded rule and measure it. |
| `intraday_macro.py` | Does ANY intraday signal work inside a specific MACRO/regime pocket? Condition the core |
| `intraday_patterns.py` | Exhaustive intraday pattern/indicator scan on 2y of 5-min bars (SPY/QQQ = 0DTE underlying). |
| `intraday_puts.py` | intraday_puts.py — which INTRADAY short/put triggers actually work, split by gamma regime. |
| `merge_optimize.py` | Merge the edges the RIGHT way (weight by quality, not equally) and test OUT-OF-SAMPLE. |
| `mes_overnight.py` | MES/ES overnight strategy research — build the best HONEST S&P futures edge. |
| `mes_refine.py` | Refine + robustness-check the overnight strategy: is the vol filter overfit? Does |
| `mes_signals.py` | mes_signals.py — live signals for the merged MES/MNQ system -> data/mes_snapshot.json. |
| `minute_edges.py` | Intraday day-trading strategies on 2 years of MINUTE bars (QQQ/SPY, regular session). |
| `momentum_intraday.py` | momentum_intraday.py — the Zarattini "Beat the Market" intraday momentum breakout, tested on our |
| `momentum_scan.py` | Scan liquid optionable names across NON-tech industries for the cleanest idiosyncratic |
| `momentum_stocks.py` | Where day-traders ACTUALLY operate: volatile individual stocks, not the index. |
| `multi_edge.py` | Find MULTIPLE real index edges, measure their correlation, and merge the uncorrelated |
| `orb_proper.py` | ORB evaluated the way it is actually traded: RISK-NORMALISED (R-multiples). |
| `predictability.py` | How predictable is 'tomorrow' really? Take the BEST setup we have — a stock in a strong |
| `scalp_backtest.py` | scalp_backtest.py — does the WALL-FADE scalp work, conditioned on gamma regime? |
| `scalp_update.py` | scalp_update.py — FAST live scalp updater for the morning momentum window (9:30–12:00 ET). |
| `scripts/_test_spinoff_regex.py` | — |
| `scripts/accuracy_hurdle.py` | What directional accuracy would we actually NEED to profit from 0DTE options? |
| `scripts/base_rate_check.py` | Base-rate check for the conditional dip-buying result. |
| `scripts/bigmove_hunt.py` | What actually precedes a BIG MOVE? The selection problem, done properly. |
| `scripts/blackswan_flip.py` | Two questions the last test raised but did not answer. |
| `scripts/blackswan_select.py` | Can SELECTION rescue far-OTM buying? The owner's actual thesis, tested. |
| `scripts/blackswan_test.py` | Black-swan lottery test: does buying very cheap far-OTM options pay? |
| `scripts/breakout_tradeable.py` | Enter AT the break, not at 10:00. The difference is the whole result. |
| `scripts/build_bundle.py` | Consolidate the whole index-daytrading repo into one self-describing folder. |
| `scripts/build_indexes.py` | Generate per-folder INDEX.md files from real docstrings, not guesses. |
| `scripts/build_iv_features.py` | Feasibility check: can we build the index-level constructs the paper sweep needs? |
| `scripts/bwb_and_box.py` | (a) Is a CREDIT broken-wing butterfly actually obtainable on SPY, and what does |
| `scripts/cb_cboe_idx.py` | Cboe benchmark index forensics: CNDR (iron condor), BFLY (iron butterfly), PUT, WPUT, BXM, SPX. |
| `scripts/cb_cndr_decay.py` | — |
| `scripts/cb_drag_crosscheck.py` | Independent cross-check of the 8-crossing spread drag, expressed as % of CAPITAL AT RISK. |
| `scripts/cb_drag_deltawing.py` | Like-for-like cross-check of the coordinator's SPY result: DELTA-DEFINED wings. |
| `scripts/cb_spxw_costs.py` | 4-leg bid/ask drag and expectancy for 0DTE SPX iron BUTTERFLIES and CONDORS, on REAL quotes. |
| `scripts/cb_spxw_manage.py` | 0DTE SPX iron butterflies / condors on REAL quotes: management rules and regime conditioning. |
| `scripts/cb_weekly_condor.py` | WEEKLY vs MONTHLY iron condors and iron butterflies on SPY, priced on REAL EOD bid/ask. |
| `scripts/cb_weekly_manage.py` | Weekly SPY iron condors: NON-OVERLAPPING trades + real path-dependent management. |
| `scripts/check_apis.py` | Probe what the Polygon and Tiingo keys can actually reach. |
| `scripts/combo_sweep.py` | Exhaustive gate-combination sweep: every 1..6-way combo, every structure. |
| `scripts/daily_engine.py` | What do these structures pay if you trade ~1 per day, gated on regime? |
| `scripts/delta_hedged_gains.py` | Delta-hedged gains on SPY, 2008-2025 — a modern replication of Bakshi & Kapadia |
| `scripts/diagnose_1300.py` | Is the 13:00 -> 15:00 result real, or a half-day artifact? |
| `scripts/earnings_convexity.py` | Buy convexity before a DATED catalyst — the one version of the idea with |
| `scripts/edge_budget.py` | The edge budget: what directional hit rate does a once-a-day intraday trade actually need, |
| `scripts/exotic_claims_test.py` | Tests the specific HEADLINE CLAIMS made about each exotic structure, on real SPY |
| `scripts/exotic_structure_costs.py` | Empirical cost measurement for exotic / multi-leg option structures. |
| `scripts/fat_tail_test.py` | Are black swans more common than the model says? Yes. Does that make options cheap? No. |
| `scripts/gao_corrected.py` | Gao/Baltussen intraday momentum, with the outcome window defined correctly. |
| `scripts/gao_intraday_momentum.py` | The actual Gao-Han-Li-Zhou intraday momentum rule, on minute bars. |
| `scripts/intraday_inventory.py` | What intraday data can we actually test a directional rule against? |
| `scripts/intraday_inventory2.py` | Second pass: the timestamps live where the first pass did not look. |
| `scripts/intraday_predict_matrix.py` | Does any half-hour of the day predict any other? The full matrix. |
| `scripts/leadlag_test.py` | Cross-asset intraday lead-lag, tested at the resolution a retail system can actually act on. |
| `scripts/leadlag_trade.py` | Honest test of the IWM -> QQQ lead-lag that showed up in leadlag_test.py. |
| `scripts/lit_search.py` | Rate-limited Semantic Scholar lookups for the spinoff / event-driven literature. |
| `scripts/macro_test.py` | Does the macro/rates narrative actually predict sector returns at swing horizon? |
| `scripts/mirror_drift_control.py` | Is QQQ's breakout asymmetry a signal, or is it just drift? |
| `scripts/mirror_test.py` | The mirror test: is a breakout "hit rate" directional, or just volatility? |
| `scripts/move_distribution.py` | How far does price actually move over a hold? The right input to the hurdle. |
| `scripts/nge_proper.py` | The Baltussen test done properly: full-surface NGE + the true 09:30 open. |
| `scripts/nge_validate.py` | Validate the Baltussen dealer-gamma split on our own SPXW chains. |
| `scripts/openalex_gap.py` | Fill remaining gaps: recent works citing Cusatis-Miles-Woolridge, plus targeted title searches. |
| `scripts/openalex_lit.py` | OpenAlex lookups for the spinoff / event-driven anomaly literature. |
| `scripts/option_drag.py` | Measure the true hurdle for expressing a 90-minute directional view in a 0DTE option, |
| `scripts/option_edge.py` | Greeks, option pricing, and structure selection for a swing-horizon view. |
| `scripts/osap_spinoff_decay.py` | Compute in-sample vs post-publication performance of the OSAP 'Spinoff' predictor. |
| `scripts/osap_spinoff_ports.py` | Portfolio-level detail for the OSAP 'Spinoff' predictor: leg composition and breadth. |
| `scripts/outlier_day_effect.py` | One day is generating the entire intraday "edge". Identify it and re-test. |
| `scripts/parse_ssi.py` | — |
| `scripts/preann_test.py` | Pre-announcement overnight drift — the one live candidate from the literature. |
| `scripts/preswan_signals.py` | Do BIG MOVERS look different in the days BEFORE they move? |
| `scripts/range_matched.py` | Match the STRUCTURE to the predicted RANGE, since range is what gamma predicts. |
| `scripts/rate_pair_test.py` | Trade the RESIDUAL, not the forecast — the one idea my own data supports. |
| `scripts/sa_spinoffs.py` | — |
| `scripts/signal_vs_base.py` | Is the signal better than buying a call on a RANDOM day? The decisive test. |
| `scripts/smallcap_tails.py` | Do small / low-priced stocks have fatter tails — and can you trade them? |
| `scripts/spinoff_edgar_harvest.py` | Survivorship-bias-free US corporate spinoff dataset from SEC EDGAR. |
| `scripts/spinoff_etf_oos.py` | Real-money out-of-sample test of the spinoff anomaly. |
| `scripts/stock_data.py` | Fetch daily history for a liquid, optionable US stock universe (Tiingo). |
| `scripts/stock_direction.py` | Market-conditioned stock direction for 5-10 day swing trades. |
| `scripts/straddle_backtest.py` | Part B: REAL-QUOTE hold-to-expiry backtest of straddles and strangles on SPY/QQQ. |
| `scripts/straddle_costs.py` | Part A: REAL bid/ask spread census for straddles and strangles on SPY/QQQ. |
| `scripts/straddle_extract.py` | Pass 1: stream the 24.7M-row SPY (and QQQ) EOD chain and keep a compact slice: |
| `scripts/straddle_extract_full.py` | Pass 1b: same monthly slice but with NO delta filter, so option PATHS |
| `scripts/straddle_hedged.py` | Part C: DELTA-HEDGED vs NAKED straddles on real SPY/QQQ EOD quotes. |
| `scripts/straddle_inspect.py` | Inspect the real EOD option chain parquet files. |
| `scripts/straddle_mae.py` | Part F: maximum ADVERSE EXCURSION of the short straddle during the life of |
| `scripts/straddle_program.py` | Part D: program-level economics of a monthly short-vol sleeve, real quotes. |
| `scripts/straddle_tails.py` | Part E: the real-quote tail. Which months produced the worst short-premium |
| `scripts/strategy_eval.py` | Evaluate candidate swing strategies through REAL SPY option quotes. |
| `scripts/stress_spread.py` | Does the bid-ask blow out exactly when you need to exit? Measured, not inferred. |
| `scripts/structure_by_regime.py` | Direction comes from flow. GAMMA picks how to EXPRESS it. |
| `scripts/structure_lab.py` | Every option structure, every timeframe, every regime -- on REAL SPY quotes. |
| `scripts/swing_data.py` | Fetch and cache the daily panel for swing-horizon research. |
| `scripts/swing_lab.py` | Swing-horizon edge lab: cross-sectional sector rotation + regime timing. |
| `scripts/swing_sweep.py` | Exhaustive sweep of swing-horizon strategies, scored honestly. |
| `scripts/test_intraday_momentum.py` | Baltussen/Da/Lammers/Martens (JFE 2021) market intraday momentum, tested on our own |
| `scripts/test_intraday_momentum_spy.py` | Independent, genuinely-recent check of market intraday momentum on SPY 1-minute data |
| `scripts/test_witching_drift.py` | Test the "derivative payoff bias" / third-Friday AM-settlement drift on our own SPX data. |
| `scripts/theta_hurdle.py` | The spread is not the binding cost on 0DTE direction -- theta is. |
| `scripts/ticket_decay.py` | How much of each ticket's premium is time value that decays to zero? |
| `scripts/uw_backtest_weights.py` | Backtest the UW inputs that HAVE history, so their weights are earned. |
| `scripts/vehicle_choice.py` | At a 53% hit rate, which vehicle actually pays: stock, ATM call, OTM, or deep ITM? |
| `scripts/vol_gate.py` | The payoff of the volatility work: can a forecast pick the tradeable days? |
| `scripts/vol_har.py` | Is volatility actually predictable on our data, and can anything beat HAR? |
| `scripts/vol_vs_implied.py` | HAR predicts volatility. Does it predict anything the OPTION MARKET does not? |
| `scripts/wing_economics.py` | Does a long wing cost less than the tail it removes? |
| `scripts/zebra_vs_call.py` | ZEBRA vs a plain 0.80-delta call vs ATM call vs 100 shares — head to head, |
| `validate_condor_real.py` | validate_condor_real.py — the condor edge, priced on REAL SPXW quotes instead of a model. |
| `validate_gapgo.py` | Stress-test the gap-and-go-with-volume edge before believing it. Kill it if it's fragile: |
| `validate_newlo_delta1.py` | validate_newlo_delta1.py — express the new-low edge WITHOUT paying premium. |
| `validate_newlo_real.py` | validate_newlo_real.py — the new-low continuation setup, traded as a REAL 0DTE put. |
| `vwap_momentum.py` | Intraday VWAP MOMENTUM — trade WITH the extension (the mirror of the losing fade). |
| `vwap_reversion.py` | Intraday VWAP mean-reversion — the opposite mechanism to breakout. |

**136 files.**
