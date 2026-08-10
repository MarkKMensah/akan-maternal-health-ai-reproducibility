# MMS maternal adapter screen — execution amendment 01

Date: 2026-08-07  
Protocol: `mms-maternal-adapter-screen-dev-v1`  
Run: `20260806_mms_maternal_adapter_screen_seed20260806`

## Trigger

The first clean execution completed the immutable train/development audio
verification and wrote the train-only processor, but failed before model
initialization and before epoch 1.  With `transformers==4.46.3`, combining
`low_cpu_mem_usage=True`, `ignore_mismatched_sizes=True`, and the resized
train-only CTC vocabulary left parameters on the meta device.  The subsequent
`model.to(cuda)` raised:

`NotImplementedError: Cannot copy out of meta tensor; no data!`

GPU memory remained at 0 GB.  No epoch, checkpoint, development prediction,
bootstrap result, test read, SBLLM run, or production change occurred.

## Amendment

Change only the model-loading implementation from
`low_cpu_mem_usage=True` to `low_cpu_mem_usage=False`.  This materializes the
same frozen base revision on CPU before moving it to the A100 and avoids the
meta-device defect.  The 83.5 GB host-RAM runtime is sufficient for this
loader path.

No data, split, seed, vocabulary, batch size, gradient accumulation, learning
rate, warm-up, epoch count, optimizer, checkpoint-selection rule, bootstrap,
speaker regression threshold, or advancement gate is changed.

The completed verified 16 kHz local cache is reused by the unchanged cache
validation/skip path.  The amended script hash and this amendment hash are
recorded in the updated precommit before rerunning.

## Boundary status at amendment

- sealed test opened: no
- test rows read: 0
- RNMT human outcomes read: no
- SBLLM run: no
- production changed: no
- training epochs completed: 0
