#!/bin/bash
# =====================================================================
# uc07_one.sh (v2) — ONE UC-07 measurement run, then stop.
#
#   ./uc07_one.sh <style> <load_mbps>
#
#   ./uc07_one.sh 2 0        Report Style 2, no load
#   ./uc07_one.sh 2 30       Report Style 2, 30 Mb/s through the RAN
#   ./uc07_one.sh 1 10       Report Style 1, 10 Mb/s
#
# Appends one line to ~/uc07_results.csv and prints the verdict.
# Runs for ~90 s. Designed to be called by hand, ten or thirty times,
# so that a failure costs 90 seconds instead of an hour.
#
# Three things bit the automated version and are handled explicitly here:
#   * `timeout docker exec` kills the client, not the process inside the
#     container - so the xApp is started detached and killed by its
#     container PID
#   * the container image has no /bin/kill - so `sh -c "kill -9 N"` is
#     used, where kill is a shell builtin
#   * a stale submgr record can absorb a new subscription silently - so
#     the Subscription ID is compared against the previous run's
# =====================================================================

set -u
ST="${1:-}"; LOAD="${2:-}"
case "$ST" in 1|2) ;; *) echo "usage: $0 <style 1|2> <load Mb/s>"; exit 1;; esac
case "$LOAD" in ''|*[!0-9]*) echo "usage: $0 <style 1|2> <load Mb/s>"; exit 1;; esac

RIC="$HOME/oran-sc-ric"
NODE="gnbd_208_093_00019b_0"
XAPP="/opt/xApps/kpm_mon_xapp.py"
WIN=70
OUT="$HOME/uc07_runs"; mkdir -p "$OUT"
CSV="$HOME/uc07_results.csv"
[ -f "$CSV" ] || echo "utc,style,load_mbps,indications,span_s,median_gap_s,min_gap,max_gap,subid,valid,flags" > "$CSV"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TAG="s${ST}_${LOAD}mbps_${STAMP}"
LOG="$OUT/${TAG}.log"
IPF="$OUT/${TAG}.iperf"

sudo -v || exit 1
cd "$RIC" || exit 1

subs ()  { docker compose exec -T submgr curl -s localhost:8088/ric/v1/subscriptions 2>/dev/null; }
orph ()  { docker top python_xapp_runner 2>/dev/null | awk '/kpm_mon/{print $2}'; }
killx () { local p; for p in $(orph); do
             docker exec -u root python_xapp_runner sh -c "kill -9 $p" 2>/dev/null; done; }

echo "=========================================================="
echo " UC-07 single run   Style $ST   ${LOAD} Mb/s   $STAMP"
echo "=========================================================="

# ---- 1. clear the decks --------------------------------------------
killx; sleep 2
if [ -n "$(orph)" ]; then
    echo "  orphan survived kill - restarting the xApp container"
    docker compose restart python_xapp_runner >/dev/null 2>&1; sleep 12
fi
for id in $(subs | grep -o '"SubscriptionId":[0-9]*' | cut -d: -f2); do
    docker compose exec -T submgr curl -s -X DELETE "localhost:8088/ric/v1/subscriptions/$id" >/dev/null 2>&1
done
sleep 2

# The REST DELETE does not remove the Redis records, and restarting submgr
# re-reads them, so a record with "SubscriptionInstances": null survives both
# and silently absorbs the next identical subscription. Delete the two keys
# directly. Never use FLUSHALL: it also drops the E2 node registration and
# forces a full gNB restart.  (Characterised 31 Jul 2026.)
if [ "$(subs)" != "[]" ]; then
    echo "  stale subscription present - clearing submgr keys in redis"
    for k in $(docker exec ric_dbaas redis-cli KEYS '*' 2>/dev/null | grep -E 'submgr_(e2|rest)SubsDb'); do
        docker exec ric_dbaas redis-cli DEL "$k" >/dev/null 2>&1
    done
    docker compose restart submgr >/dev/null 2>&1
    sleep 12
fi

BEFORE=$(subs)
echo "  subscriptions before run: $BEFORE"
[ "$BEFORE" = "[]" ] || echo "  WARNING: could not clear subscriptions - this run will be invalid"

# ---- 2. load --------------------------------------------------------
IPERF_PID=""
if [ "$LOAD" -gt 0 ]; then
    sudo ip netns exec ue1 iperf3 -c 10.45.0.2 -u -b "${LOAD}M" -l 1200 -t $((WIN+20)) -R > "$IPF" 2>&1 &
    IPERF_PID=$!
    sleep 10
    grep -q "local 10.60\." "$IPF" 2>/dev/null \
        && echo "  load running, client on $(grep -o 'local 10\.60\.[0-9.]*' "$IPF" | head -1)" \
        || echo "  WARNING: no 10.60.x client socket yet"
else
    echo "  no load (idle run)"
fi

# ---- 3. measure -----------------------------------------------------
echo "  measuring for ${WIN} s ..."
T0=$(date +%s)
docker exec python_xapp_runner python3 -u "$XAPP" \
    --e2_node_id "$NODE" --kpm_report_style "$ST" \
    $( [ "$ST" -eq 2 ] && echo "--ue_ids 0" ) --metrics "DRB.UEThpDl" 2>&1 \
  | python3 -u -c "
import sys,time
for l in sys.stdin: sys.stdout.write(f'{time.time():.3f} {l}'); sys.stdout.flush()" > "$LOG" &
PIPE_PID=$!

sleep "$WIN"
killx                      # stop the xApp inside the container
sleep 2
kill "$PIPE_PID" 2>/dev/null; wait "$PIPE_PID" 2>/dev/null
T1=$(date +%s); ELAPSED=$(( T1 - T0 ))

if [ -n "$IPERF_PID" ]; then kill "$IPERF_PID" 2>/dev/null; wait "$IPERF_PID" 2>/dev/null; fi
sudo pkill -f "iperf3 -c 10.45.0.2" 2>/dev/null

# ---- 4. analyse -----------------------------------------------------
SUBID=$(grep -o "Subscription ID: *[A-Za-z0-9]*" "$LOG" | head -1 | awk '{print $NF}')
PREV=$(tail -n +2 "$CSV" | tail -1 | cut -d, -f9)

read -r N SPAN MED MN MX <<< "$(python3 - "$LOG" <<'PY'
import sys, re
t=[float(m.group(1)) for m in
   (re.match(r'^(\d+\.\d+)\s.*RIC Indication Received', l) for l in open(sys.argv[1], errors='replace')) if m]
if len(t) > 1:
    g=sorted(round(t[i+1]-t[i],3) for i in range(len(t)-1))
    print(len(t), round(t[-1]-t[0],1), g[len(g)//2], g[0], g[-1])
else:
    print(len(t), 0, 0, 0, 0)
PY
)"

FLAGS=""; VALID=1
[ "$N" -lt 10 ] && { FLAGS="${FLAGS}FEW-IND "; VALID=0; }
[ "$ELAPSED" -lt 60 ] && { FLAGS="${FLAGS}SHORT "; VALID=0; }
[ -n "$SUBID" ] && [ "$SUBID" = "$PREV" ] && { FLAGS="${FLAGS}SUBID-REPEAT "; VALID=0; }
grep -qE "ApiException|Traceback|Address already in use" "$LOG" && { FLAGS="${FLAGS}XAPP-ERROR "; VALID=0; }
if [ "$LOAD" -gt 0 ]; then
    grep -q "local 10.60\." "$IPF" 2>/dev/null || { FLAGS="${FLAGS}NO-RAN-TRAFFIC "; VALID=0; }
fi
[ -z "$FLAGS" ] && FLAGS="ok"

echo "$STAMP,$ST,$LOAD,$N,$SPAN,$MED,$MN,$MX,$SUBID,$VALID,$FLAGS" >> "$CSV"

echo
echo "  indications   : $N over ${SPAN}s"
echo "  median gap    : ${MED}s   (min ${MN}, max ${MX})"
echo "  subscription  : ${SUBID:-none}"
if [ "$VALID" -eq 1 ]; then
    echo -e "  \033[1;32mVALID\033[0m"
else
    echo -e "  \033[1;31mINVALID\033[0m  $FLAGS"
    echo "  This run is recorded but must not be interpreted. Repeat it."
fi
echo
echo "  results so far:"
column -s, -t "$CSV" | sed 's/^/    /'
