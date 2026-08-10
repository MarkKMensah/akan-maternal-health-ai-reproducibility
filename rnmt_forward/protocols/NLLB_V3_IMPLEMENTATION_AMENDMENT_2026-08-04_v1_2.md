# NLLB V3 Implementation Amendment — 2026-08-04

## Status and scope

This record documents two narrowly scoped software-interface corrections made after the frozen NLLB V3 development notebook completed preflight and baseline inference but stopped at the start of the first LoRA seed. Both failures occurred before any optimizer step. No development outcome, model-ranking result, sealed-test result, or downstream SBLLM result was available when either correction was made.

The frozen scientific protocol remains unchanged. The correction does not alter the dataset, train/development split, model revision, tokenizer revision, LoRA rank, LoRA alpha, LoRA dropout, target modules, optimizer, learning rate, epoch count, random seeds, sampling policy, decoding configuration, metrics, bootstrap procedure, promotion gates, or test-sealing rules.

## Preserved failed run

- Run ID: `20260804T182400Z_nllb_v3_lora_dev_v1`
- Drive path: `/content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_2026-08-04/runs/20260804T182400Z_nllb_v3_lora_dev_v1`
- Original notebook SHA-256: `185854AF813D03AF8E41D86E88D24CBE8FE9563B4EBE13AC593AFD79391DFA2D`
- Failure point: first LoRA seed (`17`), immediately before optimization.
- Exception: `ValueError: You cannot specify both decoder_input_ids and decoder_inputs_embeds at the same time`
- State: preserved as an incomplete diagnostic run; no adapter is eligible for promotion or deployment.

## Reproduction and diagnosis

The actual first batch produced by the trainer data loader was inspected without modifying the data or opening the sealed test partition. It contained:

- keys: `attention_mask`, `input_ids`, `labels`
- `input_ids`: shape `(16, 57)`
- `attention_mask`: shape `(16, 57)`
- `labels`: shape `(16, 43)`
- absent: `decoder_input_ids`
- absent: `decoder_inputs_embeds`

The original code constructed `DataCollatorForSeq2Seq` with the PEFT wrapper as its `model`. In this installed interface combination, the wrapper did not expose the base sequence-to-sequence model's `prepare_decoder_input_ids_from_labels` method to the collator. Consequently, the collator did not construct `decoder_input_ids`. Because label smoothing was enabled, the trainer handled labels externally before the forward pass. The resulting decoder-input path was incompatible with the PEFT/M2M100 forward interface and training stopped before the first parameter update.

## v1.1 minimal correction

The collator now receives the underlying frozen base sequence-to-sequence model:

```python
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=base_model,
)
```

No package was upgraded and no experimental hyperparameter was changed.

## Added pre-optimizer safeguard

Before `trainer.train()` the corrected notebook now:

1. takes one batch from the actual trainer data loader;
2. requires `decoder_input_ids` to be present;
3. requires `decoder_inputs_embeds` to be absent;
4. performs one no-gradient forward pass;
5. requires all returned logits to be finite; and
6. resets the frozen random seed before training, preventing the smoke test from changing the prescribed stochastic training sequence.

This safeguard is an implementation-validity check, not a model-selection intervention.

## Preserved v1.1 safeguard run

- Run ID: `20260804T184853Z_nllb_v3_lora_dev_v1`
- Drive path: `/content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_2026-08-04/runs/20260804T184853Z_nllb_v3_lora_dev_v1`
- v1.1 notebook SHA-256: `0CCE34067EDB08E32D0C511779DE68A1B73943D1888CB8BC801D860D8E225808`
- Failure point: the new pre-optimizer smoke test for seed `17`.
- Assertion: `assert "decoder_input_ids" in smoke_batch, sorted(smoke_batch.keys())`
- Observed batch keys: `['attention_mask', 'input_ids', 'labels']`
- State: preserved as an incomplete diagnostic run; no optimizer step, adapter promotion, sealed-test access, downstream evaluation, or deployment occurred.

The v1.1 safeguard disproved the provisional assumption that passing the bare base model to `DataCollatorForSeq2Seq` would be sufficient. In Transformers `4.57.1`, the collator constructs decoder inputs only when its model exposes `prepare_decoder_input_ids_from_labels`. The pinned NLLB checkpoint resolves to the M2M100 conditional-generation implementation, which instead performs its label shift through the model-family `shift_tokens_right` routine and does not expose that collator hook. The failed assertion therefore represents a successful validity safeguard, not an experimental outcome.

## v1.2 minimal correction

The v1.2 notebook keeps the stock `DataCollatorForSeq2Seq` for padding but adds a small callable collator that explicitly constructs `decoder_input_ids` with the pinned Transformers M2M100 `shift_tokens_right` routine:

```python
batch["decoder_input_ids"] = shift_tokens_right(
    batch["labels"],
    pad_token_id=pad_token_id,
    decoder_start_token_id=decoder_start_token_id,
)
```

The callable stores only the two integer token IDs rather than a model object, so it is safe for the frozen multi-worker data-loader configuration. The v1.1 smoke test is retained unchanged. No package, dataset, model/tokenizer revision, split, hyperparameter, sampling rule, decoding setting, metric, bootstrap rule, gate, or test-sealing rule was changed.

## Versioned artifacts

- Pristine v1 notebook: `03_Notebooks/nllb_v3_lora_train_dev_colab_2026-08-04.ipynb`
- Corrected v1.1 notebook: `03_Notebooks/nllb_v3_lora_train_dev_colab_2026-08-04_v1_1.ipynb`
- Corrected v1.1 SHA-256: `0CCE34067EDB08E32D0C511779DE68A1B73943D1888CB8BC801D860D8E225808`
- Corrected v1.2 notebook: `03_Notebooks/nllb_v3_lora_train_dev_colab_2026-08-04_v1_2.ipynb`
- Corrected v1.2 SHA-256: `50DEB0AF49EF34DA5DE33BB7364122F30BCC14865B91BA26731188A822FC3438`
- The pristine local upload-bundle copy is also retained.

The v1.2 notebook must start a new timestamped run directory. It must not resume or overwrite either failed run.

## Research-integrity boundary

- The sealed test partition remains unopened.
- No OpenAI/SBLLM call was made by this run.
- No training update completed in the failed run.
- No adapter or result from the failed run was promoted, integrated into RunPod, or deployed.
- Any future promotion decision remains governed by the previously frozen development gates and blinded safety review.

## Interface references

- Hugging Face Transformers, `DataCollatorForSeq2Seq`: <https://huggingface.co/docs/transformers/main_classes/data_collator#transformers.DataCollatorForSeq2Seq>
- Hugging Face Transformers v4.57.1, `DataCollatorForSeq2Seq` source: <https://raw.githubusercontent.com/huggingface/transformers/v4.57.1/src/transformers/data/data_collator.py>
- Hugging Face Transformers, M2M100 model documentation: <https://huggingface.co/docs/transformers/model_doc/m2m_100>
- Hugging Face Transformers v4.57.1, M2M100 model source: <https://raw.githubusercontent.com/huggingface/transformers/v4.57.1/src/transformers/models/m2m_100/modeling_m2m_100.py>
- Hugging Face PEFT v0.17.1 source, sequence-to-sequence wrapper: <https://raw.githubusercontent.com/huggingface/peft/v0.17.1/src/peft/peft_model.py>

## Interpretation

These are pre-outcome implementation amendments. They repair data-collation compatibility while preserving the registered scientific comparison. Both must be disclosed with the experiment materials, but neither constitutes post-hoc tuning because no adaptation result existed when either correction was specified.

