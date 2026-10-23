# EXP-02C — Results (unit-test verification of the #684 fix)

Written 2026-09-23. Predictions and decision rules were pre-registered in
`PREREGISTRATION.md` (entry "EXP-02C METHOD CHANGE (2026-09-23)") before any
build or run. The file's hash at that point is recorded in `PREREGISTRATION.sha256`:
`5b472244f3a3212e0063dda96ecd1a847a54d0fdcf94600db75dbb4b5b4c47c5`.

> **Public-release note (2026-10-23).** The entry above is published verbatim in
> `PREREGISTRATION_unit_test.md`, except for one redacted passage. The full
> `PREREGISTRATION.md`, which the hash covers, also logs the abandoned live-lab
> attempts; it is withheld until a separate report to the OCUDU maintainers is
> resolved, and will then be published so the hash can be checked. Two passages
> of this file are redacted for the same reason and marked `[redacted]`.

## Method

The live-lab protocol could not be completed on the OCUDU build in this testbed
[redacted: details withheld pending a separate report to the maintainers]. This run
verifies the fix at unit-test level
instead, with no gNB, UE, RIC or core.

- **MR commits under test** (in `~/ocudu-fix`, branch `dev`):
  - `f078ab75a5b3ab3d7cc54ed2d2393058761e1034` "e2,kpm: fix style 2 indication readiness"
  - `1a1d1feb9bc1ee995c3695ea5662559019ea183c` "e2,kpm: fix RLC metric numeric precision"
- **AFTER** = `~/ocudu-fix` @ `d0df5e24ff7d55c7cf705a504d0520b1cd3ccd46` (HEAD, a
  descendant of both MR commits), existing build dir, RelWithDebInfo, `ENABLE_WERROR=OFF`.
- **BEFORE** = git worktree `~/ocudu-prefix` @ `f396a74e7fbf621d94a9e624d24ed6c312ff40a3`
  (the parent of `f078ab75a5`), fresh separate build dir with the same flags. The
  only files copied from AFTER are `tests/unittests/e2/e2sm_kpm_test.cpp` and
  `tests/unittests/e2/e2sm_kpm_meas_provider_metrics_test.cpp`. The parent→HEAD diff
  of these two files is exactly the MR's additions (+165 lines, no other drift).
  Nothing under `lib/` was touched, `tests/unittests/e2/CMakeLists.txt` is identical
  in both trees, and every include in the copied tests exists in the old tree.
- **Targets:** `e2sm_kpm_test` and `e2sm_kpm_meas_provider_metrics_test`, built with
  `make -j7`. Each binary was run directly with `--gtest_color=no`.
- **Logs:**
  - Build: `unittest_after_build.log` (1m14s, exit 0) and `unittest_before_build.log`
    (6m41s, exit 0). Neither build had errors or warnings.
  - Run: `unittest_after.log` (both binaries exit 0) and `unittest_before.log`
    (both binaries exit 1).
- **Order of work:** the git-history inspection that identified the commits and
  targets ran before the pre-registration. No test was built or run before it.

## Per-test results

### The 4 MR-added tests

| Test | Fix | Predicted BEFORE | BEFORE | Predicted AFTER | AFTER |
|---|---|---|---|---|---|
| `e2sm_kpm_report_service_style2_test.readiness_and_record_order_are_independent_of_metric_order` | f078ab75 (#684) | FAIL | **FAIL** | PASS | PASS |
| `e2sm_kpm_report_service_style2_test.indication_is_not_ready_when_all_metrics_are_unavailable` | f078ab75 (guard) | PASS | **PASS** | PASS | PASS |
| `e2sm_kpm_meas_provider_metrics_test.e2sm_kpm_drb_latency_does_not_overflow_signed_integer` | 1a1d1feb (RLC) | FAIL | **FAIL** | PASS | PASS |
| `e2sm_kpm_meas_provider_metrics_test.e2sm_kpm_drb_throughput_preserves_fractional_values` | 1a1d1feb (RLC) | FAIL (low confidence) | **FAIL** | PASS | PASS |

### Pre-existing tests

All 17 passed in both BEFORE and AFTER, as predicted: 6 in `e2sm_kpm_test` and
11 in `e2sm_kpm_meas_provider_metrics_test`. No test was skipped or disabled.

| Binary | BEFORE | AFTER |
|---|---|---|
| `e2sm_kpm_test` | 7 passed, 1 failed | 8/8 passed |
| `e2sm_kpm_meas_provider_metrics_test` | 11 passed, 2 failed | 13/13 passed |

**Prediction mismatches: none.**

## Failing assertions in BEFORE (verbatim, from `unittest_before.log`)

### `readiness_and_record_order_are_independent_of_metric_order`

```
/home/payam/ocudu-prefix/tests/unittests/e2/e2sm_kpm_test.cpp:203: Failure
Value of: report_service.is_ind_msg_ready()
  Actual: false
Expected: true
Google Test trace:
/home/payam/ocudu-prefix/tests/unittests/e2/e2sm_kpm_test.cpp:199: unavailable_metric=no-value valid_metric_first=true
```

### `e2sm_kpm_drb_throughput_preserves_fractional_values`

The following block appears 4 times, identical each time:

```
/home/payam/ocudu-prefix/tests/unittests/e2/e2sm_kpm_meas_provider_metrics_test.cpp:576: Failure
Expected equality of these values:
  meas_records[0].real().value
    Which is: 0
  0.4F
    Which is: 0.40000001
```

### `e2sm_kpm_drb_latency_does_not_overflow_signed_integer`

The following block appears twice:

```
/home/payam/ocudu-prefix/tests/unittests/e2/e2sm_kpm_meas_provider_metrics_test.cpp:614: Failure
Expected equality of these values:
  meas_records[0].real().value
    Which is: -4.3000001907348633
  10.0
    Which is: 10
```

It is followed by two more occurrences with the same text except
`Which is: -4.3165574073791504`.

## Decision rules

- **#684 fix (f078ab75a5): CONFIRMED.**
  - Rule: `readiness_and_record_order_are_independent_of_metric_order` FAILS on
    BEFORE and every test in both binaries PASSES on AFTER.
  - Result: it failed on BEFORE, and all 21 tests passed on AFTER.
- **RLC precision fix (1a1d1feb9b): CONFIRMED.**
  - Rule: at least `e2sm_kpm_drb_latency_does_not_overflow_signed_integer` FAILS on
    BEFORE and PASSES on AFTER.
  - Result: it failed on BEFORE and passed on AFTER.

## Limitations

- **This is code-level verification, not an end-to-end lab run.** No gNB, UE, RIC
  or core was involved, and no KPM indication was observed on the wire or by an
  xApp. The original lab protocol (Runs 1 and 2 in `PREREGISTRATION.md`) could not be
  completed on the OCUDU build in this testbed [redacted: details withheld pending a
  separate report to the maintainers].
  That issue is unrelated to the code under test. This result says nothing about how the fixed
  code behaves in a running system beyond what the unit tests exercise.
- **The tests come from the MR itself,** written by the fix's author. They check
  the author's specified inputs and expected values. They are not an independent
  test design for issue #684.
- **The readiness test stops at the first failure.** It uses a fatal `ASSERT_TRUE`
  inside a loop over parameter combinations, so on BEFORE it aborted at the first
  failing combination (`unavailable_metric=no-value valid_metric_first=true`). The
  remaining combinations were not evaluated on BEFORE.
- **AFTER includes later, unrelated commits.** AFTER is HEAD `d0df5e24ff`, which is
  18 commits past `1a1d1feb9b`. The two test files and `lib/e2/e2sm/e2sm_kpm/`
  are unchanged between `1a1d1feb9b` and HEAD, but other parts of the tree differ.
- **BEFORE is a hybrid tree:** old `lib/` code plus the new test files. It compiled
  cleanly, but it is not a commit that exists upstream.
- **The MR number "!1521" is not confirmed from git.** No commit message references
  it. The two commits were identified by subject and file scope.
  *Added 2026-10-23:* GitLab MR !1521 carries the title of `f078ab75a5` ("e2,kpm:
  fix style 2 indication readiness") and closes issue #684, and the test
  `readiness_and_record_order_are_independent_of_metric_order` is present in the
  `release_26_10` tag (OCUDU 26.10).
- **The BEFORE and AFTER builds were configured separately.** Both use the same
  build type and `ENABLE_WERROR` setting, but BEFORE was freshly configured while
  AFTER reused the build dir from the earlier gNB build. Other cache options were
  left at their defaults and were not compared item by item.
