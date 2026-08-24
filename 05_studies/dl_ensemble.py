"""dl_ensemble.py — LSTM + GRU + Temporal-CNN + Transformer ensemble for next-session SPX direction.

Predicts P(up) for the NEXT session's open→close from a 20-day sequence of features (all as of the
prior close = no leakage). Target = sign(next open→close), the thing a 0DTE captures.

RIGOR (this is the whole point — DL on daily direction overfits trivially):
  - strict WALK-FORWARD: train on the past, test on the next block, roll forward. Never shuffle time.
  - scaler fit on TRAIN only, applied to test.
  - small models + dropout + early stopping to fight overfitting on ~3.7k daily samples.
  - honest baselines: majority class (~54%), and we compare the ensemble OOS to it.
Only worth wiring into the live signal if the ENSEMBLE OOS accuracy clearly beats the baseline.
"""
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from idt import paths

torch.manual_seed(0); np.random.seed(0)
DEV = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
LOOK = 20            # sequence length (days)
FEATS = ["dix_z", "gex_z", "ret1", "ret5", "rvol", "vix", "vix_ts", "trend", "dow_s", "dow_c"]


def build_data():
    import yfinance as yf
    G = pd.read_csv(paths.require_data("squeeze_dix_gex.csv"), parse_dates=["date"]).sort_values("date")
    px = yf.download(["SPY", "^VIX", "^VIX9D"], start="2011-05-01", interval="1d", progress=False, auto_adjust=True)
    d = pd.DataFrame({"date": px.index})
    for c in ("Open", "Close"):
        d[c.lower()] = px[c]["SPY"].values
    d["vix"] = px["Close"]["^VIX"].values; d["vix9"] = px["Close"]["^VIX9D"].values
    d["date"] = pd.to_datetime(d["date"]).dt.tz_localize(None)
    d = d.merge(G[["date", "dix", "gex"]], on="date", how="inner").sort_values("date").reset_index(drop=True)
    d["dix_z"] = (d.dix - d.dix.rolling(252, min_periods=60).mean()) / d.dix.rolling(252, min_periods=60).std()
    d["gex_z"] = (d.gex - d.gex.rolling(252, min_periods=60).mean()) / d.gex.rolling(252, min_periods=60).std()
    d["ret1"] = d.close.pct_change() * 100
    d["ret5"] = d.close.pct_change(5) * 100
    d["rvol"] = d.close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    d["vix_ts"] = d.vix9 / d.vix
    d["trend"] = (d.close / d.close.rolling(200).mean() - 1) * 100
    dow = pd.to_datetime(d.date).dt.dayofweek
    d["dow_s"] = np.sin(2 * np.pi * dow / 5); d["dow_c"] = np.cos(2 * np.pi * dow / 5)
    # TARGET: next session open->close direction (known at T+1 close; features all <= T)
    d["y"] = (d.close.shift(-1) > d.open.shift(-1)).astype(float)
    d = d.dropna(subset=FEATS + ["y"]).reset_index(drop=True)
    return d


def make_seqs(d, idx):
    X, Y = [], []
    arr = d[FEATS].values; y = d["y"].values
    for i in idx:
        if i < LOOK:
            continue
        X.append(arr[i - LOOK:i]); Y.append(y[i])
    return np.array(X, dtype=np.float32), np.array(Y, dtype=np.float32)


# ---------- models (small on purpose) ----------
class LSTMNet(nn.Module):
    def __init__(self, n): super().__init__(); self.r = nn.LSTM(n, 32, batch_first=True); self.h = nn.Sequential(nn.Dropout(.3), nn.Linear(32, 1))
    def forward(self, x): o, _ = self.r(x); return self.h(o[:, -1]).squeeze(-1)

class GRUNet(nn.Module):
    def __init__(self, n): super().__init__(); self.r = nn.GRU(n, 32, batch_first=True); self.h = nn.Sequential(nn.Dropout(.3), nn.Linear(32, 1))
    def forward(self, x): o, _ = self.r(x); return self.h(o[:, -1]).squeeze(-1)

class TCN(nn.Module):
    def __init__(self, n):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(n, 32, 3, padding=2, dilation=2), nn.ReLU(), nn.Dropout(.3),
            nn.Conv1d(32, 32, 3, padding=4, dilation=4), nn.ReLU(), nn.Dropout(.3))
        self.h = nn.Linear(32, 1)
    def forward(self, x): z = self.net(x.transpose(1, 2)); return self.h(z[:, :, -1]).squeeze(-1)

class Transformer(nn.Module):
    def __init__(self, n):
        super().__init__(); self.proj = nn.Linear(n, 32)
        enc = nn.TransformerEncoderLayer(32, 4, 64, dropout=.3, batch_first=True)
        self.enc = nn.TransformerEncoder(enc, 2); self.h = nn.Linear(32, 1)
    def forward(self, x): z = self.enc(self.proj(x)); return self.h(z.mean(1)).squeeze(-1)

MODELS = {"LSTM": LSTMNet, "GRU": GRUNet, "TCN": TCN, "Transformer": Transformer}


def train_one(Cls, Xtr, Ytr, Xva, Yva, epochs=60):
    m = Cls(len(FEATS)).to(DEV)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = nn.BCEWithLogitsLoss()
    xt, yt = torch.tensor(Xtr).to(DEV), torch.tensor(Ytr).to(DEV)
    xv, yv = torch.tensor(Xva).to(DEV), torch.tensor(Yva).to(DEV)
    best, best_state, patience = 1e9, None, 0
    for ep in range(epochs):
        m.train(); opt.zero_grad()
        loss = lossf(m(xt), yt); loss.backward(); opt.step()
        m.eval()
        with torch.no_grad():
            vl = lossf(m(xv), yv).item()
        if vl < best - 1e-4:
            best, best_state, patience = vl, {k: v.clone() for k, v in m.state_dict().items()}, 0
        else:
            patience += 1
            if patience > 12:
                break
    if best_state:
        m.load_state_dict(best_state)
    return m


def walk_forward(d):
    """Expanding-window walk-forward: test each ~1-yr block using only prior data."""
    n = len(d); fold = 252
    starts = list(range(fold * 3, n, fold))     # first test starts after 3y of history
    accs = {k: [] for k in MODELS}; accs["ENSEMBLE"] = []; base = []
    for s in starts:
        te = list(range(s, min(s + fold, n)))
        tr = list(range(0, s))
        # scaler on TRAIN only
        mu = d.loc[tr[LOOK:], FEATS].mean(); sd = d.loc[tr[LOOK:], FEATS].std().replace(0, 1)
        ds = d.copy(); ds[FEATS] = (ds[FEATS] - mu) / sd
        Xtr, Ytr = make_seqs(ds, tr); Xte, Yte = make_seqs(ds, te)
        if len(Xte) < 20 or len(Xtr) < 200:
            continue
        cut = int(len(Xtr) * 0.85)
        preds = []
        for name, Cls in MODELS.items():
            m = train_one(Cls, Xtr[:cut], Ytr[:cut], Xtr[cut:], Ytr[cut:])
            m.eval()
            with torch.no_grad():
                p = torch.sigmoid(m(torch.tensor(Xte).to(DEV))).cpu().numpy()
            preds.append(p)
            accs[name].append(((p > 0.5) == (Yte > 0.5)).mean())
        ens = np.mean(preds, axis=0)
        accs["ENSEMBLE"].append(((ens > 0.5) == (Yte > 0.5)).mean())
        base.append(max(Yte.mean(), 1 - Yte.mean()))
    print(f"Walk-forward OOS accuracy ({len(accs['ENSEMBLE'])} yearly folds):\n")
    print(f"  {'baseline (majority)':<22} {np.mean(base)*100:5.1f}%")
    for k in list(MODELS) + ["ENSEMBLE"]:
        if accs[k]:
            print(f"  {k:<22} {np.mean(accs[k])*100:5.1f}%   (folds: {', '.join(f'{a*100:.0f}' for a in accs[k])})")
    print(f"\n=> ensemble must clearly beat baseline ({np.mean(base)*100:.1f}%) OOS to be worth wiring in.")
    return accs, base


if __name__ == "__main__":
    d = build_data()
    print(f"dataset: {len(d)} days {d.date.min().date()}→{d.date.max().date()}, {len(FEATS)} features, device {DEV}\n")
    walk_forward(d)
