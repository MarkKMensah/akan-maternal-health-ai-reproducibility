# V3-M13 reverse-MT zero-shot screening results

## Decision

`SHORTLIST_READY_FOR_SEPARATELY_FROZEN_BLIND_AUDIT`

NLLB-3.3B (`B3`) ranks first and NLLB-1.3B (`B2`) ranks second. Both advance to a separately frozen, development-only blind audit against the current NLLB-600M sentence anchor (`B1`). MADLAD-400-3B (`B4`) is rejected. This is not authorization to change RunPod or the production application.

## Automatic development results

| Candidate | chrF++ | sacreBLEU | token F1 | protected recall | response repetition flags | generation seconds | peak GPU GiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1 NLLB-600M sentence anchor | 29.519 | 9.667 | 0.3600 | 0.4796 | 0 | 32.10 | 3.79 |
| B2 NLLB-1.3B sentence | 30.923 | 10.020 | 0.3695 | 0.4783 | 0 | 86.77 | 3.88 |
| B3 NLLB-3.3B sentence | 31.702 | 10.261 | 0.3747 | 0.5068 | 0 | 143.97 | 7.59 |
| B4 MADLAD-400-3B sentence | 20.205 | 3.525 | 0.2404 | 0.2846 | 61 | 500.75 | 9.52 |

All candidates produced non-empty development and response outputs. B1, B2, and B3 retained all question marks and had no response-level repetition detector positives.

## Paired 20,000-cluster bootstrap against B1

The resampling unit was the original content group, preserving dependence among related variants.

| Comparison | chrF++ difference (95% CI) | token-F1 difference (95% CI) | protected-recall difference (95% CI) |
|---|---:|---:|---:|
| B2 − B1 | +1.467 [0.876, 2.050] | +0.0098 [0.0019, 0.0175] | −0.0013 [−0.0350, 0.0329] |
| B3 − B1 | +2.092 [1.513, 2.663] | +0.0146 [0.0069, 0.0225] | +0.0274 [−0.0059, 0.0608] |
| B4 − B1 | −8.779 [−9.555, −7.976] | −0.1194 [−0.1309, −0.1080] | −0.1924 [−0.2378, −0.1477] |

The intervals support positive automatic chrF++ and token-F1 differences for B2 and B3. They do not establish a protected-concept improvement: both protected-recall intervals include zero. Human semantic-safety review is therefore mandatory before any deployment decision.

## Efficiency interpretation

- B3 gives the strongest automatic quality and protected-recall point estimates, but generation took about 4.5 times as long as B1 and used about twice the peak GPU memory.
- B2 gives a smaller but statistically supported quality improvement, took about 2.7 times as long as B1, and added only about 0.09 GiB peak GPU memory in this run.
- If blinded human performance is practically equivalent, B2 is the more deployment-efficient candidate. If B3 shows a meaningful and safety-preserving human advantage, its additional compute may be justified.

## Claim boundary

These findings are development-only automatic model screening. They are not clinical validation, end-to-end system evidence, population-level user evidence, or a reason to open the sealed test partition. The forward Akan-to-English RNMT stage remains frozen and unchanged.

