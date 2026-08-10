# MMS adapter three-seed confirmation — execution amendment 01

Date: 2026-08-07  
Protocol: `mms-maternal-adapter-confirm-dev-v1`

## Trigger

The first launch of confirmation seed `20260807` exited before model loading or training. Local syntax validation identified that three shell-status lines (`Exit code`, `Wall time`, and `Output`) had been accidentally prepended to the frozen per-seed Python file when it was copied from prior terminal output.

## Permitted correction

Only those three non-Python lines were removed. No dataset, partition, seed, model, hyperparameter, epoch count, selection rule, metric, confidence-interval method, gate, or stop boundary changed.

- Original invalid per-seed script SHA-256: `8B68FCF053191CFEFDC85EE8C41B59A62E4E47D839AE256F4BFDDCD79C183E8B`
- Corrected syntax-valid per-seed script SHA-256: `8FFC5C440BCE1F274BD3DC57AECC96C454DE43B3B35ACEDEE6E2D16F73A55639`
- Joint-analysis script unchanged: `26AC627940D19C76EB9964458F2A6D400418FEE8917EDAB67D8ABBAE6A7FED0A`

The precommit artifact was advanced from `v1` to `v1.1` solely to record this execution correction.

## Boundary audit

- Seed training completed before failure: **no**
- Development prediction produced: **no**
- Sealed test opened or read: **no; 0 rows**
- RNMT human outcomes read: **no**
- SBLLM run: **no**
- Production changed: **no**

The amended launch must re-check the updated hashes before executing any confirmation seed.
