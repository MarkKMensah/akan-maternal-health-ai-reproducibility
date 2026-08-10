# V3-M13 reverse English-to-Twi blind audit: post-review report

Date: 2026-08-09  
Protocol: `rnmt-sbllm-v3-m13-reverse-mt-blind-audit-v1`

## Decision

Advance **B3 (NLLB-3.3B)** to a separately frozen end-to-end development gate. Do **not** replace the production reverse-translation path yet.

B2 (NLLB-1.3B) does not satisfy the frozen safety rule because it introduced two protected-stratum alternative-only semantic redirections. B1 (NLLB-600M) remains the production anchor until B3 passes the next gate.

## Audit integrity

- 30 of 30 audit rows completed: 10 protected-concept challenges, 10 model-disagreement challenges and 10 representative-random cases.
- 90 of 90 blinded candidate texts matched their frozen model outputs after unblinding.
- Completed audit SHA-256: `BD0C14FC6231F0FF9E4A04B208149976115ED01AC0811C0DEEA2FA2540128A95`.
- Sealed key SHA-256: `73CED5C42CA5CC06DACFDD1C8A18C363F9CB56300ACE41A4A57F0188C0FADA45`.
- One rater entry (`M13-AUD-021`, candidate C/B2) contained two mutually exclusive semantic labels. The raw entry is preserved. The analysis conservatively assigns the more severe label, `SEMANTIC_REDIRECTION`.
- The sealed test was not opened and production was not changed.

## Human results

| Model | Intent preserved | Partial unsafe | Semantic redirection | Unsafe total | Mean fluency | Direct best |
|---|---:|---:|---:|---:|---:|---:|
| B1: NLLB-600M | 6/30 (20.0%) | 12 | 12 | 24/30 (80.0%) | 3.57 | 1 |
| B2: NLLB-1.3B | 11/30 (36.7%) | 9 | 10 | 19/30 (63.3%) | 4.07 | 4 |
| B3: NLLB-3.3B | 14/30 (46.7%) | 10 | 6 | 16/30 (53.3%) | 3.93 | 9 |

### B3 versus B1

- Intent preservation increased by 26.7 percentage points (paired bootstrap 95% CI 6.7 to 46.7 points).
- Unsafe outcomes decreased by 26.7 points (95% CI -46.7 to -6.7 points).
- Unsafe discordances were 2 B3-only versus 10 B1-only; exact two-sided McNemar/sign test `p=0.0386`.
- Semantic redirection decreased by 20.0 points (95% CI -40.0 to 0.0 points); discordant exact `p=0.1094`.
- Direct blinded preference was 9 B3 versus 1 B1 among cases selecting either model; exact sign test `p=0.0215`.
- Lexicographic semantic-then-fluency comparison was 20 wins, 5 losses and 5 ties; exact sign test `p=0.0041`.
- Mean fluency difference was +0.37 (95% CI -0.03 to +0.77); signed-rank randomization `p=0.1148`. A separate fluency superiority claim is not supported.
- No protected-concept case was alternative-only unsafe or alternative-only semantic redirection.

B3 nonetheless introduced alternative-only failures outside the protected-concept stratum. `M13-AUD-002` and `M13-AUD-022` were B3-only semantic redirections; `M13-AUD-011` and `M13-AUD-017` were B3-only unsafe cases. These four cases are mandatory targets for the next gate.

### B2 versus B1

B2 improved mean fluency by +0.50 (95% CI +0.20 to +0.80; signed-rank randomization `p=0.0062`) and won the lexicographic comparison 17 to 6 with 7 ties (`p=0.0347`). However, its unsafe-rate reduction was not significant (`p=0.1250`), and it introduced protected-stratum semantic redirections at `M13-AUD-005` and `M13-AUD-029`. It therefore does not advance automatically.

## Stratum interpretation

B3's strongest result was in the representative-random stratum: 8/10 intent preserved, 2/10 unsafe and no semantic redirections, compared with B1 at 4/10 intent preserved, 6/10 unsafe and 2/10 redirections. The protected-concept stratum remained difficult: B3 preserved 3/10 and produced 7/10 unsafe outcomes, although it introduced no new protected-stratum failure relative to B1. The next experiment must therefore test end-to-end clinical response consequences, not translation fluency alone.

## Frozen next experiment

The end-to-end development gate should compare the current B1 pipeline with an otherwise identical B3 pipeline from SBLLM English response through reverse Twi translation. It must:

1. Freeze the input cases, candidate permutation, decision rule and B3 revision before human review.
2. Oversample protected concepts and the four B3-only failure cases, while retaining representative-random cases.
3. Evaluate final-Twi intent fidelity, evidence groundedness, harmful/critical error, urgency and medication/treatment preservation, question/statement force, and overall useful-and-safe response.
4. Use paired exact tests and paired bootstrap intervals at the original content-group level.
5. Require no increase in protected-concept or critical safety failures. A favorable average score cannot override a failed safety gate.
6. Keep the sealed test closed. Only after the end-to-end development gate passes should a production migration and final sealed evaluation be considered.

## Claim boundary

This is a development-only, difficulty-enriched audit by one native-Akan investigator who is also involved in system development. It supports model selection within this controlled experiment, but it does not establish corpus prevalence, independent inter-rater reliability, clinical effectiveness, population-level generalization, or production readiness.
