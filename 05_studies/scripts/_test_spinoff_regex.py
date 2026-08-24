import re, html

raw = open("/private/tmp/claude-501/-Users-sahilmajmudar/c703fa96-a221-4df1-a82d-b31b1bf84807/scratchpad/gev.htm", encoding="utf-8", errors="ignore").read()
txt = re.sub(r"<[^>]+>", " ", raw)
txt = html.unescape(txt)
txt = re.sub(r"[ ]", " ", txt)
txt = re.sub(r"\s+", " ", txt)
head = txt[:250000]
print("len:", len(txt))

Q = '"“”‘’`\''
SYM_RE = re.compile(r'symbols?\s*[' + Q + r']\s*([A-Z]{1,5})\s*[.,]?\s*[' + Q + r']')
print("SYM hits:", [m.group(1) for m in SYM_RE.finditer(head)][:10])

RATIO_RE = re.compile(
    r'([\w-]+)\s+shares?\s+of\s+(?:our\s+|GE\s+Vernova\s+)?common\s+stock\s+'
    r'for\s+e(?:ach|very)\s+([\w-]+)?\s*shares?\s+of\s+([A-Za-z ]{0,30})common\s+stock', re.I)
for m in list(RATIO_RE.finditer(head))[:4]:
    print("RATIO:", m.group(0)[:150])

for kw in ["distribution date of", "Distribution Date", "expected to be", "record date", "when-issued", "regular-way"]:
    i = head.lower().find(kw.lower())
    print(f"\n--- {kw} @{i} ---")
    if i > 0:
        print(head[max(0, i-250):i+250])
