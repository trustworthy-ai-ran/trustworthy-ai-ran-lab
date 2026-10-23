# EXP-02C — independent verification of the upstream fix for issue #684

The order-dependent silence found in [EXP-02B](../exp-02b) was reported to the OCUDU
project as issue #684. The maintainers fixed it in merge request !1521, which closes
#684 and contains two commits:

- `f078ab75a5` "e2,kpm: fix style 2 indication readiness": readiness is evaluated
  across all requested metrics; a missing measurement is sent as `noValue`, so metric
  order is preserved.
- `1a1d1feb9b` "e2,kpm: fix RLC metric numeric precision".

The fix is part of the OCUDU 26.10 release (`release_26_10`).

## Method (pre-registered)

Predictions and decision rules were written before any build
([`PREREGISTRATION_unit_test.md`](PREREGISTRATION_unit_test.md)).

- **AFTER:** OCUDU `d0df5e24ff`, a descendant of both commits.
- **BEFORE:** a worktree at `f396a74e7f`, the parent of `f078ab75a5`, with only the
  merge request's two test files copied in. Nothing under `lib/` was changed.
- Same targets built in both trees: `e2sm_kpm_test`, `e2sm_kpm_meas_provider_metrics_test`.

## Result

| Test added by the merge request | Predicted (before) | Before | After |
|---|---|---|---|
| `readiness_and_record_order_are_independent_of_metric_order` | fail | **fail** | pass |
| `indication_is_not_ready_when_all_metrics_are_unavailable` (guard) | pass | **pass** | pass |
| `e2sm_kpm_drb_latency_does_not_overflow_signed_integer` | fail | **fail** | pass |
| `e2sm_kpm_drb_throughput_preserves_fractional_values` | fail (low confidence) | **fail** | pass |

All 17 pre-existing tests passed in both trees; all 21 passed after the fix. Every
prediction held. On the old code the latency test returned −4.3 where 10 was expected,
and the throughput test returned 0 where 0.4 was expected (verbatim assertions in
[`RESULTS.md`](RESULTS.md)). The latency result matches the candidate cause recorded
for [OQ-2](../OPEN_QUESTIONS.md).

## Limits

- Code-level verification, not an end-to-end run: no gNB, UE, RIC or core was
  involved, and no Indication was observed on the wire.
- The tests are the maintainers' own. What is independent is their execution on both
  trees against predictions written in advance, not the test design.
- The full pre-registration file, which also logs the abandoned live-lab attempts, is
  withheld until a separate report to the maintainers is resolved. Its hash is in
  `PREREGISTRATION.sha256`, and it will be published so the hash can be checked.

## Files

| File | Content |
|---|---|
| `PREREGISTRATION_unit_test.md` | the unit-test pre-registration entry, verbatim except one redacted passage |
| `PREREGISTRATION.sha256` | hashes of the full pre-registration file, before data and before the builds |
| `RESULTS.md` | full results, failing assertions and limitations (two passages redacted) |
| `unittest_before.log`, `unittest_after.log` | test runs, both trees |
| `unittest_before_build.log`, `unittest_after_build.log` | build logs, both trees |
