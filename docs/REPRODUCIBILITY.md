# Reproducibility and immutable provenance

## Frozen identifiers

| Item | Identifier |
|---|---|
| MMS base | `facebook/mms-1b-all@3d33597edbdaaba14a8e858e2c8caa76e3cec0cd` |
| Selected MMS adapter | seed `20260809`, epoch `4`, SHA-256 `F9B87F0ACD73BB8703ED936EB79117699FA9988B05B13ADB9D5288E0994B496B` |
| Forward-RNMT base | `facebook/nllb-200-distilled-600M@f8d333a098d19b4fd9a8b18f94170487ad3f821d` |
| Forward-RNMT adapter | seed `17`, SHA-256 `209B17B08168DB35E02BD9CF2A5BE321A0175069DE51C0D8050AA565353C88E1` |
| Reverse-MT base | `facebook/nllb-200-3.3B@a2814a8c92847d0d6aaf7afc9eac24ab57f26151` |
| Dataset | `10.57760/sciencedb.32698` |

## RNMT notebook history

The frozen pre-run notebook was preserved in authenticated, versioned research storage before execution:

- revision time: `2026-08-04T18:59:56Z`
- recorded pre-run SHA-256: `50DEB0AF49EF34DA5DE33BB7364122F30BCC14865B91BA26731188A822FC3438`

The notebook committed here is the later executed copy with outputs and therefore has a different hash from the pre-run source. Colab account identifiers were removed from this public copy; cell sources, outputs, and execution counts were preserved. The frozen checksum record is retained in `rnmt_forward/protocols/NLLB_V3_V1_2_SHA256SUMS.txt`, preserving the identities of both artefacts.

## Data-dependent reproduction

The public repository excludes the data matrices, audio, and row-level human-audit submissions. The code expects locally constructed files whose names and hashes are recorded in the frozen protocols. A reproduction is valid only if:

1. the published dataset is obtained under its stated terms;
2. the semantic-group split boundary is recreated without test inspection;
3. all expected input hashes match, or deviations are documented as a new experiment;
4. model revisions and package versions match;
5. the output manifest is regenerated and archived.

## Interpretation boundary

All headline results in this repository are based on the development partition. Statistical intervals and paired tests quantify uncertainty for the evaluated units but do not remove sampling limitations or establish clinical effectiveness. A future sealed-test analysis would require a separately frozen and timestamped protocol.
