#!/bin/bash
# =====================================================================
# labcheck v3 — read-only health report for the Trustworthy AI-RAN lab
#
# Changes nothing. Starts nothing. Kills nothing.
# Run it any time to find out whether the lab is ready for an experiment,
# and if not, exactly which layer is broken.
#
#   ./labcheck.sh
#
# Every check that matters for running a KPM experiment is here, in the
# order the layers depend on each other. Checks marked BLOCKING must pass
# before any subscription will work.
# =====================================================================

RIC="$HOME/oran-sc-ric"
NODE="gnbd_208_093_00019b_0"
PASS=0; WARN=0; FAIL=0

g () { echo -e "  \033[1;32m PASS \033[0m $*"; PASS=$((PASS+1)); }
y () { echo -e "  \033[1;33m WARN \033[0m $*"; WARN=$((WARN+1)); }
r () { echo -e "  \033[1;31m FAIL \033[0m $*"; FAIL=$((FAIL+1)); }
h () { echo -e "\n\033[1;36m$*\033[0m"; }
n () { echo -e "         $*"; }

echo "======================================================================"
echo " Lab health check  —  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "======================================================================"

# ---------------------------------------------------------------- host
h "HOST"
UP=$(uptime -p 2>/dev/null); n "uptime: ${UP:-unknown}"
MEMF=$(free -g | awk '/^Mem:/{print $7}')
[ "${MEMF:-0}" -ge 4 ] && g "free memory ${MEMF} GB" || y "only ${MEMF} GB free memory"
DISK=$(df -h "$HOME" | awk 'NR==2{print $4" free ("$5" used)"}'); n "disk: $DISK"
lsmod | grep -q gtp5g && g "gtp5g kernel module loaded" \
                      || r "gtp5g NOT loaded  ->  sudo modprobe gtp5g   [BLOCKING]"

# ---------------------------------------------------------------- core
h "5G CORE  (free5GC, native processes)"
for nf in nrf amf smf upf ausf udm; do
    # free5GC starts UPF under "sudo -E", so pgrep sees 3 PIDs for 1 instance.
    # Count only cmdlines that start with ./bin/<nf>, ignoring the sudo wrappers.
    C=$(pgrep -af "bin/$nf" | grep -v " sudo " | wc -l)
    case "$C" in
        0) r "$nf not running   [BLOCKING]" ;;
        1) g "$nf running (1 instance)" ;;
        *) r "$nf has $C instances - duplicates cause RRC Release   [BLOCKING]" ;;
    esac
done
LOGD=$(ls -dt "$HOME"/free5gc/log/*/ 2>/dev/null | head -1)
[ -n "$LOGD" ] && n "newest core log dir: $(basename "$LOGD")"

# ----------------------------------------------------------------- ric
h "NEAR-RT RIC  (docker)"
if ! docker info >/dev/null 2>&1; then
    r "docker not responding   [BLOCKING]"
else
    RUNNING=$(docker ps --format '{{.Names}}')
    for c in ric_dbaas ric_e2term ric_e2mgr ric_submgr ric_appmgr ric_rtmgr_sim python_xapp_runner; do
        echo "$RUNNING" | grep -qx "$c" && g "$c up" || r "$c DOWN   [BLOCKING]"
    done
    if echo "$RUNNING" | grep -qx ric_dbaas; then
        P=$(docker exec ric_dbaas redis-cli ping 2>/dev/null)
        [ "$P" = "PONG" ] && g "redis answering" || r "redis not answering   [BLOCKING]"
    fi
fi

# ------------------------------------------------------------------ ran
h "RAN"
GN=$(pgrep -f "apps/gnb/gnb" | wc -l)
case "$GN" in
    0) r "gNB not running   [BLOCKING]" ;;
    1) g "gNB running" ;;
    *) r "gNB has $GN instances   [BLOCKING]" ;;
esac
UN=$(pgrep -f "srsue" | wc -l)
case "$UN" in
    0) r "srsUE not running   [BLOCKING]" ;;
    1) g "srsUE running" ;;
    *) r "srsUE has $UN instances   [BLOCKING]" ;;
esac
for p in 2000 2001; do
    sudo ss -tlnp 2>/dev/null | grep -q ":$p " && g "ZMQ port $p bound (radio link live)" \
                                               || y "ZMQ port $p not bound"
done

# ------------------------------------------------------------ data path
h "DATA PATH"
if sudo ip netns list 2>/dev/null | grep -q ue1; then
    g "netns ue1 exists"
    if sudo ip netns exec ue1 ip -br addr 2>/dev/null | grep -q tun_srsue; then
        IP=$(sudo ip netns exec ue1 ip -4 -br addr show tun_srsue 2>/dev/null | awk '{print $3}')
        g "tun_srsue up  ${IP}"
    else
        r "tun_srsue missing - no PDU session   [BLOCKING]"
    fi
    sudo ip netns exec ue1 ip route 2>/dev/null | grep -q default \
        && g "default route present in ue1" \
        || r "no default route in ue1   [BLOCKING]"
else
    r "netns ue1 missing   [BLOCKING]"
fi
sudo ip netns list 2>/dev/null | grep -q srv && g "netns srv exists" || r "netns srv missing   [BLOCKING]"
sudo ip netns exec srv ss -tlnp 2>/dev/null | grep -q 5201 \
    && g "iperf3 server listening on 10.45.0.2" \
    || y "iperf3 server not listening  ->  sudo ip netns exec srv iperf3 -s -D"

echo
if sudo ip netns exec ue1 ping -c3 -W2 10.45.0.2 >/tmp/_lc_ping 2>&1; then
    RTT=$(awk -F'/' '/rtt/{printf "%.0f ms avg", $5}' /tmp/_lc_ping)
    g "UE -> N6 reachable  ($RTT)"
    n "$(grep 'rtt min' /tmp/_lc_ping)"
else
    r "UE cannot reach 10.45.0.2   [BLOCKING]"
fi

# ------------------------------------------------------------------- e2
h "E2 INTERFACE"
if docker ps --format '{{.Names}}' | grep -qx ric_e2mgr; then
    ST=$(cd "$RIC" && docker compose exec -T e2mgr curl -s localhost:3800/v1/nodeb/states 2>/dev/null)
    if echo "$ST" | grep -q '"connectionStatus":"CONNECTED"'; then
        g "e2mgr reports node CONNECTED"
    elif echo "$ST" | grep -q DISCONNECTED; then
        r "e2mgr reports DISCONNECTED - restart gNB to re-send E2 Setup   [BLOCKING]"
    else
        r "e2mgr knows no E2 node   [BLOCKING]"
    fi
fi

SUBS=$(cd "$RIC" && docker compose exec -T submgr curl -s localhost:8088/ric/v1/subscriptions 2>/dev/null)
if [ "$SUBS" = "[]" ]; then
    g "subscription list empty - clean slate"
elif echo "$SUBS" | grep -q '"SubscriptionInstances":null'; then
    r "STALE SUBSCRIPTION with SubscriptionInstances:null   [BLOCKING]"
    n "This record swallows every new subscription and routes"
    n "Indications to a dead endpoint. Known lab defect, 30 Jul 2026."
    n "$SUBS"
elif [ -n "$SUBS" ]; then
    y "subscriptions present (may be legitimate if an xApp is running)"
    n "$SUBS"
fi

# Use docker top rather than a shell inside the container: a shell would
# carry the search pattern in its own cmdline and report itself as an orphan.
# (That false positive cost real debugging time on 30-31 Jul 2026.)
ORPH=$(docker top python_xapp_runner 2>/dev/null | awk '/kpm_mon/{print $2}' | tr '\n' ' ')
if [ -z "$ORPH" ]; then
    g "no orphaned xApp processes"
else
    r "orphaned xApp PIDs: $ORPH   [BLOCKING]"
    n "They hold the HTTP port; new xApps fail with 'Address already in use'."
    n "Fix: cd $RIC && docker compose restart python_xapp_runner"
fi

# ------------------------------------------------------------- log perms
h "LOG FILE PERMISSIONS"
for f in /tmp/gnb_srsran.log /tmp/ue_srsran.log; do
    if [ ! -e "$f" ]; then
        y "$f does not exist (will be created)"
    elif [ -w "$f" ]; then
        g "$(basename $f) writable"
    else
        r "$(basename $f) NOT writable - owned by $(stat -c %U "$f")"
        n "Fix: sudo chmod 666 $f"
    fi
done

# ----------------------------------------------------------------- verdict
echo
echo "======================================================================"
if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
    echo -e " \033[1;32mLAB READY\033[0m   $PASS checks passed"
elif [ "$FAIL" -eq 0 ]; then
    echo -e " \033[1;33mLAB USABLE\033[0m   $PASS passed, $WARN warnings - read them before running"
else
    echo -e " \033[1;31mLAB NOT READY\033[0m   $FAIL failures, $WARN warnings, $PASS passed"
    echo "  Fix the BLOCKING items above, top to bottom. Layer order matters:"
    echo "  core -> RIC -> gNB -> UE -> network."
fi
echo "======================================================================"
[ "$FAIL" -eq 0 ]
