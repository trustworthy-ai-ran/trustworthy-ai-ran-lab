#!/usr/bin/env python3
"""
Reconcile the published p95 with the archived probe logs.

METHOD.md reports Run 2 p95 = 2,189 ms and Run 3 p95 = 2,125 ms, "agreeing
within 3%". Recomputing from run2_ping.txt gives ~2,487 ms under every
window definition tried. This scans statistic x window combinations to find
which one reproduces the published figure, and re-checks the replication
claim under whichever definition is adopted.

    python3 reconcile_p95.py run2_ping.txt run3_ping.txt
"""

import sys, re
from datetime import datetime, timezone

def parse_ping(path):
    out, day = [], datetime(2026, 7, 17, tzinfo=timezone.utc)
    utc_re   = re.compile(r'\[(\d{2}:\d{2}:\d{2})\s*UTC\]')
    epoch_re = re.compile(r'^\[?(\d{10}(?:\.\d+)?)\]?')
    rtt_re   = re.compile(r'time[=<]\s*([\d.]+)\s*ms')
    for line in open(path, errors='replace'):
        r = rtt_re.search(line)
        if not r: continue
        rtt = float(r.group(1))
        m = utc_re.search(line)
        if m:
            hh, mm, ss = map(int, m.group(1).split(':'))
            out.append((day.replace(hour=hh, minute=mm, second=ss), rtt)); continue
        m = epoch_re.match(line)
        if m:
            out.append((datetime.fromtimestamp(float(m.group(1)), timezone.utc), rtt))
    return out

def load_window(ping, thr, need=5, tol=5):
    hi = [i for i, (_, r) in enumerate(ping) if r > thr]
    if not hi: return None, None
    st = next((hi[i] for i in range(len(hi)-need+1)
               if hi[i+need-1]-hi[i] == need-1), None)
    if st is None: return None, None
    en, miss = st, 0
    for i in range(st, len(ping)):
        if ping[i][1] > thr: en, miss = i, 0
        else:
            miss += 1
            if miss > tol: break
    return ping[st][0], ping[en][0]

# --- percentile variants -------------------------------------------------
def p_index(v, p):                       # v[int(p*(n-1))]
    return v[int(p*(len(v)-1))]
def p_nearest(v, p):                     # round to nearest rank
    return v[min(len(v)-1, max(0, round(p*(len(v)-1))))]
def p_linear(v, p):                      # numpy default
    k = p*(len(v)-1); f = int(k); c = min(f+1, len(v)-1)
    return v[f] + (v[c]-v[f])*(k-f)
def p_ceil(v, p):                        # classic nearest-rank, ceil
    import math
    return v[min(len(v)-1, math.ceil(p*len(v))-1)]

STATS = {
    'p95 index'   : lambda v: p_index(v, .95),
    'p95 nearest' : lambda v: p_nearest(v, .95),
    'p95 linear'  : lambda v: p_linear(v, .95),
    'p95 ceil'    : lambda v: p_ceil(v, .95),
    'p90 linear'  : lambda v: p_linear(v, .90),
    'p75 linear'  : lambda v: p_linear(v, .75),
    'median'      : lambda v: p_linear(v, .50),
    'mean'        : lambda v: sum(v)/len(v),
}

def windows(ping, t0, t1):
    """Candidate sample sets."""
    w = {}
    w['detected window']   = [r for t, r in ping if t0 <= t <= t1]
    w['whole log']         = [r for _, r in ping]
    for skip in (5, 10, 15, 20, 30):
        w[f'skip first {skip}s'] = [r for t, r in ping
                                    if (t-t0).total_seconds() >= skip and t <= t1]
    for trim in (5, 10, 20):
        w[f'trim last {trim}s']  = [r for t, r in ping
                                    if t0 <= t and (t1-t).total_seconds() >= trim]
    w['fixed 120s from t0'] = [r for t, r in ping
                               if 0 <= (t-t0).total_seconds() <= 120]
    w['load + recovery']   = [r for t, r in ping if t >= t0]
    return w

def report(path, target=None):
    ping = parse_ping(path)
    rough = sorted(r for _, r in ping)[len(ping)//10]
    t0, t1 = load_window(ping, 5*rough)
    idle = sorted(r for t, r in ping if t < t0)
    base = idle[len(idle)//2]
    print(f"\n=== {path} ===")
    print(f"  {len(ping)} samples · idle median {base:.0f} ms · "
          f"window {t0:%H:%M:%S}-{t1:%H:%M:%S} ({(t1-t0).total_seconds():.0f} s)")
    hits = []
    for wname, vals in windows(ping, t0, t1).items():
        if len(vals) < 5: continue
        sv = sorted(vals)
        for sname, fn in STATS.items():
            val = fn(sv)
            if target and abs(val - target) <= 15:
                hits.append((sname, wname, val, len(sv)))
    print(f"  {'statistic':<13} {'window':<22} {'value':>9}  n")
    for wname, vals in windows(ping, t0, t1).items():
        if len(vals) < 5: continue
        sv = sorted(vals)
        for sname in ('p95 linear', 'median'):
            v = STATS[sname](sv)
            mark = '  <<<' if target and abs(v-target) <= 15 else ''
            print(f"  {sname:<13} {wname:<22} {v:9.0f}  {len(sv):3d}{mark}")
    if target:
        print(f"\n  --- combinations reproducing {target} ms (±15) ---")
        if hits:
            for s, w, v, n in hits:
                print(f"    {s:<13} over {w:<22} -> {v:.0f} ms  (n={n})")
        else:
            print("    NONE. The published figure is not reproducible from this log")
            print("    under any statistic x window combination tested.")
    return {name: STATS['p95 linear'](sorted(v))
            for name, v in windows(ping, t0, t1).items() if len(v) >= 5}, base

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    targets = {1: 2189, 2: 2125}
    res = []
    for i, p in enumerate(sys.argv[1:], 1):
        res.append(report(p, targets.get(i)))

    if len(res) == 2:
        print("\n=== REPLICATION CHECK under the recomputed definition ===")
        a, b = res[0][0], res[1][0]
        for w in a:
            if w in b and a[w] and b[w]:
                d = 100*abs(a[w]-b[w])/max(a[w], b[w])
                flag = 'OK' if d <= 5 else 'DIVERGES'
                print(f"  {w:<22} run2 {a[w]:6.0f}   run3 {b[w]:6.0f}   diff {d:4.1f}%  {flag}")
        print("\n  METHOD.md claims the two valid runs agree within 3%.")
        print("  Whichever definition is adopted must be checked against that claim.")

if __name__ == '__main__':
    main()
