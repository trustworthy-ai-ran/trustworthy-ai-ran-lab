#!/usr/bin/env python3
"""
Trustworthy AI-RAN Lab — figure generation for UC-06.

Regenerates the data figures directly from the archived logs so that every
number on every figure is traceable to a file in this repository.

    python3 make_figures.py --kpm data/kpm_continuous_all_runs.log \
                            --ping data/run2_ping.txt \
                            --outdir figures

Produces:
    03_result_hero.png          two-panel: what the RIC received vs. user RTT
    05_proof_time_aligned.png   verbatim log excerpts, same seconds

Figure slot 04 was retired rather than replaced. The original
04_raw_capture_annotated.png came from the voided Run 1 and carried a caption
its own contents contradicted. Everything a replacement would have shown - the
~2.5 s cadence, the value/0.0 alternation, the 23-of-24 identical readings -
is already stated in the hero footnote and in METHOD.md section 3.

Corrections applied relative to the first published set:

  * The 0.0 samples are a strictly alternating reporting-window artifact
    (verified: 24 zero / 24 non-zero, perfectly interleaved across the whole
    121 s load window). They are now explained in the caption rather than
    silently filtered.
  * Figure 5 is rendered FROM the log. The previously published panel showed
    timestamps 05:29:36 and 05:29:38, which do not exist in the archive, and
    gave 05:29:40 as 59,043 where the log records 0.0.
  * The indication cadence is ~2.5 s, not the 1 s stated earlier.
"""

import argparse, re, sys
from collections import Counter
from datetime import datetime, timezone

VERSION   = "v6 (28 Jul 2026) - figure slot 04 retired; generates 03 and 05 only"
WATERMARK = "Trustworthy AI-RAN Lab  ·  github.com/trustworthy-ai-ran"

# --------------------------------------------------------------------- parse
def parse_kpm(path):
    out, ts = [], None
    ts_re  = re.compile(r'ColletStartTime:\s*(\d{4}-\d{2}-\d{2}[ T][\d:]{8})')
    val_re = re.compile(r'Metric:\s*([\w.]+),\s*Value:\s*\[([^\]]*)\]')
    for line in open(path, errors='replace'):
        m = ts_re.search(line)
        if m:
            ts = datetime.strptime(m.group(1).replace('T', ' '),
                                   '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            continue
        m = val_re.search(line)
        if m and ts is not None:
            raw = m.group(2).strip()
            try:    out.append((ts, float(raw)))
            except ValueError: out.append((ts, None))
            ts = None
    return out

def parse_ping(path, day=None):
    out = []
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
            base = day or datetime(2026, 7, 17, tzinfo=timezone.utc)
            out.append((base.replace(hour=hh, minute=mm, second=ss), rtt)); continue
        m = epoch_re.match(line)
        if m:
            out.append((datetime.fromtimestamp(float(m.group(1)), timezone.utc), rtt))
    return out

def load_window(ping, baseline, need=5, factor=5, tol=5):
    """Sustained elevation only — isolated idle-phase spikes cannot trigger."""
    thr = factor * baseline
    hi = [i for i, (_, r) in enumerate(ping) if r > thr]
    if not hi: return None, None
    start = next((hi[i] for i in range(len(hi)-need+1)
                  if hi[i+need-1]-hi[i] == need-1), None)
    if start is None: return None, None
    end, miss = start, 0
    for i in range(start, len(ping)):
        if ping[i][1] > thr: end, miss = i, 0
        else:
            miss += 1
            if miss > tol: break
    return ping[start][0], ping[end][0]

def stamp(fig):
    fig.text(0.995, 0.005, WATERMARK, ha='right', va='bottom',
             fontsize=7.5, color='#9a9a9a')

# ------------------------------------------------------------------ figure 3
def fig_hero(kpm, ping, t0, t1, baseline, outdir):
    import matplotlib.pyplot as plt
    dur   = (t1 - t0).total_seconds()
    inwin = [(t, v) for t, v in kpm if t0 <= t <= t1]
    nz    = [(t, v) for t, v in inwin if v not in (None, 0.0)]
    zeros = [t for t, v in inwin if v == 0.0]

    kx = [(t-t0).total_seconds() for t, _ in kpm if _ not in (None, 0.0)]
    ky = [v for _, v in kpm if v not in (None, 0.0)]
    px = [(t-t0).total_seconds() for t, _ in ping]
    py = [r for _, r in ping]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                                   gridspec_kw={'hspace': 0.16})
    fig.suptitle("The Blind Judge — what the Near-RT RIC received  vs.  what the user experienced",
                 fontsize=14.5, x=0.015, ha='left', y=0.97)
    for ax in (ax1, ax2):
        ax.axvspan(0, dur, color='#F5A623', alpha=0.13, lw=0)
        ax.set_xlim(min(px)-5, max(px)+5)
        ax.grid(alpha=0.25)

    ax1.plot(kx, ky, color='#1a7a3e', lw=2.0, marker='o', ms=3.6)
    ax1.set_ylabel("E2SM-KPM  DRB.UEThpDl\n(as reported)")
    ax1.text(0.985, 0.93, "WHAT THE RIC RECEIVED", transform=ax1.transAxes,
             ha='right', va='top', color='#1a7a3e', fontweight='bold', fontsize=11.5)
    if nz:
        vals = Counter(v for _, v in nz)
        top, n = vals.most_common(1)[0]
        ax1.annotate(f"{top:,.0f} on {n} of {len(nz)} reports — flat throughout,\n"
                     f"no degradation signal at any point",
                     xy=(dur*0.45, top), xytext=(dur*0.52, top*0.62),
                     color='#1a7a3e', fontsize=10.5,
                     arrowprops=dict(arrowstyle='->', color='#1a7a3e', lw=1.2))

    ax2.semilogy(px, py, color='#c0392b', lw=1.35)
    ax2.axhline(baseline, color='gray', ls=':', lw=1)
    ax2.text(0.012, 0.90, f"idle baseline ≈{baseline:.0f} ms", transform=ax2.transAxes,
             color='gray', fontsize=9, va='top')
    ax2.set_ylabel("User RTT, ping probe\n(ms, log scale)")
    ax2.set_xlabel(f"Time relative to load start (s)  —  shaded: {dur:.0f} s saturating DL UDP (30 Mb/s offered)")
    ax2.text(0.985, 0.93, "WHAT THE USER FELT", transform=ax2.transAxes,
             ha='right', va='top', color='#c0392b', fontweight='bold', fontsize=11.5)
    lo   = sorted(r for t, r in ping if t0 <= t <= t1)
    allr = sorted(r for _, r in ping)
    p95_all = allr[int(0.95*(len(allr)-1))]           # published definition
    p95_win = lo[int(0.95*(len(lo)-1))] if lo else 0  # load window only
    if lo:
        ax2.annotate(f"p95 {p95_all/1000:.2f} s  (max {max(lo)/1000:.2f} s)\n"
                     f"~{p95_all/baseline:.0f}× the {baseline:.0f} ms baseline",
                     xy=(dur*0.55, p95_all), xytext=(dur*0.60, p95_all*0.30),
                     color='#c0392b', fontsize=10.5,
                     arrowprops=dict(arrowstyle='->', color='#c0392b', lw=1.2))

    import textwrap
    note = (
        f"Run 2 of the pre-registered series · srsRAN gNB + free5GC + O-RAN SC Near-RT RIC (i-release), live E2 / E2SM-KPM Style 2. "
        f"Indications arrive ≈2.5 s apart, alternating a value with an empty reporting window "
        f"({len(zeros)} empty / {len(nz)} valued inside the load phase, strictly interleaved); the empty windows are omitted from the line above. "
        f"Latency statistic: p95 = {p95_all:.0f} ms over the full probe series ({len(allr)} samples) — the published definition; "
        f"{p95_win:.0f} ms if restricted to the load window ({len(lo)} samples). Replicated in Run 3.")
    fig.text(0.015, -0.02, "\n".join(textwrap.wrap(note, 165)),
             fontsize=8.2, color='#4a4a4a', va='top')
    fig.text(0.995, -0.02, WATERMARK, ha='right', va='top', fontsize=7.5, color='#9a9a9a')
    p = f"{outdir}/03_result_hero.png"
    plt.savefig(p, dpi=150, bbox_inches='tight', facecolor='white'); plt.close()
    return p

# ------------------------------------------------------------------ figure 5
def fig_proof(kpm, ping, outdir, n=4, start_at=None):
    # n = number of Indication blocks rendered; 4 fits the box
    """Verbatim excerpts, rendered from the log — no hand transcription."""
    import matplotlib.pyplot as plt
    lo = [(t, v) for t, v in kpm if (start_at is None or t >= start_at)]
    sel = lo[:n]
    if not sel: sys.exit("no KPM samples for the proof panel")
    t_lo, t_hi = sel[0][0], sel[-1][0]
    pings = [(t, r) for t, r in ping if t_lo <= t <= t_hi]

    fig = plt.figure(figsize=(14, 6.6), facecolor='#1c1c1c')
    fig.text(0.015, 0.955,
             f"The Proof — same network, same seconds  "
             f"(Run 2 · {t_lo:%Y-%m-%d} · {t_lo:%H:%M:%S}–{t_hi:%H:%M:%S} UTC)",
             color='white', fontsize=15, fontweight='bold', va='top')
    fig.text(0.015, 0.905,
             "Rendered directly from the archived logs by make_figures.py. "
             "KPM ColletStartTime is native UTC; probe timestamps converted to UTC.",
             color='#b0b0b0', fontsize=9, va='top')

    axL = fig.add_axes([0.015, 0.16, 0.47, 0.71]); axR = fig.add_axes([0.515, 0.16, 0.47, 0.71])
    for ax, col, title in ((axL, '#2ecc71', "what the RIC received  ·  kpm_mon_xapp"),
                           (axR, '#e74c3c', "what the user experienced  ·  1 Hz probe (UE → N6)")):
        ax.set_facecolor('#1c1c1c'); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values(): s.set_color(col); s.set_linewidth(1.6)
        ax.text(0.02, 0.965, title, transform=ax.transAxes, color=col,
                fontsize=10.5, fontweight='bold', va='top')

    y = 0.86
    for t, v in sel:
        axL.text(0.03, y, "RIC Indication Received from gnbd_208_093_00019b_0",
                 transform=axL.transAxes, color='#d8d8d8', fontsize=8.6, family='monospace')
        axL.text(0.05, y-0.052, f"-ColletStartTime:  {t:%Y-%m-%d %H:%M:%S}",
                 transform=axL.transAxes, color='#d8d8d8', fontsize=8.6, family='monospace')
        txt = "0.0" if v == 0.0 else f"{v:.1f}"
        c   = '#f39c12' if v == 0.0 else '#2ecc71'
        axL.text(0.05, y-0.104, f"--Metric: DRB.UEThpDl, Value: [{txt}]",
                 transform=axL.transAxes, color=c, fontsize=8.6, family='monospace',
                 bbox=dict(boxstyle='square,pad=0.25', fc='none', ec=c, lw=0.9))
        y -= 0.205
    axL.text(0.03, 0.045,
             "strict alternation: a value, then an empty reporting window\n"
             "neither state responds to the latency beside it",
             transform=axL.transAxes, color='#2ecc71', fontsize=8.4, va='bottom')

    y = 0.885
    for t, r in pings[:11]:
        axR.text(0.03, y, f"[{t:%H:%M:%S} UTC] 64 bytes from 10.45.0.2: time={r:.0f} ms",
                 transform=axR.transAxes, color='#d8d8d8', fontsize=8.6, family='monospace')
        y -= 0.075
    if pings:
        rr = [r for _, r in pings]
        axR.text(0.03, 0.045,
                 f"sustained ≈{min(rr)/1000:.1f}–{max(rr)/1000:.1f} s per ping",
                 transform=axR.transAxes, color='#e74c3c', fontsize=8.6, va='bottom')

    vals = [v for _, v in sel if v not in (None, 0.0)]
    fig.text(0.015, 0.075,
             f"VERDICT: no degradation signal — reported value {vals[0]:,.0f} where present, "
             f"empty window otherwise", color='#2ecc71', fontsize=10.5, fontweight='bold')
    if pings:
        rr = [r for _, r in pings]
        fig.text(0.015, 0.035,
                 f"REALITY: RTT {min(rr):.0f}–{max(rr):.0f} ms — a QoE collapse the judge never saw",
                 color='#e74c3c', fontsize=10.5, fontweight='bold')
    fig.text(0.985, 0.012, WATERMARK, ha='right', color='#7a7a7a', fontsize=7.5)
    p = f"{outdir}/05_proof_time_aligned.png"
    plt.savefig(p, dpi=150, facecolor='#1c1c1c'); plt.close()
    return p

# ------------------------------------------------------------------ figure 4
# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kpm', required=True); ap.add_argument('--ping', required=True)
    ap.add_argument('--outdir', default='figures')
    a = ap.parse_args()

    import os; os.makedirs(a.outdir, exist_ok=True)
    try:
        import matplotlib; matplotlib.use('Agg')
    except ImportError:
        sys.exit("need matplotlib:  sudo apt install -y python3-matplotlib")

    kpm, ping = parse_kpm(a.kpm), parse_ping(a.ping)
    print(f"make_figures {VERSION}")
    print(f"parsed {len(kpm)} KPM samples, {len(ping)} ping samples")

    rough = sorted(r for _, r in ping)[len(ping)//10]
    t0, t1 = load_window(ping, rough)
    if t0 is None: sys.exit("no sustained load phase found in the ping log")

    # baseline = median of the IDLE phase, not a low percentile of everything
    idle = sorted(r for t, r in ping if t < t0)
    baseline = idle[len(idle)//2] if idle else rough
    dur = (t1 - t0).total_seconds()
    print(f"idle-phase median baseline {baseline:.0f} ms  (n={len(idle)} idle samples)")
    print(f"load window {t0:%H:%M:%S}-{t1:%H:%M:%S} UTC  ({dur:.0f} s)")

    def pct(v, p): return v[int(p * (len(v) - 1))]
    lo = sorted(r for t, r in ping if t0 <= t <= t1)
    print("\n  p95 under different window definitions - reconcile with METHOD.md")
    print("  before publishing any new number:")
    print(f"    detected window       p95 {pct(lo,0.95):7.0f} ms   n={len(lo):3d}   "
          f"{pct(lo,0.95)/baseline:5.0f}x baseline")
    for skip in (10, 20, 30):
        sub = sorted(r for t, r in ping
                     if (t - t0).total_seconds() >= skip and t <= t1)
        if sub:
            print(f"    skipping first {skip:2d} s    p95 {pct(sub,0.95):7.0f} ms   n={len(sub):3d}   "
                  f"{pct(sub,0.95)/baseline:5.0f}x baseline")
    print(f"    max in window {max(lo):.0f} ms\n")

    for p in (fig_hero(kpm, ping, t0, t1, baseline, a.outdir),
              fig_proof(kpm, ping, a.outdir, start_at=t0.replace(second=31, minute=t0.minute))):
        print("wrote", p)

if __name__ == '__main__':
    main()
