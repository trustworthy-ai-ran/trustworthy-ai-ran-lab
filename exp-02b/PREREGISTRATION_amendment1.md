
## Amendment 1 — before any data collection

Added Run P (positive control, `DRB.UEThpDl` alone) and Run C
(`DRB.UEThpDl,DRB.FakeMetric123`). Reason: shell history shows the
FakeMetric configuration was tried in the original session but the log
was lost. A non-existent metric cannot produce a value and therefore
cannot break the ASN.1 encoder, making Run C a sharper discriminator
between the readiness-check and encoding hypotheses than Run B.
Confirmation rule unchanged: H1 confirmed iff P>0, A1=0, B>0, A2=0.
