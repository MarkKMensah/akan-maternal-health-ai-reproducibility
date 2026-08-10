# V3-M14 final results: causal reverse-MT gate

**Protocol:** `rnmt-sbllm-v3-m14-end-to-end-reverse-mt-gate-v1`  
**Analysis date:** 2026-08-09  
**Decision:** **All eight frozen gates passed — advance B3 to a separate technical deployment-acceptance stage.**  
**Production status:** unchanged; B1 remains deployed until technical acceptance and rollback validation succeed.  
**Sealed test:** unopened.

## 1. Scientific question

V3-M14 asked whether changing only the final English→Twi translator from the current sentence-segmented NLLB-600M anchor (B1) to the sentence-segmented NLLB-3.3B candidate (B3) causally improves the safety and semantic fidelity of final Twi responses. The adapted-MMS transcript, forward RNMT result, retrieval context, SBLLM English response and SBLLM disposition were fixed for every paired case.

The experiment used the same 72 challenge-enriched V3-M10 content groups: 18 each from BT, HA, IM and PT, and 24 each from `REGRESSION_RISK`, `STRONG_GAIN` and `SYSTEM_DISAGREEMENT`.

## 2. Integrity and blinding

The reviewer completed all 72 paired cases. All labels were valid and there were zero `UNCERTAIN` judgments. Before opening the reveal mapping, the completed audit was copied to a separate locked Drive folder and serialised to a canonical snapshot with SHA-256:

`89F5C0CE84E33E992CCDD7FA8AAEF05CE6617CE385573B33BE1B747F81D07AD9`

The reveal-key SHA-256 was:

`D5A4E9BC60E6F32764302744B97352DA8D21741024745F2AB3BA5355E381E1A6`

No model was trained or adapted, the sealed test was not opened, and production was not changed.

## 3. Precommitted analysis

- Analysis unit: content group.
- Primary binary comparison: two-sided exact McNemar/binomial test on discordant pairs.
- Direct preference: two-sided exact sign test excluding `TIE` and `NEITHER`.
- Paired rates and mean fluency: 20,000 content-group bootstrap resamples, seed `20260814`.
- Fluency location: exact paired signed-rank randomisation test.
- Alpha: 0.05.
- All eight advancement gates were conjunctive; a favorable average could not override a failed safety gate.

## 4. Primary outcome

Safe final-Twi fidelity increased from **40/72 (55.6%) with B1** to **54/72 (75.0%) with B3**, an absolute paired improvement of **19.4 percentage points** (bootstrap 95% CI **6.9 to 31.9 points**).

There were **19 B3-only successes** and **5 B1-only successes** among 24 discordant pairs. The exact paired p-value was **0.00661**, and the matched discordant-pair odds ratio was **3.80** (Haldane-corrected 3.55).

This passes the primary frozen gate and supports a causal B3-over-B1 improvement on this fixed development cohort.

## 5. End-to-end useful-and-safe outcome

Thirty-four cases had a frozen English pipeline that was already useful and safe before reverse translation. Within this prespecified subset, the final useful-and-safe rate increased from **17/34 (50.0%) with B1** to **28/34 (82.4%) with B3**, an absolute improvement of **32.4 percentage points** (bootstrap 95% CI **17.6 to 47.1 points**).

There were **11 B3-only successes and zero B1-only successes**. The exact paired p-value was **0.000977**.

This is the most direct evidence that the reverse-translation replacement repairs a real downstream bottleneck rather than merely producing more fluent Twi.

## 6. Preference and fluency

Among 57 arm-decided comparisons, B3 was preferred in **46 (80.7%)** and B1 in **11 (19.3%)**; there were 2 ties and 13 cases where neither candidate was acceptable. The exact sign-test p-value was **3.31×10⁻⁶**.

Mean fluency increased from **3.42** with B1 to **4.11** with B3, a paired mean increase of **0.69 points** (bootstrap 95% CI **0.51 to 0.88**). Median fluency increased from 3 to 4. The exact signed-rank randomisation p-value was **6.19×10⁻¹⁰**.

## 7. Safety outcomes

Potentially harmful or critical final-Twi responses decreased from **32/72 (44.4%) with B1** to **18/72 (25.0%) with B3**. There were 19 B1-only harmful/critical cases and 5 B3-only cases; exact paired p = **0.00661**.

Unsafe semantic redirections showed the same reduction: **32/72 (44.4%)** with B1 versus **18/72 (25.0%)** with B3, with 19 B1-only and 5 B3-only discordances; exact paired p = **0.00661**.

Each system had one `CRITICAL` case, and it was the same paired case; therefore there were **zero B3-only critical cases**.

The presence of any coded critical-error category decreased from **64/72 (88.9%)** with B1 to **40/72 (55.6%)** with B3, with 26 B1-only and 2 B3-only discordances; exact paired p = **3.03×10⁻⁶**. This is a secondary, non-multiplicity-adjusted result.

## 8. Prespecified high-risk categories

All eight high-risk category gates passed: body site, contraception, infectious disease, negation/polarity, number/timing, symptom/condition, treatment and urgency/referral. Every category had zero B3-only critical cases, and no category had more B3-only than B1-only unsafe redirections.

Across the union of 68 high-risk cases, unsafe redirection fell from 31 with B1 to 17 with B3. The discordances were 19 B1-only versus 5 B3-only, with zero B3-only critical cases.

## 9. Frozen gate decision

| Gate | Outcome |
|---|---|
| 1. Complete, valid, no uncertain labels | PASS |
| 2. Primary safe-fidelity superiority | PASS |
| 3. ≥60% B3 preference plus significant sign test | PASS |
| 4. No excess B3-only harmful/critical cases | PASS |
| 5. Zero B3-only critical cases | PASS |
| 6. No excess B3 unsafe redirection | PASS |
| 7. End-to-end useful-and-safe superiority | PASS |
| 8. Prespecified high-risk safety | PASS |

**Conjunctive decision: PASS.** B3 advances to technical deployment acceptance.

## 10. Defensible claim

The defensible claim is:

> In a precommitted, blinded, paired 72-case challenge-enriched development experiment that held the adapted-MMS ASR, forward RNMT, retrieval and SBLLM English response constant, replacing the sentence-segmented NLLB-600M reverse translator with the immutable NLLB-3.3B revision caused a statistically significant improvement in safe final-Twi fidelity and end-to-end useful-and-safe responses, while reducing unsafe semantic redirection and without introducing excess critical or prespecified high-risk failures.

The result does **not** establish clinical effectiveness, autonomous decision support, population prevalence, independent inter-rater reliability, unseen-speaker or spontaneous-patient generalisation, sealed-test performance, or production readiness.

## 11. Deployment consequence

B3 should replace B1 only after a separate technical acceptance stage confirms:

1. the immutable B3 model revision and decoding settings are reproduced in the RunPod image;
2. the 72 fixed English responses reproduce the archived B3 outputs or their approved hashes;
3. cold start, GPU memory, latency, concurrency, restart and persistent-cache behavior are acceptable on the RTX 4000 Ada pod;
4. `/docs`, WebSocket and frontend transparency fields remain correct;
5. a canary smoke suite covers successful answers, abstentions, high-risk cases and error handling; and
6. a tested rollback path restores the current B1 image/configuration.

No sealed test should be opened merely to support deployment. Production migration must be versioned and reversible.

## 12. Dissertation contribution

V3-M14 strengthens the dissertation in three ways:

- **Causal isolation:** it identifies reverse translation as an independently remediable bottleneck because every upstream component was held fixed.
- **Safety-aware evaluation:** it demonstrates that WER/CER or fluency alone are insufficient and uses clinically meaningful semantic-redirection, harmfulness, critical-error and protected-concept gates.
- **Reproducible engineering evidence:** the systems, revisions, decoding parameters, sample, audit instrument, randomisation rule, hashes, tests, seeds and advancement thresholds were frozen before outcome inspection.

The experiment should be reported as a development-stage causal component-selection study inside the broader adapted-MMS → RNMT → grounded SBLLM → reverse-MT → TTS architecture, not as a standalone clinical trial.
