# Git Safety Reference

## Purpose

This document defines commit safety rules for AI/ML research experiments. It specifies which files must never be committed to version control, detection patterns for sensitive data, and size limits for repository health. These rules protect against accidental exposure of credentials, prevent repository bloat from model checkpoints, and maintain a clean research history.

## Files That Must Never Be Committed

### Model Checkpoints and Weights

Model checkpoints are large binary files that should be distributed through specialized platforms (HuggingFace Hub, model registries) rather than Git repositories.

**File Extensions to Block**:
- `*.pt` - PyTorch model files
- `*.pth` - PyTorch checkpoint files
- `*.ckpt` - Generic checkpoint files (PyTorch Lightning, TensorFlow)
- `*.bin` - Binary model weights (older Transformers format)
- `*.safetensors` - SafeTensors format (efficient and safe, but still large)
- `*.h5` - Keras/TensorFlow HDF5 models
- `*.hdf5` - HDF5 data/model files
- `*.pb` - TensorFlow protobuf models
- `*.onnx` - ONNX model files
- `*.tflite` - TensorFlow Lite models

**Directory Patterns to Block**:
- `experiments/*/runs/*/checkpoints/`
- `experiments/*/runs/*/models/`
- `outputs/*/checkpoints/`
- `outputs/*/models/`

**Rationale**: A single model checkpoint for a 7B parameter model can be 13+ GB. Committing these to Git makes the repository unusable and wastes storage.

### Secrets and Credentials

Credentials must never be committed to version control. Even in private repositories, this creates security risks and makes credential rotation difficult.

**File Extensions to Block**:
- `*.env` - Environment files (often contain API keys)
- `*.key` - Private key files
- `*.pem` - PEM-encoded certificates/keys
- `*.token` - Token files

**Specific Filenames to Block**:
- `.env`
- `.env.local`
- `.env.*.local`
- `credentials.json`
- `secrets.yaml`
- `secrets.yml`
- `id_rsa`
- `id_ed25519`
- `*.secret`

**Rationale**: Exposed credentials can lead to unauthorized access, data breaches, and service abuse. Credentials should be managed through secure environment variables, secret managers, or configuration systems.

### Cache Directories and Temporary Files

Cache directories contain temporary data that is either regenerated automatically or unnecessary for reproduction.

**Directories to Block**:
- `wandb/` - Weights & Biases cache (anywhere in repo)
- `experiments/*/wandb/` - Experiment-level W&B cache
- `.cache/` - General cache directory
- `__pycache__/` - Python bytecode cache
- `.ipynb_checkpoints/` - Jupyter notebook checkpoints
- `.pytest_cache/` - Pytest cache
- `.mypy_cache/` - Mypy type checking cache

**Rationale**: Cache directories are large, frequently changing, and automatically regenerated. Committing them creates merge conflicts and wastes storage.

### Raw Slurm Logs

Raw Slurm output files are typically large and contain redundant information already captured in processed logs.

**File Patterns to Block**:
- `*.out` - Slurm stdout files (in run logs directories)
- `*.err` - Slurm stderr files (in run logs directories)
- `slurm-*.out` - Slurm job output files

**Specific Paths to Block**:
- `experiments/*/runs/*/logs/*.out`
- `experiments/*/runs/*/logs/*.err`

**Exception - Processed Logs to Commit**:
- `experiments/*/runs/*/logs/stdout.log` - Processed/structured stdout
- `experiments/*/runs/*/logs/stderr.log` - Processed/structured stderr
- `experiments/*/runs/*/logs/execution.log` - Agent execution notes

**Rationale**: Raw Slurm logs can be multiple MB per job. We preserve the information by extracting relevant content into structured log files during run tracking.

### Operating System Files

OS-specific files provide no value in version control and create noise.

**Files to Block**:
- `.DS_Store` - macOS Finder metadata
- `.AppleDouble` - macOS resource forks
- `.LSOverride` - macOS launch services
- `Thumbs.db` - Windows thumbnail cache
- `Desktop.ini` - Windows folder config
- `*~` - Unix backup files
- `.directory` - KDE directory metadata

**Rationale**: These files are OS-specific, automatically generated, and irrelevant to research reproduction.

### IDE and Editor Files

IDE configuration files often contain user-specific paths, preferences, and machine-specific settings.

**Directories to Block**:
- `.vscode/` - VSCode settings (unless explicitly shared)
- `.idea/` - PyCharm/IntelliJ settings
- `*.sublime-project` - Sublime Text project files
- `*.sublime-workspace` - Sublime Text workspace

**Files to Block**:
- `*.swp`, `*.swo` - Vim swap files
- `*~` - Emacs backup files
- `\#*\#`, `.\#*` - Emacs auto-save files

**Exception - Shared IDE Settings**:
- If the team explicitly decides to commit `.vscode/settings.json` or similar for shared linting/formatting configuration, this should be documented in the repository README.

**Rationale**: Personal IDE settings vary between developers and machines. They create merge conflicts without adding value to research.

## Secret Detection Patterns

Before committing any file, scan for patterns that indicate the presence of secrets, API keys, or credentials.

### API Keys and Tokens

**Regex Patterns**:

```regex
# Generic API keys (20+ alphanumeric characters)
[aA][pP][iI][-_]?[kK][eE][yY][-_:=\s]['\"]?[a-zA-Z0-9]{20,}

# Generic tokens
[tT][oO][kK][eE][nN][-_:=\s]['\"]?[a-zA-Z0-9]{20,}

# Bearer tokens
[bB][eE][aA][rR][eE][rR]\s+[a-zA-Z0-9\-_\.=]{20,}

# AWS Access Key ID (starts with AKIA)
AKIA[0-9A-Z]{16}

# AWS Secret Access Key (40 alphanumeric characters)
[aA][wW][sS][-_]?[sS][eE][cC][rR][eE][tT][-_]?[aA][cC][cC][eE][sS][sS][-_]?[kK][eE][yY][-_:=\s]['\"]?[a-zA-Z0-9/+=]{40}

# HuggingFace User Access Token (starts with hf_)
hf_[a-zA-Z0-9]{32,}

# OpenAI API Key
sk-[a-zA-Z0-9]{48}

# Anthropic API Key
sk-ant-[a-zA-Z0-9\-_]{95,}

# Google API Key
AIza[0-9A-Za-z\-_]{35}

# GitHub Personal Access Token (classic)
ghp_[a-zA-Z0-9]{36}

# GitHub Fine-grained Personal Access Token
github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}

# Weights & Biases API Key (40 hex characters)
[0-9a-f]{40}

# Private SSH Key (detect BEGIN markers)
-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----

# Generic password assignments
[pP][aA][sS][sS][wW][oO][rR][dD][-_:=\s]['\"]?[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]{8,}
```

### Secret Detection Algorithm

```python
def scan_file_for_secrets(file_path):
    """
    Scan a file for potential secrets before committing.
    
    Returns:
        list: Detected secrets with line numbers and pattern names
    """
    secret_patterns = {
        'api_key': r'[aA][pP][iI][-_]?[kK][eE][yY][-_:=\s][\'"]?[a-zA-Z0-9]{20,}',
        'bearer_token': r'[bB][eE][aA][rR][eE][rR]\s+[a-zA-Z0-9\-_\.=]{20,}',
        'aws_access_key': r'AKIA[0-9A-Z]{16}',
        'huggingface_token': r'hf_[a-zA-Z0-9]{32,}',
        'openai_key': r'sk-[a-zA-Z0-9]{48}',
        'anthropic_key': r'sk-ant-[a-zA-Z0-9\-_]{95,}',
        'github_pat': r'gh[ps]_[a-zA-Z0-9]{36}',
        'ssh_private_key': r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',
        'generic_token': r'[tT][oO][kK][eE][nN][-_:=\s][\'"]?[a-zA-Z0-9]{20,}',
        'password': r'[pP][aA][sS][sS][wW][oO][rR][dD][-_:=\s][\'"]?[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]{8,}'
    }
    
    detections = []
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, start=1):
            for pattern_name, pattern in secret_patterns.items():
                if re.search(pattern, line):
                    detections.append({
                        'line': line_num,
                        'pattern': pattern_name,
                        'preview': line[:80] + '...' if len(line) > 80 else line
                    })
    
    return detections
```

### False Positive Handling

Some patterns may trigger false positives:

**Acceptable Contexts**:
- Comments explaining API key format: `# API Key format: sk-...`
- Documentation examples with clearly fake keys: `API_KEY=sk-example-not-a-real-key`
- Test fixtures with dummy credentials: `TEST_TOKEN = "test_" + "0" * 40`
- Environment variable declarations without values: `export WANDB_API_KEY=`

**Mitigation Strategy**:
1. **Context checking**: Examine surrounding lines to determine if the detection is in documentation/comments
2. **Keyword filtering**: Skip lines containing words like "example", "dummy", "test", "fake", "placeholder"
3. **Value validation**: Check if detected values are obviously fake (e.g., all zeros, repeated patterns)
4. **Manual review**: Present detections to user for confirmation when context is ambiguous

### Secret Detection Reporting

When secrets are detected before commit:

```
❌ Secret detection: 3 potential secrets found

File: src/training/config.py
  Line 42: api_key - OPENAI_API_KEY = "sk-..."
  Line 67: huggingface_token - HF_TOKEN = "hf_..."

File: notebooks/experiment.ipynb
  Line 15: bearer_token - Authorization: Bearer eyJ...

🛑 Commit blocked. Please review and remove secrets before committing.

Recommendations:
  1. Move secrets to .env file (already in .gitignore)
  2. Use environment variables: os.getenv('OPENAI_API_KEY')
  3. For development, use direnv or similar tools
  4. For production, use secret management systems

If these are false positives (documentation, examples):
  - Add "# nosecret" comment to the line to bypass detection
  - Ensure values are clearly fake/placeholder
```

## Large File Detection

Large files make Git repositories slow to clone and difficult to work with. Implement size-based warnings and blocks.

### Size Thresholds

**Warning threshold: 10 MB**
- Issue warning but allow commit with explicit confirmation
- Prompt user to consider alternatives (Git LFS, external storage)

**Block threshold: 50 MB**
- Block commit entirely
- Require user to remove file or add to external storage first

**Rationale**: GitHub has a 50 MB per-file warning and 100 MB hard limit. We set more conservative thresholds to keep repositories nimble.

### Size Detection Algorithm

```python
def check_file_sizes(files_to_commit):
    """
    Check file sizes against thresholds before committing.
    
    Returns:
        dict: warnings and blocks for large files
    """
    WARN_SIZE = 10 * 1024 * 1024  # 10 MB
    BLOCK_SIZE = 50 * 1024 * 1024  # 50 MB
    
    warnings = []
    blocks = []
    
    for file_path in files_to_commit:
        if not os.path.exists(file_path):
            continue
            
        size = os.path.getsize(file_path)
        size_mb = size / (1024 * 1024)
        
        if size >= BLOCK_SIZE:
            blocks.append({
                'file': file_path,
                'size_mb': round(size_mb, 2),
                'threshold': 'block'
            })
        elif size >= WARN_SIZE:
            warnings.append({
                'file': file_path,
                'size_mb': round(size_mb, 2),
                'threshold': 'warn'
            })
    
    return {'warnings': warnings, 'blocks': blocks}
```

### Large File Reporting

**Warning (10-50 MB)**:

```
⚠️  Large file warning:

File: data/preprocessed_dataset.json (23.5 MB)

This file is large and will slow down repository operations.
Consider alternatives:
  1. Use Git LFS (Large File Storage)
  2. Store in data/ and add to .gitignore if reproducible
  3. Use external storage (S3, cloud storage) and commit a download script
  4. Compress the file if possible

Proceed with commit? (yes/no)
```

**Block (>50 MB)**:

```
❌ Large file blocked:

File: outputs/results/all_predictions.json (127.3 MB)

This file exceeds the 50 MB commit limit and cannot be added to Git.

Required actions:
  1. Move to outputs/ directory (already in .gitignore)
  2. Or upload to external storage (S3, Hugging Face Datasets, etc.)
  3. Or split into smaller files (<10 MB each)
  4. Or use Git LFS for large binary files

Commit blocked. Remove or relocate the file to proceed.
```

### Exceptions to Size Limits

Some files may legitimately need to exceed thresholds:

**Acceptable large files**:
- Preprocessed datasets <50 MB that are expensive to regenerate
- Compiled documentation (PDFs, presentations) <20 MB
- Reference artifacts for reproducibility <30 MB

**Process for exceptions**:
1. User explicitly acknowledges the size
2. File is documented in repository README with justification
3. Alternative storage is not viable (explain why)
4. File is essential for reproduction (not regeneratable)

### Git LFS Recommendation

For legitimate large files, recommend Git LFS:

```bash
# Install Git LFS
git lfs install

# Track large file types
git lfs track "*.psd"
git lfs track "*.bin"
git lfs track "*.h5"

# Commit .gitattributes
git add .gitattributes
git commit -m "Configure Git LFS for large files"

# Now commit large files normally
git add large_file.psd
git commit -m "Add design assets"
```

**Note**: Git LFS is appropriate for binary assets that change infrequently. For frequently changing large files (datasets, intermediate results), external storage is better.

## Commit Safety Workflow

### Pre-Commit Validation Sequence

Before proposing any commit, execute these checks in order:

1. **File pattern matching**: Check all files against never-commit patterns
2. **Secret scanning**: Scan all text files for secret patterns
3. **Size checking**: Measure file sizes and compare against thresholds
4. **Manual review**: Present findings to user for final confirmation

### Automated Checks (Phase 2)

Phase 2 implementation uses manual agent-driven checks:

```python
def validate_commit_safety(files_to_commit, workspace_path):
    """
    Validate commit safety for a list of files.
    
    Returns:
        dict: validation results with blocks, warnings, and safe files
    """
    results = {
        'blocked': [],
        'warnings': [],
        'safe': [],
        'review_required': []
    }
    
    for file_path in files_to_commit:
        rel_path = os.path.relpath(file_path, workspace_path)
        
        # Check 1: File pattern blocking
        if is_blocked_pattern(rel_path):
            results['blocked'].append({
                'file': rel_path,
                'reason': 'blocked_pattern',
                'message': f'File type should not be committed: {rel_path}'
            })
            continue
        
        # Check 2: Secret detection
        secrets = scan_file_for_secrets(file_path)
        if secrets:
            results['blocked'].append({
                'file': rel_path,
                'reason': 'secrets_detected',
                'secrets': secrets
            })
            continue
        
        # Check 3: Size checking
        size_check = check_file_sizes([file_path])
        if size_check['blocks']:
            results['blocked'].append({
                'file': rel_path,
                'reason': 'size_exceeded',
                'size_mb': size_check['blocks'][0]['size_mb']
            })
            continue
        elif size_check['warnings']:
            results['warnings'].append({
                'file': rel_path,
                'reason': 'large_file',
                'size_mb': size_check['warnings'][0]['size_mb']
            })
            continue
        
        # Passed all checks
        results['safe'].append(rel_path)
    
    return results
```

### Reporting Format

Present validation results clearly to the user:

```
📋 Commit Safety Validation Results

✅ Safe to commit (15 files):
  experiments/learning-rate-sweep/plan.md
  experiments/learning-rate-sweep/jobs/train.yaml
  experiments/learning-rate-sweep/runs/train-lr1e4__20250115T142530/run.yaml
  experiments/learning-rate-sweep/results.yaml
  experiments/learning-rate-sweep/history.md
  experiments/learning-rate-sweep/journal.md
  project-log.md
  ... (8 more)

⚠️  Warnings (2 files):
  data/preprocessed_wikitext.json (15.3 MB) - Large file
    → Consider moving to external storage or compressing

❌ Blocked (1 file):
  src/config.py (0.8 KB) - Secret detected
    → Line 42: api_key pattern detected
    → Remove secret or move to .env file

Proceed with committing 15 safe files? (yes/no/review)
```

### User Options

After validation, offer these options:

1. **Commit safe files only**: Proceed with files that passed all checks
2. **Fix and retry**: User addresses warnings/blocks, then retry validation
3. **Review individually**: Show each file's status for manual override decisions
4. **Abort**: Cancel the commit operation

## Git Commit Best Practices

### Commit Message Format

Use conventional commit format for clarity:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New experiment or feature
- `exp`: Experiment execution/results
- `docs`: Documentation updates
- `refactor`: Code refactoring
- `fix`: Bug fixes
- `test`: Test additions/updates
- `chore`: Maintenance tasks

**Examples**:

```
exp(lora-rank): Complete rank=16 ablation run

- Executed train-r16 job on local GPU
- Training completed in 2h 15m
- Final validation loss: 2.347
- Results documented in experiments/lora-rank-ablation/results.yaml

Closes #42
```

```
docs(project): Update project-log with LoRA findings

Consolidated findings from lora-rank-ablation experiment:
- Rank=32 provides best performance/efficiency tradeoff
- Rank=64 shows diminishing returns
- Recommend rank=32 for future experiments
```

### What to Commit

**Always commit**:
- Experiment plans (`plan.md`)
- Job configurations (`jobs/*.yaml`)
- Run metadata (`runs/*/run.yaml`, `runs/*/resolved-job.yaml`)
- Results summaries (`results.yaml`)
- Research notes (`history.md`, `journal.md`)
- Project conclusions (`project-log.md`)
- Source code changes (`src/**/*.py`)
- Documentation updates (`*.md`)

**Never commit**:
- Model checkpoints (use HuggingFace Hub)
- Raw training logs (commit processed/structured logs only)
- Secrets and credentials
- Cache directories
- Large datasets (commit download scripts instead)

**Conditionally commit**:
- Processed logs (<1 MB): Yes
- Generated plots/figures (<5 MB): Yes, if part of documentation
- Small preprocessed datasets (<10 MB): Yes, if expensive to regenerate
- Configuration files: Yes, but scan for secrets first

### Atomic Commits

Each commit should represent a single logical unit:

- **One experiment run**: All files related to a single run
- **One documentation update**: Changes to related docs
- **One refactoring**: Self-contained code improvement

Avoid mixing unrelated changes in a single commit.

### Branch Strategy

**For experiments**:
- Create feature branch: `exp/lora-rank-ablation`
- Commit incremental progress
- Merge to main when experiment completes
- Tag significant results: `v1.0-lora-rank-results`

**For code changes**:
- Create feature branch: `feat/add-gradient-checkpointing`
- Implement and test changes
- Merge to main when stable
- Avoid committing broken code to main

## Phase Boundaries

### Phase 2 (Current): Manual Agent-Driven Checks

**Implemented**:
- ✅ File pattern blocking rules
- ✅ Secret detection patterns
- ✅ Size threshold checking
- ✅ Validation reporting format
- ✅ Commit proposal workflow

**Not Implemented**:
- ❌ Git pre-commit hooks
- ❌ Automated secret scanning on every commit
- ❌ CI/CD integration for validation
- ❌ Git LFS automatic setup

**Implementation Approach**: Codex manually runs validation checks before proposing commits and presents results to the user for review.

### Future Phases: Automated Enforcement

**Potential additions**:
- Git pre-commit hooks that run validation automatically
- CI/CD pipelines that verify commits don't contain secrets
- Integration with secret scanning services (GitHub Advanced Security, GitGuardian)
- Automatic Git LFS setup for large file patterns
- Branch protection rules that enforce validation

## Security Considerations

### Credential Rotation

If secrets are accidentally committed:

1. **Immediate action**: Rotate the compromised credential
2. **History cleaning**: Use `git filter-branch` or `BFG Repo-Cleaner` to remove from history
3. **Force push**: Update remote repository (⚠️ disruptive to collaborators)
4. **Notification**: Inform team members to re-clone repository
5. **Audit**: Check for unauthorized access using the compromised credential

**Prevention is better than remediation**: These checks aim to prevent this scenario.

### Public vs Private Repositories

These rules apply to both public and private repositories:

- **Public repos**: Secrets are immediately visible to anyone
- **Private repos**: Secrets are visible to all collaborators and in backups
- **Forked repos**: Secrets can leak through forks even if original is private

**Never assume privacy is sufficient protection for secrets.**

## References

- **Git Ignore Patterns**: https://git-scm.com/docs/gitignore
- **Git LFS Documentation**: https://git-lfs.github.com/
- **GitHub Secret Scanning**: https://docs.github.com/en/code-security/secret-scanning
- **Conventional Commits**: https://www.conventionalcommits.org/
- **BFG Repo-Cleaner**: https://rtyley.github.io/bfg-repo-cleaner/

## Document History

- **2025-01-XX**: Initial creation (Phase 2 implementation)
- **Status**: Draft for Phase 2 review
