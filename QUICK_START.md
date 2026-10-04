# 🎯 Quick Start Guide - Production Features

## Testing Parameter Validation

All these will error gracefully with clear messages:

```bash
# ❌ Invalid batch size
python from_scratch_transformer.py --batch_size -1
# Error: ❌ batch_size must be positive, got -1

# ❌ Invalid learning rate  
python from_scratch_transformer.py --lr 0
# Error: ❌ lr must be positive, got 0

# ❌ min_lr > lr
python from_scratch_transformer.py --lr 1e-4 --min_lr 1e-3
# Error: ❌ min_lr (0.001) must be <= lr (0.0001)

# ✅ All parameters validated successfully
python from_scratch_transformer.py --batch_size 4 --seq_len 512
```

---

## Memory Estimation (Before Training)

```bash
# See VRAM needs before committing to training
python from_scratch_transformer.py --estimate_memory

# Output shows breakdown:
# 📊 VRAM USAGE ESTIMATION
# ============================================================
# Model weights:          0.30 GB
# Activations (forward):  0.12 GB
# Attention matrices:     0.08 GB
# Gradients:              0.30 GB
# Optimizer states:       0.60 GB
#
# 📈 TRAINING (batch_size=2):  1.40 GB
# 📉 INFERENCE (batch_size=2): 0.52 GB
```

---

## Gradient Clipping (Prevents Exploding Gradients)

```bash
# Default: clip at norm 1.0
python from_scratch_transformer.py

# More aggressive clipping (for unstable training)
python from_scratch_transformer.py --grad_clip 0.5

# No clipping (not recommended)
python from_scratch_transformer.py --grad_clip 0

# In training loop, you'll see stable loss updates
# [step    10] loss=2.3456 (accum 1/4) lr=3.00e-04
# [step    15] loss=2.1234 (accum 2/4) lr=3.00e-04  <- no spikes!
```

---

## Learning Rate Floor (Prevents Training Stall)

```bash
# Default: min LR is 1e-5
python from_scratch_transformer.py

# Start with higher floor (if LR decays too fast)
python from_scratch_transformer.py --min_lr 1e-4

# In training loop, LR will never go below min_lr:
# [step  390] loss=1.5234 (accum 3/4) lr=1.00e-05  <- clamped to floor
# [step  395] loss=1.4890 (accum 4/4) lr=1.00e-05  <- stays here
```

---

## Generation Validation (Prevents Crashes)

These operations now validate parameters:

```python
from from_scratch_transformer import sample

# ❌ This will error with clear message
sample(model, start_ids, temp=-1.0)
# ValueError: Temperature must be positive, got -1.0

# ❌ This will error  
sample(model, start_ids, repetition_penalty=0.5)
# ValueError: Repetition penalty must be >= 1.0, got 0.5

# ✅ Valid generation
output = sample(model, start_ids, temp=0.8, repetition_penalty=1.2)
```

---

## Numerical Stability (No More NaN)

Logits are automatically clipped before softmax:

```python
# Even with extreme temperature, no overflow:
output = sample(model, start_ids, temp=100.0)  # Would crash before
# Now handled gracefully - logits clamped to [-50, 50]

# Batch processing stays stable:
outputs = sample(
    model, 
    [prompt1, prompt2, prompt3],
    temp=0.6,
    batch_size=3
)
```

---

## Combined Training Command (Production Settings)

```bash
python from_scratch_transformer.py \
    --batch_size 4 \
    --seq_len 512 \
    --max_steps 5000 \
    --lr 3e-4 \
    --min_lr 1e-5 \
    --grad_clip 1.0 \
    --grad_accum 4 \
    --use_amp \
    --grad_ckpt \
    --file training/
```

Expected output:
```
✅ All parameters validated successfully
📊 VRAM USAGE ESTIMATION
============================================================
Model weights:          0.30 GB
...
📈 TRAINING (batch_size=4):  2.10 GB
📉 INFERENCE (batch_size=4): 0.68 GB
============================================================

Starting V.O.I.D. Transformer Training
============================================================

Training from step 0 to 5000...
Gradient accumulation: 4 steps

[step     5] loss=4.8234 (accum 1/4) lr=3.00e-04
[step    10] loss=4.7156 (accum 2/4) lr=3.00e-04
[OPTIM STEP    10/5000] avg_loss=4.7695 lr=3.00e-04 elapsed=2s
[step    15] loss=4.6234 (accum 3/4) lr=3.00e-04
...
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Memory exceeded" error | Run `--estimate_memory` first, reduce batch_size or seq_len |
| Training loss spikes → NaN | Increase `--grad_clip` (e.g., 0.5) |
| Training loss plateaus early | Increase `--min_lr` (e.g., 1e-4) |
| Generation crashes | Use proper `temp > 0` and `repetition_penalty >= 1.0` |
| Batch inference fails | All sequences must use valid parameters |

---

## Performance Tips

1. **Memory**: Use `--estimate_memory` first to plan batch size
2. **Speed**: Use `--use_amp` for 2-3x faster training on CUDA
3. **Stability**: Use `--grad_clip 1.0` if loss spikes occur
4. **Convergence**: Adjust `--min_lr` if training stalls early
5. **Checkpointing**: Use `--grad_ckpt` if training runs out of memory

---

## What's Protected Now

✅ **Startup**: Bad arguments caught immediately with clear errors
✅ **Training**: Exploding gradients clipped, LR never stalls
✅ **Generation**: Invalid parameters caught, no silent failures
✅ **Numerics**: Logits clamped before softmax, no NaN overflow
✅ **Inference**: Batch optimizations skip finished sequences
✅ **Planning**: Memory estimator helps predict resource needs

You now have a production-ready transformer! 🚀
