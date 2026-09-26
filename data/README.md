# Data Directory

This directory is for storing datasets used in your ML research experiments.

## Organization Guidelines

Organize datasets in subdirectories by:

- **Dataset source**: `data/huggingface/`, `data/kaggle/`, `data/custom/`
- **Dataset name**: `data/glue/`, `data/squad/`, `data/imagenet/`
- **Experiment**: `data/<experiment-id>/` for experiment-specific preprocessed data

Choose the structure that best fits your workflow.

## Git Exclusion

**By default, the `data/` directory is excluded from Git** (except for this README and `.gitkeep` files). This prevents accidentally committing large datasets to version control.

Only commit:
- Dataset documentation and descriptions
- Preprocessing scripts
- Small sample datasets for testing (<10 MB)

## Large Dataset Management

For large datasets, consider these alternatives to storing in this directory:

### 1. Symlinks

Create symlinks to datasets stored elsewhere on your filesystem:

```bash
ln -s /mnt/datasets/imagenet data/imagenet
```

This keeps your workspace clean while providing local access.

### 2. Data Registries

Use data versioning tools:

- **DVC** (Data Version Control): Track datasets with Git-like commands
- **Hugging Face Datasets**: Load datasets directly from the Hub in your code
- **AWS S3 / GCS**: Store datasets in cloud buckets with URI references
- **Weights & Biases Artifacts**: Track datasets alongside experiments

### 3. Download Scripts

Write scripts that download datasets on-demand:

```python
# data/download_squad.py
from datasets import load_dataset

dataset = load_dataset("squad")
dataset.save_to_disk("data/squad")
```

Include download instructions in your experiment documentation.

## Best Practices

1. **Document dataset versions**: Record exact dataset versions, splits, and preprocessing steps
2. **Use caching**: Configure libraries like `datasets` to cache in `data/`
3. **Check licenses**: Ensure dataset licenses permit your intended use
4. **Keep raw data separate**: Store raw and preprocessed data in separate directories
5. **Add dataset READMEs**: Create `data/<dataset-name>/README.md` for dataset-specific notes

## Example Structure

```
data/
├── README.md                   # This file
├── .gitkeep                    # Preserves directory in Git
├── huggingface_cache/          # HF datasets cache (gitignored)
├── glue/                       # GLUE benchmark tasks
│   ├── README.md              # Dataset documentation
│   └── raw/                   # Raw downloaded data
├── custom_dataset/             # Your custom dataset
│   ├── README.md              # Data description and collection notes
│   ├── train.jsonl
│   ├── val.jsonl
│   └── test.jsonl
└── preprocessed/               # Experiment-specific preprocessed data
    └── exp-001/
        ├── train_tokenized.pt
        └── val_tokenized.pt
```

## Configuration

Set dataset paths in your experiment job configurations:

```yaml
# experiments/my-experiment/jobs/train.yaml
parameters:
  dataset_path: data/glue/mnli
  cache_dir: data/huggingface_cache
```

Or configure dataset locations in `project-plan.md` for project-wide defaults.
