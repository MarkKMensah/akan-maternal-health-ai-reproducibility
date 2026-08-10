# NLLB v3 Colab upload bundle

This bundle contains only the frozen development experiment notebook,
protocol, train data, development data, data manifest, and safety-trigger
lexicon. It contains no sealed-test rows or predictions.

## Google Drive destination

Upload the bundle contents beneath:

`My Drive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_2026-08-04/`

The four files currently inside `inputs/` must remain together at:

`My Drive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_2026-08-04/inputs/`

Open `nllb_v3_lora_train_dev_colab_2026-08-04.ipynb` in Google Colab,
select an A100 (or H100) runtime, and run cells in order. The notebook will
abort before training if any uploaded input hash differs from the frozen
manifest.

Do not add a test file to this folder. Do not open the generated reveal key
until the blinded semantic-safety review has been completed.


