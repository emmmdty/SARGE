# Reproducibility And Determinism

## Warning

Training logs reported the following class of warning:

```text
Deterministic behavior was enabled ... operation is not deterministic because it uses CuBLAS and CUDA >= 10.2 ... set CUBLAS_WORKSPACE_CONFIG=:4096:8 or :16:8.
```

## Interpretation

- This is a bit-level determinism and strict reproducibility risk.
- It does not directly prove that the existing metrics are wrong.
- Existing metrics remain artifact-level evidence tied to saved predictions,
  manifests, and evaluator outputs.
- The repository must not claim the affected training/generation path is fully
  bitwise reproducible.
- Existing test-reference outputs must not be rerun automatically because of
  this warning.

## Required Future Wrapper Environment

Future training, inference, and evaluation shell wrappers must set deterministic
environment variables before Python starts:

```bash
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONHASHSEED=42
```

Use `:16:8` only if a future documented environment cannot run with `:4096:8`.

## Paper Wording

Allowed wording:

- “The reported results are preserved as artifact-level evidence.”
- “Strict bitwise reproducibility is not claimed because CUDA/CuBLAS emitted a
  deterministic warn-only message in earlier runs.”

Forbidden wording:

- “All reported training and inference runs are bitwise reproducible.”
- “The CUBLAS warning invalidates existing metrics.”
- “The warning requires rerunning the existing test-reference result.”
