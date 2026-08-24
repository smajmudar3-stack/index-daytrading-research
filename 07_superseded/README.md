# 07_superseded: retired documents, kept as a record

**The rule for this directory, and there is only one:**

> **Nothing in here is an instruction.** Not a rule, not a number, not a structure,
> not a size. If you are looking for what to do, you are in the wrong folder.

Where to go instead:

| you want | read |
|---|---|
| the verdict on any claim in this repo | [`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md) |
| what survived testing | [`../02_findings/WHAT_WORKS.md`](../02_findings/WHAT_WORKS.md) |
| what did not, so it is not re-proposed | [`../02_findings/WHAT_FAILED.md`](../02_findings/WHAT_FAILED.md) |
| how a backtest lies, before writing one | [`../02_findings/METHODOLOGY_TRAPS.md`](../02_findings/METHODOLOGY_TRAPS.md) |

---

## What is in here

| file | what it claimed | why it was retired |
|---|---|---|
| [`STRATEGY_0DTE.md`](STRATEGY_0DTE.md) | "Above the gamma flip = pin (sell premium); below the flip = trend (buy premium)" | Buying premium below the flip measured **−7.2%** per trade on straddles and **−19.1%** on strangles |
| [`RULES.md`](RULES.md) | A 0DTE iron condor gated on prior-close dealer gamma at **+3.7% per trade, 91% win, t = +7.4**, filed under "VALIDATED & ROBUST" | The P&L came from Black-Scholes with a linear skew approximation. On 1,919 sessions of real SPXW bid/ask it is approximately break-even, and the 11:00 entry the live system used measured **−1.70%** |

Both were moved here on **2026-08-24**.

## Why they were not deleted

Because how a conclusion moves is evidence, and this repo's real value is negative
results. `RULES.md` in particular is worth reading once: it states its own weakest
assumption in §0, in the open, under the heading "The one assumption you cannot
escape", and that assumption is exactly what turned out to be wrong. A document
that names the thing that will kill it and then gets killed by that thing is a
better teacher than a document that was simply right.

Parts of both files were never overturned and are still cited by name elsewhere in
the repo. `RULES.md` §1.1 (the model-free range finding), §0 (how the testing was
done), §3 (everything rejected), §5 (the growth arithmetic) and §7 (the risks) all
still stand. **Citing a surviving section of a superseded document is fine. Trading
a refuted one is not**, which is why every refuted claim in both files is struck
through and labelled inline rather than left as clean prose.

## Why annotating them in place was not enough

Both files already carried a correction. `STRATEGY_0DTE.md` said at the top, on
2026-08-05, that its central rule "is WRONG and has been retired", and then stated
that same rule again further down the page as **"Rule: above the gamma flip = pin
...; below the flip = trend (buy premium)"**. The dashboard served that document to
users as "📖 How it works". A banner at the top of a document does not travel with
the paragraph a reader actually lands on.

So the standing rule here is stronger than a banner:

> **Every restatement of a retired claim inside a superseded document must be struck
> through or marked inline, so that no paragraph can be read in isolation as advice.**

## Adding something to this directory

1. Write the verdict in [`../docs/VERDICT_LOG.md`](../docs/VERDICT_LOG.md) first,
   with the measurement and the file that carries the evidence.
2. Move the document here.
3. Put the superseded banner at the top: what replaced it, one line of why, and a
   link to the verdict log.
4. Strike through every restatement of the retired claim in the body. Search for
   the claim, do not skim for it.
5. Fix the inbound links, including the ones in code.
6. Add a row to the table above.

Do not delete the original correction notes, and do not soften them. The honest
record of a past failure is the most valuable thing in a superseded file.
