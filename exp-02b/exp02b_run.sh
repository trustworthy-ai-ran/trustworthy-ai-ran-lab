#!/bin/bash
# EXP-02B — metric order dependency in E2SM-KPM Report Style 2
# Pre-registered. Do not edit run definitions after first execution.

set -u

NODE="gnbd_208_093_00019b_0"
OUT="$HOME/exp02b"
WINDOW=60          # measurement window, seconds
SETTLE=15          # subscription teardown gap between runs

mkdir -p "$OUT"
STAMP=$(date +%Y%m%d_%H%M%S)
SUMMARY="$OUT/summary_$STAMP.txt"

echo "EXP-02B  $STAMP" | tee "$SUMMARY"
echo "node=$NODE  window=${WINDOW}s  settle=${SETTLE}s" | tee -a "$SUMMARY"
echo "" | tee -a "$SUMMARY"

run () {
    local name="$1"; local metrics="$2"; local predict="$3"

    echo "--- RUN $name  [$metrics]  predicted: $predict"

    # ensure no residual xApp / subscription
    sudo docker exec python_xapp_runner pkill -f kpm_mon_xapp >/dev/null 2>&1
    sleep "$SETTLE"

    timeout $((WINDOW + 10)) sudo docker exec python_xapp_runner \
        python3 /opt/xApps/kpm_mon_xapp.py \
        --e2_node_id "$NODE" \
        --kpm_report_style 2 \
        --ue_ids 0 \
        --metrics "$metrics" \
        > "$OUT/run_${name}_$STAMP.log" 2>&1

    local n
    n=$(grep -c "RIC Indication Received" "$OUT/run_${name}_$STAMP.log" || true)
    printf "%-4s %-40s predicted=%-4s observed=%s\n" \
        "$name" "$metrics" "$predict" "$n" | tee -a "$SUMMARY"
}

# P  — positive control. Proves the whole chain works in THIS session.
#      If P is zero, nothing below is interpretable. Stop and fix.
run P  "DRB.UEThpDl"                        ">0"

# A1 — reproduce the original EXP-02 failure, same session
run A1 "DRB.UEThpDl,DRB.RlcSduDelayDl"      "0"

# B  — primary test. Same metrics, order swapped.
run B  "DRB.RlcSduDelayDl,DRB.UEThpDl"      ">0"

# A2 — reversibility
run A2 "DRB.UEThpDl,DRB.RlcSduDelayDl"      "0"

# C  — discriminator. A non-existent metric can never produce a value,
#      so it cannot break an encoder. If C is also zero, the encoding
#      hypothesis is dead and only the readiness-check remains.
run C  "DRB.UEThpDl,DRB.FakeMetric123"      "0"

sudo docker exec python_xapp_runner pkill -f kpm_mon_xapp >/dev/null 2>&1

echo "" | tee -a "$SUMMARY"
echo "Analysis rule (locked): H1 confirmed iff P>0, A1=0, B>0, A2=0." | tee -a "$SUMMARY"
echo "Run C is diagnostic, not part of the confirmation rule." | tee -a "$SUMMARY"
echo "" | tee -a "$SUMMARY"
echo "Logs: $OUT" | tee -a "$SUMMARY"
