"""Part E: the real-quote tail. Which months produced the worst short-premium
losses, and how large were they as a multiple of the credit collected and of
Reg-T naked margin?"""
import pandas as pd
import pickle

from idt import paths

SYM = "SPY"

pd.set_option("display.width", 240)


def main():
    with open(paths.require_data("opt_eod", f"{SYM}_straddle_sel.pkl"), "rb") as fh:
        sel = pickle.load(fh)

    for key in [("ATM straddle", 45), ("16d strangle", 45), ("30d strangle", 45)]:
        s = sel[key].copy()
        s["loss_x_credit"] = -(s["bid_t"] - s["payoff"]) / s["bid_t"]
        s["margin"] = 0.20 * s["spot"] * 100
        s["loss_x_margin"] = -(s["bid_t"] - s["payoff"]) * 100 / s["margin"]
        s["move_%"] = 100 * (s["S_T"] / s["spot"] - 1)
        w = s.nsmallest(8, "short_bid")[["date", "expiration", "spot", "S_T", "move_%",
                                         "bid_t", "payoff", "loss_x_credit", "loss_x_margin"]]
        print(f"\n=== {key[0]} @45DTE: 8 worst months for the SHORT side (real EOD NBBO) ===")
        print(w.round(2).to_string(index=False))
        n = len(s)
        print(f"  n={n};  months where the loss exceeded 1x the credit: "
              f"{(s['loss_x_credit'] > 1).sum()} ({100*(s['loss_x_credit']>1).mean():.1f}%)")
        print(f"  months where the loss exceeded 5x the credit: {(s['loss_x_credit'] > 5).sum()}")
        print(f"  months where the loss exceeded the 20%-notional margin posted: "
              f"{(s['loss_x_margin'] > 1).sum()}")
        print(f"  sum of the 3 worst months as a multiple of the mean monthly credit: "
              f"{(-s.nsmallest(3,'short_bid')['short_bid']).sum():.1f}x")
        tot = s["short_bid"].sum()
        top3 = s.nsmallest(3, "short_bid")["short_bid"].sum()
        print(f"  total return over the whole sample (sum of per-trade % of credit): {100*tot:.0f}%;"
              f"  excluding the 3 worst months: {100*(tot-top3):.0f}%")


if __name__ == "__main__":
    main()
