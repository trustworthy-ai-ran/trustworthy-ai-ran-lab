# EXP-02C — pre-registration excerpt (unit-test method)

This is the entry `EXP-02C METHOD CHANGE (2026-09-23)` from the experiment's
`PREREGISTRATION.md`, copied verbatim except for one passage marked `[redacted]`.
It was written before any unit-test build or run. The hash of the full file at that
moment is recorded in `PREREGISTRATION.sha256`
(`5b472244f3a3212e0063dda96ecd1a847a54d0fdcf94600db75dbb4b5b4c47c5`). The full file
also logs the abandoned live-lab attempts and is withheld until a separate report to
the OCUDU maintainers is resolved; it will then be published so the hash can be checked.

```text
=== EXP-02C METHOD CHANGE (2026-09-23, written before any build/run) ===
Live-lab protocol ABANDONED: [redacted: the live-lab protocol could not be completed on the OCUDU
  build in this testbed; details withheld pending a separate report to the maintainers]; unrelated
  to the fix under test. Runs 1 and 2 not performed.
  RIC and core are down and stay down for this method.
Ordering note: step 2 (read-only git history inspection to identify commits/targets) ran before this
  pre-registration was written. No test was built or run before this entry.
New method: unit-test verification of the #684 fix (MR commits f078ab75a5 + 1a1d1feb9b). No gNB/UE/RIC/core.
  AFTER  = ~/ocudu-fix @ d0df5e24ff7d55c7cf705a504d0520b1cd3ccd46, existing build dir (RelWithDebInfo).
  BEFORE = git worktree ~/ocudu-prefix @ f396a74e7fbf621d94a9e624d24ed6c312ff40a3 (parent of f078ab75a5),
           separate build dir, same flags; ONLY tests/unittests/e2/{e2sm_kpm_test,e2sm_kpm_meas_provider_metrics_test}.cpp
           copied from AFTER (verified: parent->HEAD diff of these files = MR additions only, +165 lines).
           lib/ untouched. If the copied tests need a header/helper absent from BEFORE: stop and report.
  Targets: e2sm_kpm_test, e2sm_kpm_meas_provider_metrics_test. Logs: unittest_after.log, unittest_before.log.
Predictions (per test):
  e2sm_kpm_report_service_style2_test.readiness_and_record_order_are_independent_of_metric_order:
    BEFORE FAIL, AFTER PASS. Direct #684 test (metric-order dependence).
  e2sm_kpm_report_service_style2_test.indication_is_not_ready_when_all_metrics_are_unavailable:
    BEFORE PASS (predicted), AFTER PASS. Old code checks only the last metric; if all are unavailable the
    last one is too, so old code also returns not-ready. Regression guard, not a bug detector.
  e2sm_kpm_meas_provider_metrics_test.e2sm_kpm_drb_latency_does_not_overflow_signed_integer:
    BEFORE FAIL, AFTER PASS.
  e2sm_kpm_meas_provider_metrics_test.e2sm_kpm_drb_throughput_preserves_fractional_values:
    BEFORE FAIL (LOW confidence; depends on whether float loses the tested fraction), AFTER PASS.
  All pre-existing tests in both binaries: PASS in BEFORE and AFTER.
Decision rules (reported separately):
  #684 fix confirmed iff readiness_and_record_order_are_independent_of_metric_order FAILS on BEFORE
    AND every test in both binaries PASSES on AFTER.
  RLC precision fix (1a1d1feb) confirmed iff at least e2sm_kpm_drb_latency_does_not_overflow_signed_integer
    FAILS on BEFORE and PASSES on AFTER.
  A mismatch on the low-confidence (throughput) or guard (all-unavailable) predictions is reported as a
    mismatch, not hidden, and does not by itself void the #684 result.
  A BEFORE compile failure is not a FAIL: stop and report, no lib/ edits.
```
