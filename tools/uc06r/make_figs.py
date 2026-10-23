"""UC-06R figures. RTT and KPM values are computed from the raw logs by stats.py.
Fig. 3 (EXP-02B, July 2026) uses the counts recorded in exp-02b/RESULTS.md.
Run: python3 tools/uc06r/make_figs.py && python3 tools/uc06r/make_timeseries.py
"""
import matplotlib
import stats as _stats
S = _stats.compute()
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import os

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "uc06r-replication", "figures"))
os.makedirs(OUT, exist_ok=True)

INK, INK2, MUTED, RULE = "#15171C", "#454A54", "#5E636C", "#D9D4C8"
BLUE, ORANGE, IDLE = "#1F4E99", "#C4480F", "#8A8F98"
HATCH_EDGE = "#5E636C"

plt.rcParams.update({
    "font.family": "STIXGeneral", "mathtext.fontset": "stix",
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "pdf.fonttype": 42, "ps.fonttype": 42, "hatch.linewidth": 0.6,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})

def clean(ax, grid_axis="x"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid_axis:
        ax.grid(axis=grid_axis, color="#E6E1D6", linewidth=0.5)
        ax.set_axisbelow(True)

def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=220)
    plt.close(fig)

# ---------------------------------------------------------------- Fig. 1 architecture
def box(ax, x, y, w, h, title, sub=None, edge=MUTED, lw=0.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                fc="white", ec=edge, lw=lw))
    ty = y + h - 2.6
    ax.text(x + w / 2, ty, title, ha="center", va="top", fontsize=8, color=INK, fontweight="bold")
    if sub:
        ax.text(x + w / 2, ty - 3.6, sub, ha="center", va="top", fontsize=7, color=INK2, linespacing=1.15)

def arrow(ax, x0, y0, x1, y1, color=MUTED, label=None, lx=None, ly=None, both=False, lcolor=None):
    style = "<|-|>" if both else "-|>"
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color, lw=1.0, shrinkA=0, shrinkB=0,
                                mutation_scale=7))
    if label:
        ax.text(lx if lx is not None else (x0 + x1) / 2, ly if ly is not None else (y0 + y1) / 2 + 1.6,
                label, ha="center", va="bottom", fontsize=6.8, color=lcolor or color)

fig, ax = plt.subplots(figsize=(7.16, 2.05))
ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")
# user-plane row
box(ax, 0.5, 23, 15, 15, "iperf3 server", "N6 side\nUDP, 30 Mb/s DL")
box(ax, 20.5, 23, 16, 15, "free5GC core", "AMF, SMF, UPF\n(native)")
box(ax, 41.5, 23, 25, 15, "srsRAN Project gNB", "commit d2f4b70dda", edge=ORANGE, lw=1.0)
for i in range(8):
    ax.add_patch(Rectangle((44.0 + i * 1.7, 24.8), 1.2, 3.6, fc=ORANGE, ec="none"))
ax.text(58.2, 26.6, "RLC queue\n(DU-local)", ha="left", va="center", fontsize=6.6, color=ORANGE, linespacing=1.1)
box(ax, 76.5, 23, 23, 15, "srsUE (single UE)", "ICMP probe every 200 ms\n= user-side witness")
arrow(ax, 15.5, 30.5, 20.5, 30.5, label="N6", ly=31.2)
arrow(ax, 36.5, 30.5, 41.5, 30.5, label="N3", ly=31.2)
arrow(ax, 66.5, 30.5, 76.5, 30.5, label="ZMQ radio", ly=31.2, both=True)
# telemetry row
box(ax, 41.5, 1, 25, 13, "O-RAN SC Near-RT RIC", "i-release, 7 containers", edge=BLUE)
box(ax, 76.5, 1, 23, 13, "kpm_mon xApp", "E2SM-KPM Report Style 2\n= the “judge”", edge=BLUE, lw=1.0)
arrow(ax, 54, 23, 54, 14, color=BLUE)
ax.text(55.2, 18.5, "E2 / E2SM-KPM", ha="left", va="center", fontsize=6.8, color=BLUE)
arrow(ax, 66.5, 7.5, 76.5, 7.5, color=BLUE, label="Indication", ly=8.2)
ax.text(1, 12.8, "Telemetry path (blue): what an AI agent on the RIC sees.", fontsize=7, color=INK2, va="top")
ax.text(1, 8.3, "User-plane path (top): where the queue forms.", fontsize=7, color=INK2, va="top")
ax.text(1, 3.8, "Both are recorded with timestamps in every run.", fontsize=7, color=INK2, va="top")
save(fig, "fig1_testbed")

# ---------------------------------------------------------------- Fig. 2 protocol
fig, ax = plt.subplots(figsize=(3.5, 0.95))
segs = [(0, 120, "#E6E1D6", "idle, 120 s", INK), (120, 120, ORANGE, "load, 120 s", "white"),
        (240, 60, "#E6E1D6", "idle, 60 s", INK)]
for x0, w, c, lab, tc in segs:
    ax.add_patch(Rectangle((x0 + 1, 0), w - 2, 1, fc=c, ec="none"))
    ax.text(x0 + w / 2, 0.5, lab, ha="center", va="center", fontsize=7.5, color=tc)
ax.set_xlim(0, 300); ax.set_ylim(-0.05, 1.05)
ax.set_yticks([]); ax.set_xticks([0, 60, 120, 180, 240, 300])
ax.set_xlabel("time from xApp subscription and probe start (s)")
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
save(fig, "fig2_protocol")

# ---------------------------------------------------------------- Fig. 3 EXP-02B
fig, ax = plt.subplots(figsize=(3.5, 1.75))
labels = ["W1\nThp", "W2\nThp, Delay", "W3\nDelay, Thp", "W4\nThp, Delay", "W5\nThp, Fake"]
vals = [24, 0, 24, 0, 0]
xs = range(len(vals))
for x, v in zip(xs, vals):
    if v > 0:
        ax.bar(x, v, width=0.5, color=BLUE)
        ax.text(x, v + 0.8, str(v), ha="center", va="bottom", fontsize=7.5, color=INK)
    else:
        ax.plot([x - 0.25, x + 0.25], [0, 0], color=ORANGE, lw=2.2, solid_capstyle="butt")
        ax.text(x, 1.0, "0", ha="center", va="bottom", fontsize=7.5, color=INK)
ax.set_xticks(list(xs)); ax.set_xticklabels(labels, fontsize=7)
ax.set_ylim(0, 29); ax.set_yticks([0, 10, 20])
ax.set_ylabel("RIC Indications / 60 s")
clean(ax, "y")
save(fig, "fig3_exp02b")

# ---------------------------------------------------------------- Fig. 4 RTT, all six loaded runs (raw-log values)
runs = ["A1", "A2", "A3", "B1", "B2", "C1"]
idle_med = [S[r]["rtt_idle"]["median"] for r in runs]; load_med = [S[r]["rtt_load"]["median"] for r in runs]
load_p95 = [S[r]["rtt_load"]["p95"] for r in runs]; infl = [S[r]["inflation"] for r in runs]
fig, ax = plt.subplots(figsize=(3.5, 2.0))
n = len(runs)
for i, r in enumerate(runs):
    y = n - 1 - i
    ax.plot([idle_med[i], load_med[i]], [y, y], color=RULE, lw=1.6, zorder=1)
    ax.scatter(idle_med[i], y, s=24, color=IDLE, edgecolor="white", linewidth=0.8, zorder=3,
               label="pre-load idle, median" if i == 0 else None)
    ax.scatter(load_med[i], y, s=24, color=ORANGE, edgecolor="white", linewidth=0.8, zorder=3,
               label="under load, median" if i == 0 else None)
    ax.scatter(load_p95[i], y, s=20, marker="D", facecolor="white", edgecolor=ORANGE, linewidth=1.0,
               zorder=3, label="under load, p95" if i == 0 else None)
    ax.text(5300, y, "\u00d7%d" % int(infl[i] + 0.5), va="center", ha="left",
            fontsize=8, color=INK, fontweight="bold")
ax.axhline(2.5, color=RULE, lw=0.6)
ax.set_xscale("log"); ax.set_xlim(20, 5000)
ax.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000])
ax.set_xticklabels(["20", "50", "100", "200", "500", "1k", "2k", "5k"])
ax.set_yticks(list(range(n - 1, -1, -1))); ax.set_yticklabels(runs); ax.set_ylim(-0.6, n - 0.4)
ax.set_xlabel("round-trip time from the UE (ms, log scale)")
clean(ax, "x")
ax.legend(loc="upper center", bbox_to_anchor=(0.45, 1.22), ncol=3, frameon=False, handletextpad=0.3,
          columnspacing=1.0)
save(fig, "fig4_rtt")

# ---------------------------------------------------------------- Fig. 5 throughput KPM in load window
def _row(r):
    d = S[r]["DRB.UEThpDl|load"]
    note = ("%.1f Mb/s rx; median %.1fk" % (S[r]["rx_mbps"], d["median"] / 1000)) if d["nonzero"] else ("%.1f Mb/s rx; 0.0 throughout" % S[r]["rx_mbps"])
    return (r, d["nonzero"], d["zero"], note)
rows = [_row(r) for r in ("A1", "A2", "A3", "C1")]
fig, ax = plt.subplots(figsize=(3.5, 1.45))
for i, (lab, nz, z, note) in enumerate(rows):
    y = 3 - i
    if nz:
        ax.barh(y, nz, height=0.52, color=BLUE, label="non-zero value" if i == 1 else None)
    if z:
        ax.barh(y, z, height=0.52, color="white", edgecolor=HATCH_EDGE, hatch="////", linewidth=0.6,
                label="0.0" if i == 0 else None)
    ax.text(61, y, note, va="center", ha="left", fontsize=7, color=INK2)
ax.set_yticks([3, 2, 1, 0]); ax.set_yticklabels([r[0] for r in rows])
ax.set_xlim(0, 60); ax.set_xticks([0, 20, 40, 56])
ax.set_xlabel("DRB.UEThpDl reports inside the load window")
clean(ax, "x")
ax.legend(loc="upper center", bbox_to_anchor=(0.45, 1.3), ncol=2, frameon=False)
save(fig, "fig5_thp_load")

# ---------------------------------------------------------------- Fig. 7 failure-mode matrix
modes = ["Blind", "Stuck", "Void", "Silent"]
runs = ["A1", "A2", "A3", "B1", "B2", "C1"]
hits = {("A1", "Stuck"), ("A2", "Blind"), ("A3", "Blind"), ("B1", "Silent"), ("B2", "Silent"),
        ("C1", "Stuck"), ("C1", "Void")}
fig, ax = plt.subplots(figsize=(3.5, 1.55))
for i, r in enumerate(runs):
    for j, m in enumerate(modes):
        if (r, m) in hits:
            ax.scatter(j, -i, s=60, color=INK, zorder=3)
        else:
            ax.scatter(j, -i, s=14, facecolor="white", edgecolor=RULE, linewidth=0.8, zorder=3)
ax.set_xticks(range(len(modes))); ax.set_xticklabels(modes)
ax.xaxis.tick_top()
ax.set_yticks([-i for i in range(len(runs))]); ax.set_yticklabels(runs)
ax.set_xlim(-0.6, len(modes) - 0.4); ax.set_ylim(-len(runs) + 0.4, 0.6)
for s in ("top", "right", "bottom", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(length=0)
save(fig, "fig7_modes")
print("ok", sorted(os.listdir(OUT)))
