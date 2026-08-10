# V3-M9 positive development result record

Date: 2026-08-07  
Protocol: `nllb-v3-m9-adapted-asr-causal-propagation-dev-v1`  
Decision: `PASS_TO_SEPARATELY_FROZEN_72_CASE_BLINDED_DEVELOPMENT_AUDIT`

## Research question

Does replacing the public-MMS transcript with the representative adapted-MMS
transcript improve downstream Akan/Twi-to-English RNMT output when the RNMT
model, generation settings, safety-selection rules, development partition and
analysis are held fixed?

The representative ASR checkpoint was seed `20260809`, epoch 4, selected before
this experiment because its development WER was closest to the three-seed mean,
not because it was the best seed. Its adapter SHA-256 was
`F9B87F0ACD73BB8703ED936EB79117699FA9988B05B13ADB9D5288E0994B496B`.

## Frozen conditions

- `G`: gold Akan/Twi input through the unchanged RNMT path; diagnostic ceiling,
  not a deployable condition.
- `D0`: original public-MMS transcript through the unchanged RNMT path.
- `D1`: adapted-MMS transcript through the same unchanged RNMT path.
- Development corpus: 1,558 rows, 458 semantic groups, BT/HA/IM/PT.
- Primary paired unit: semantic group.
- Bootstrap: 20,000 semantic-group-clustered replicates, seed `20260807`.
- Sealed test, prior human outcomes, SBLLM and production were inaccessible to
  the experiment.

## Automatic result

All 12 precommitted automatic gates passed.

| Metric | G | D0 public MMS | D1 adapted MMS | D1 - D0 |
|---|---:|---:|---:|---:|
| chrF++ | 39.7483 | 25.4841 | 30.8636 | +5.3795 |
| SacreBLEU | 20.1753 | 7.2029 | 10.9806 | +3.7777 |
| Macro token F1 | 0.4469 | 0.2677 | 0.3359 | +0.0682 |
| Protected-concept recall | 0.5712 | 0.3799 | 0.4575 | +0.0776 |
| Number agreement | 0.9519 | 0.9358 | 0.9377 | +0.0019 |
| Negation agreement | 0.9012 | 0.8402 | 0.8633 | +0.0231 |
| Empty outputs | 0 | 0 | 0 | 0 |

The paired mean sentence-level chrF++ gain was `+6.1250`; its
semantic-group-clustered 95% interval was `[+5.1963, +6.7625]`. D1 beat D0 on
1,054 rows, lost on 487 and tied on 17. The exact two-sided sign-test p-value
was `3.3463e-48`. These results establish a strong development-set causal
propagation signal under the frozen pipeline; they do not replace the planned
human assessment of meaning and safety.

D1 recovered `37.71%` of the positive D0-to-G chrF++ gap. This is useful but
also shows that substantial downstream translation error remains.

## Speaker-code stratification

| Speaker code | Rows | Groups | D0 chrF++ | D1 chrF++ | Delta |
|---|---:|---:|---:|---:|---:|
| BT | 377 | 115 | 26.2686 | 31.7366 | +5.4680 |
| HA | 429 | 143 | 23.1963 | 26.8860 | +3.6897 |
| IM | 372 | 94 | 31.1237 | 38.2765 | +7.1529 |
| PT | 380 | 107 | 21.7018 | 27.0464 | +5.3446 |

Every speaker-code stratum improved, but BT, HA, IM and PT occur in both train
and development. These are speaker-code-stratified results, not evidence of
unseen-speaker generalisation.

## Integrity and stop boundaries

- Development-source SHA-256:
  `CB202D42D8A0D079F68515A4EFFD536BE2EE91CEA5E4689E2F55251A5C67626A`
- Adapted-ASR predictions SHA-256:
  `0D0120327BB58CE505C81C0F4563D929A8204E717E89C16F67AA4D61A0A71BD2`
- Frozen RNMT adapter SHA-256:
  `209B17B08168DB35E02BD9CF2A5BE321A0175069DE51C0D8050AA565353C88E1`
- Paired G/D0/D1 predictions SHA-256:
  `4ED5189C8DA8B5F6A1904363CB486ABDC51C722618F8E8B63D8640A23DFB1C86`
- Complete ZIP archive SHA-256:
  `10D4970803BBEA5909A7E2778FE90CC12E68281C2EF1E30BC12490473FF89176`
- Sealed test opened: no; rows read: 0.
- Prior human outcomes read: no.
- SBLLM run: no.
- Production changed: no.

The Drive evidence folder is:
https://drive.google.com/drive/folders/1TbDtnMhsTZU_CiEfSKt_y2JlfL0Uvx0x

## Claim boundary

The defensible claim at this stage is:

> On the fixed, semantic-group-disjoint development partition of controlled
> scripted maternal-health Twi from four speaker codes, replacing public-MMS
> transcripts with the preselected adapted-MMS transcripts materially improved
> outputs from the otherwise unchanged RNMT path across automatic translation
> and protected-concept screening measures.

This is not clinical validation, patient testing, spontaneous-speech evidence,
unseen-speaker evidence, population-level Akan generalisation, SBLLM evidence,
or permission to deploy. Lexicon, number and negation checks are automatic
screening proxies rather than clinical-safety judgments.

## Authorized next step

Freeze and conduct a 72-case blinded development audit, with 18 previously
unreviewed semantic groups per speaker code. The audit must blind D0/D1 identity,
keep the reveal key separate, and assess intent preservation, critical-concept
errors, safety/usefulness and preference. Only that audit may decide whether D1
is ready to become the ASR condition in the final end-to-end freeze. The sealed
test remains closed until ASR, RNMT, SBLLM, reverse translation, normalization,
metrics and audit rules are all signed.
