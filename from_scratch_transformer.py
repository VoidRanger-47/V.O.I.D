# from_scratch_transformer.py
# Build and train a GPT-style Transformer from scratch (byte-level tokenizer).
# No external APIs, no pretrained models.
# Requirements: torch, tiktoken
# Usage:
#   python from_scratch_transformer.py

import sys
import io

# Fix Windows console encoding for emojis and errors
if sys.platform == "win32":
    # Fix both stdout and stderr for UTF-8 output
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    # Fallback for older Python versions
    if not hasattr(sys.stdout, 'reconfigure'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import torch.utils.checkpoint as cp
import json
import os
import math
import time
import argparse
import glob
import tiktoken
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.nn import functional as F

# Try importing pdf_utils, handle failure if missing
try:
    from pdf_utils import pdf_to_text, save_text
except ImportError:
    def pdf_to_text(path): return ""
    def save_text(text, path): pass
    print("⚠️ pdf_utils not found. PDF support disabled.")

print(torch.cuda.is_available())
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = True
print("Using device:", device)


# -------------------------
# Args / Config
# -------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--use_amp", action="store_true", help="Use mixed precision (fp16) on CUDA")
parser.add_argument("--grad_ckpt", action="store_true", help="Enable gradient checkpointing")
parser.add_argument("--grad_accum", type=int, default=4, help="Gradient accumulation steps")
parser.add_argument("--file", type=str, default="training", help="Training text file (utf-8)")
parser.add_argument("--seq_len", type=int, default=256, help="Context length (tokens / bytes)")
parser.add_argument("--batch_size", type=int, default=2, help="Batch size")
parser.add_argument("--d_model", type=int, default=400, help="Model hidden size (d_model)")
parser.add_argument("--n_head", type=int, default=8, help="Number of attention heads")
parser.add_argument("--n_layer", type=int, default=12, help="Number of transformer blocks")
parser.add_argument("--dropout", type=float, default=0.1, help="Dropout")
parser.add_argument("--epochs", type=int, default=2000, help="Number of training steps (not epochs)")
parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", help="Device")
parser.add_argument("--save_every", type=int, default=200, help="Save checkpoint every N steps")
parser.add_argument("--checkpoint", type=str, default="checkpoint.pt", help="Checkpoint path")
parser.add_argument("--generate_every", type=int, default=100, help="Generate sample every N steps")
parser.add_argument("--gen_temp", type=float, default=0.6, help="Generation temperature")
parser.add_argument("--top_k", type=int, default=40, help="Top-k sampling")
parser.add_argument("--max_steps", type=int, default=600, help="Total training steps")
parser.add_argument("--seed", type=int, default=42, help="Random seed")
parser.add_argument("--export_model", type=str, default=None, help="Export model-only checkpoint to this path")
parser.add_argument("--import_model", type=str, default=None, help="Import model-only checkpoint from this path")
parser.add_argument("--estimate_memory", action="store_true", help="Estimate VRAM requirements and exit")
parser.add_argument("--grad_clip", type=float, default=1.0, help="Gradient clipping norm (0 = disabled)")
parser.add_argument("--min_lr", type=float, default=1e-5, help="Minimum learning rate")
parser.add_argument("--warmup_steps", type=int, default=None, help="Number of warmup steps (default: 10% of max_steps)")
args, _ = parser.parse_known_args()

# -------------------------
# PARAMETER VALIDATION
# -------------------------
def validate_args(args):
    """Validate command-line arguments before training."""
    errors = []
    
    # Batch size validation
    if args.batch_size <= 0:
        errors.append(f"❌ batch_size must be positive, got {args.batch_size}")
    
    # Sequence length validation
    if args.seq_len <= 0:
        errors.append(f"❌ seq_len must be positive, got {args.seq_len}")
    
    # Learning rate validation
    if args.lr <= 0:
        errors.append(f"❌ lr must be positive, got {args.lr}")
    if args.min_lr < 0:
        errors.append(f"❌ min_lr must be non-negative, got {args.min_lr}")
    if args.min_lr > args.lr:
        errors.append(f"❌ min_lr ({args.min_lr}) must be <= lr ({args.lr})")
    
    # Max steps validation
    if args.max_steps <= 0:
        errors.append(f"❌ max_steps must be positive, got {args.max_steps}")
    
    # Gradient accumulation validation
    if args.grad_accum <= 0:
        errors.append(f"❌ grad_accum must be positive, got {args.grad_accum}")
    
    # Generation parameters validation
    if args.gen_temp <= 0:
        errors.append(f"❌ gen_temp must be positive, got {args.gen_temp}")
    
    if args.top_k <= 0:
        errors.append(f"❌ top_k must be positive, got {args.top_k}")
    
    if args.dropout < 0 or args.dropout >= 1.0:
        errors.append(f"❌ dropout must be in [0, 1), got {args.dropout}")
    
    if args.grad_clip < 0:
        errors.append(f"❌ grad_clip must be non-negative, got {args.grad_clip}")
    
    if args.warmup_steps is not None:
        if args.warmup_steps < 0:
            errors.append(f"❌ warmup_steps must be non-negative, got {args.warmup_steps}")
        if args.warmup_steps >= args.max_steps:
            errors.append(f"❌ warmup_steps ({args.warmup_steps}) must be < max_steps ({args.max_steps})")
    
    if errors:
        print("\n" + "\n".join(errors))
        sys.exit(1)
    
    print("✅ All parameters validated successfully")

validate_args(args)
torch.manual_seed(args.seed)


CODE_EXTENSIONS = (
    ".txt", ".jsonl", ".pdf",  # Existing supported formats
    ".py", ".js", ".jsx", ".ts", ".tsx",  # Python/JavaScript/TypeScript
    ".java", ".cpp", ".c", ".h", ".cs",  # C-family/Java
    ".html", ".css", ".scss", ".xml", ".json",  # Web/Markup
    ".sh", ".bash", ".ps1", ".yaml", ".yml", ".md",  # Shell/Config/Markdown
)

# -------------------------
# Create sample train_text if missing
# -------------------------
if not os.path.exists(args.file):
    sample_text = ("""This is VOID's training center ok ok""")
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(sample_text)
    print(f"Created sample {args.file}; replace it with your dataset for better results.")


# -------------------------
# Load training data
# -------------------------
# Helper to process a single file
def parse_jsonl_dataset(file_path):
    text_data = []
    print(f"📂 Parsing JSONL: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if "messages" in data:
                    conversation = ""
                    for msg in data["messages"]:
                        raw_role = msg.get("role", "").lower()
                        content = msg.get("content", "")
                        display_role = "V.O.I.D." if raw_role == "assistant" else "User" if raw_role == "user" else raw_role.capitalize()
                        conversation += f"### {display_role}:\n{content}\n"
                    conversation += "\n<|endoftext|>\n"
                    text_data.append(conversation)
            except json.JSONDecodeError:
                continue
    return "".join(text_data)

def read_file_content(path):
    if path.lower().endswith(".pdf"):
        print(f"📄 Processing PDF: {path}")
        return pdf_to_text(path)
    elif path.lower().endswith(".jsonl"):
        return parse_jsonl_dataset(path)
    else:
        print(f"📄 Processing Text: {path}")
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip() + "\n"

input_path = args.file
full_dataset_text = ""

if os.path.isdir(input_path):
    print(f"📂 Detected directory: {input_path}. Scanning for files...")
    files = glob.glob(os.path.join(input_path, "*"))
    for file_p in files:
        if file_p.endswith(CODE_EXTENSIONS):
            full_dataset_text += read_file_content(file_p)
            full_dataset_text += "<|endoftext|>\n"
else:
    if not os.path.exists(input_path):
        print(f"⚠️ File {input_path} not found. Creating sample...")
        with open(input_path, "w", encoding="utf-8") as f:
            f.write("Sample text for training.")
    full_dataset_text = read_file_content(input_path)

text = full_dataset_text
print(f"✅ Total loaded dataset size: {len(text)} characters")

if not text.strip():
    raise ValueError("❌ Training data is empty! Please check your file path or contents.")


# -------------------------
# GPT-Style Tokenizer (cl100k_base) with offline fallback
# -------------------------
class GPTTokenizer:
    def __init__(self, model_name="cl100k_base"):
        try:
            self.enc = tiktoken.get_encoding(model_name)
            self.vocab_size = self.enc.n_vocab
            self.offline_mode = False
        except Exception as e:
            print(f"⚠️ Could not load tiktoken ({type(e).__name__}), using offline character tokenizer")
            self.enc = None
            self.vocab_size = 256  # ASCII range + special tokens
            self.offline_mode = True

    def encode(self, text):
        if self.offline_mode:
            # Character-level encoding
            return [ord(c) for c in text] + [0]  # 0 = end of text token
        else:
            return self.enc.encode(text, allowed_special={"<|endoftext|>"})

    def decode(self, ids):
        if self.offline_mode:
            # Character-level decoding
            return "".join(chr(i) for i in ids if i > 0 and i < 256)
        else:
            return self.enc.decode(ids)

tokenizer = GPTTokenizer("cl100k_base")
data = torch.tensor(tokenizer.encode(text), dtype=torch.long)
print(f"Vocab size: {tokenizer.vocab_size}")

# Split Data for Validation
n = int(0.9 * len(data))
train_data = data[:n]
val_data = data[n:]

def get_batch(split, batch_size=8, seq_len=128):
    data_src = train_data if split == "train" else val_data
    if len(data_src) <= seq_len:
        # Fallback for very small datasets
        data_src = data
    ix = torch.randint(len(data_src) - seq_len, (batch_size,))
    x = torch.stack([data_src[i:i+seq_len] for i in ix])
    y = torch.stack([data_src[i+1:i+seq_len+1] for i in ix])
    return x, y

# -------------------------
# Dataset (For Main Loader)
# -------------------------
class TextDataset(Dataset):
    def __init__(self, token_data, seq_len):
        self.tokens = token_data
        self.seq_len = seq_len

    def __len__(self):
        return max(1, len(self.tokens) - self.seq_len)

    def __getitem__(self, idx):
        # Safety check for idx
        if idx >= len(self.tokens) - self.seq_len:
            idx = 0
        x = self.tokens[idx: idx + self.seq_len]
        y = self.tokens[idx + 1: idx + self.seq_len + 1]
        return torch.tensor(x, dtype=torch.long), torch.tensor(y, dtype=torch.long)

# Use train_data for the dataloader so we don't train on validation set
dataset = TextDataset(train_data, args.seq_len)
dloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)
print(f"Dataset size: {len(dataset)} sequences.")

# -------------------------
# Model Components
# -------------------------
class RotaryEmbedding(nn.Module):
    def __init__(self, dim):
        super().__init__()
        inv_freq = 1.0 / (10000 ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq)
    
    def apply_rotary(self, x):
        x1, x2 = x[..., ::2], x[..., 1::2]
        T = x.shape[1]
        freqs = torch.einsum("i,j->ij", torch.arange(T, device=x.device), self.inv_freq)
        cos, sin = freqs.cos()[None, :, None, :], freqs.sin()[None, :, None, :]
        x_rotated = torch.cat([x1 * cos - x2 * sin, x1 * sin + x2 * cos], dim=-1)
        return x_rotated

class LayerNorm(nn.Module):
    def __init__(self, dim, eps=1e-5):
        super().__init__()
        self.gamma = nn.Parameter(torch.ones(dim))
        self.beta = nn.Parameter(torch.zeros(dim))
        self.eps = eps
    def forward(self, x):
        mean = x.mean(-1, keepdim=True)
        var = ((x - mean) ** 2).mean(-1, keepdim=True)
        return (x - mean) / torch.sqrt(var + self.eps) * self.gamma + self.beta

class FeedForward(nn.Module):
    def __init__(self, d_model, d_ff, dropout):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout)
        )
    def forward(self, x):
        return self.net(x)

class TransformerBlock(nn.Module):
    def __init__(self, d_model, n_head, d_ff, dropout):
        super().__init__()
        self.n_head = n_head
        self.d_model = d_model
        self.head_dim = d_model // n_head
        assert self.head_dim * n_head == d_model, "d_model must be divisible by n_head"

        self.ln1 = LayerNorm(d_model)
        self.ln2 = LayerNorm(d_model)
        self.ff = FeedForward(d_model, d_ff, dropout)
        self.dropout = nn.Dropout(dropout)
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)
        self.rotary_emb = RotaryEmbedding(self.head_dim)

    def forward(self, x, attn_mask=None, kv_cache=None, seq_lengths=None):
        """
        Forward pass with optional sequence length masking.
        
        Args:
            x: Input embeddings (batch_size, seq_len, d_model)
            attn_mask: Causal attention mask
            kv_cache: Previous KV cache for incremental decoding
            seq_lengths: Actual lengths of each sequence (for padding masking)
        """
        residual = x
        x_ln = self.ln1(x)

        def attn_forward(x_in, mask, kv_c, seq_lens):
            B, T, D = x_in.size()
            q = self.q_proj(x_in).view(B, T, self.n_head, self.head_dim)
            k = self.k_proj(x_in).view(B, T, self.n_head, self.head_dim)
            v = self.v_proj(x_in).view(B, T, self.n_head, self.head_dim)
            q = self.rotary_emb.apply_rotary(q)
            k = self.rotary_emb.apply_rotary(k)

            # KV Cache: concatenate with cached k, v if available
            new_kv = (k, v)
            if kv_c is not None:
                k_cached, v_cached = kv_c
                k = torch.cat([k_cached, k], dim=1)
                v = torch.cat([v_cached, v], dim=1)

            # Try hardware-accelerated scaled_dot_product_attention (FlashAttention)
            if hasattr(F, "scaled_dot_product_attention") and seq_lens is None and mask is None and kv_c is None:
                q_t = q.transpose(1, 2)  # (B, n_head, T, head_dim)
                k_t = k.transpose(1, 2)
                v_t = v.transpose(1, 2)
                drop_p = self.dropout.p if self.training else 0.0
                attn_out_sdpa = F.scaled_dot_product_attention(q_t, k_t, v_t, is_causal=True, dropout_p=drop_p)
                attn_out = attn_out_sdpa.transpose(1, 2).contiguous().view(B, T, D)
                return self.out_proj(attn_out), new_kv

            attn_scores = torch.einsum("bthd,bshd->bhts", q, k) / math.sqrt(self.head_dim)
            
            # Apply causal mask if provided
            if mask is not None:
                m = mask.to(attn_scores.device)
                attn_scores = attn_scores.masked_fill(m.unsqueeze(0).unsqueeze(0), float("-inf"))
            
            # Apply sequence length mask (mask out padding tokens)
            # This prevents attention to padded positions
            if seq_lens is not None:
                for b in range(B):
                    if seq_lens[b] < T:
                        # Mask all positions beyond actual sequence length
                        attn_scores[b, :, :, seq_lens[b]:] = float("-inf")

            attn_probs = F.softmax(attn_scores, dim=-1)
            attn_probs = self.dropout(attn_probs)
            attn_out = torch.einsum("bhtT,bThd->bthd", attn_probs, v).contiguous().view(B, T, D)
            return self.out_proj(attn_out), new_kv

        if getattr(self, "use_checkpoint", False):
            attn_out, new_kv = cp.checkpoint(attn_forward, x_ln, attn_mask, kv_cache, seq_lengths, use_reentrant=False)
        else:
            attn_out, new_kv = attn_forward(x_ln, attn_mask, kv_cache, seq_lengths)

        x = residual + attn_out
        residual2 = x
        x_ln2 = self.ln2(x)

        def ff_forward(x_in):
            return self.ff(x_in)

        if getattr(self, "use_checkpoint", False):
            ff_out = cp.checkpoint(ff_forward, x_ln2, use_reentrant=False)
        else:
            ff_out = ff_forward(x_ln2)

        x = residual2 + ff_out
        return x, new_kv

class TinyGPT(nn.Module):
    def __init__(self, vocab_size, seq_len, d_model, n_layer, n_head, dropout=0.1):
        super().__init__()
        self.vocab_size = vocab_size
        self.seq_len = seq_len
        self.token_emb = nn.Embedding(vocab_size, d_model)
        self.ln_f = LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)
        d_ff = d_model * 4
        self.blocks = nn.ModuleList([
            TransformerBlock(d_model=d_model, n_head=n_head, d_ff=d_ff, dropout=dropout)
            for _ in range(n_layer)
        ])

    def forward(self, idx, kv_caches=None, use_kv_cache=False, seq_lengths=None):
        """
        Forward pass with sequence length awareness.
        
        Args:
            idx: Token indices (batch_size, seq_len)
            kv_caches: Previous KV caches for incremental decoding
            use_kv_cache: Whether to use KV cache
            seq_lengths: Actual lengths of sequences (batch_size,) for attention masking
        """
        B, T = idx.size()
        x = self.token_emb(idx) * math.sqrt(self.token_emb.embedding_dim)
        drop_p = self.blocks[0].dropout.p if len(self.blocks) > 0 else 0.0
        x = F.dropout(x, p=drop_p, training=self.training)
        
        # Dynamic attention mask: only create as needed
        if use_kv_cache and kv_caches is not None and T == 1:
            # Single token generation: no mask needed
            attn_mask = None
        else:
            # Full context: use causal mask
            if not hasattr(self, "cached_mask") or self.cached_mask.size(-1) != T:
                self.cached_mask = torch.triu(torch.ones(T, T, device=idx.device), diagonal=1).bool()
            attn_mask = self.cached_mask

        new_kv_caches = [] if use_kv_cache else None
        for i, blk in enumerate(self.blocks):
            kv_cache = None
            if use_kv_cache and kv_caches is not None:
                kv_cache = kv_caches[i] if i < len(kv_caches) else None
            
            if getattr(self, "grad_ckpt", False):
                x, new_kv = cp.checkpoint(blk, x, attn_mask, kv_cache, seq_lengths, use_reentrant=False)
            else:
                x, new_kv = blk(x, attn_mask=attn_mask, kv_cache=kv_cache, seq_lengths=seq_lengths)
            
            if use_kv_cache:
                new_kv_caches.append(new_kv)

        x = self.ln_f(x)
        logits = self.head(x)
        return logits, new_kv_caches

def top_p_filtering(logits, top_p=0.9):
    sorted_logits, sorted_indices = torch.sort(logits, descending=True)
    sorted_probs = F.softmax(sorted_logits, dim=-1)
    cumulative_probs = sorted_probs.cumsum(dim=-1)
    sorted_mask = cumulative_probs > top_p
    sorted_mask[..., 1:] = sorted_mask[..., :-1].clone()
    sorted_mask[..., 0] = 0
    mask = torch.zeros_like(logits, dtype=torch.bool)
    mask.scatter_(dim=-1, index=sorted_indices, src=sorted_mask)
    logits = logits.masked_fill(mask, float("-inf"))
    return logits

# -------------------------
# Initialization
# -------------------------
model = TinyGPT(vocab_size=tokenizer.vocab_size, seq_len=args.seq_len,
                d_model=args.d_model, n_layer=args.n_layer, n_head=args.n_head, dropout=args.dropout)
model = model.to(args.device)

if args.grad_ckpt:
    model.grad_ckpt = True
    for blk in model.blocks:
        blk.use_checkpoint = True
    print("Gradient checkpointing ENABLED")

print(f"Model params: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

# Optimizer
optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)

# -------------------------
# MEMORY ESTIMATOR
# -------------------------
def estimate_vram_usage(vocab_size, d_model, n_layer, seq_len, batch_size, use_grad_ckpt=False):
    """Estimate VRAM requirements in GB for training and inference."""
    print("\n" + "="*60)
    print("📊 VRAM USAGE ESTIMATION")
    print("="*60)
    
    # Model parameters (float32 = 4 bytes each)
    embed_params = vocab_size * d_model
    head_params = vocab_size * d_model
    ln_params = 2 * d_model * 2  # gamma + beta per layer
    
    # Per layer: Q, K, V, Out projections + FF layer
    proj_params = 4 * d_model * d_model  # Q, K, V, Out
    ff_params = 2 * d_model * (4 * d_model)  # 4x expansion
    layer_ln_params = 4 * d_model  # 2 layer norms
    per_layer = proj_params + ff_params + layer_ln_params
    
    total_params = embed_params + head_params + ln_params + (n_layer * per_layer)
    model_size_gb = (total_params * 4) / (1024**3)
    
    # Activations during forward pass
    # Batch x seq_len x d_model tensors
    batch_activations = (seq_len * d_model * 4) / (1024**3)  # One layer activation
    total_activations_gb = batch_activations * n_layer * batch_size
    
    # Attention matrices: batch x seq_len x seq_len x head_dim
    # But we compute per head, so split by heads
    attn_matrices_gb = (batch_size * seq_len * seq_len * 4) / (1024**3)
    
    # Gradients (same as model)
    gradients_gb = model_size_gb
    
    # Optimizer state (Adam = 2 extra states per parameter)
    optimizer_states_gb = model_size_gb * 2
    
    # KV cache (only for inference)
    # Per layer: batch x seq_len x d_model
    kv_cache_gb = (batch_size * seq_len * d_model * 4 * 2 * n_layer) / (1024**3)
    
    # Training memory
    training_total = model_size_gb + total_activations_gb + attn_matrices_gb + gradients_gb + optimizer_states_gb
    if use_grad_ckpt:
        training_total -= total_activations_gb * 0.7  # Grad checkpoint saves ~70% of activations
    
    # Inference memory
    inference_total = model_size_gb + batch_activations * batch_size + attn_matrices_gb + kv_cache_gb
    
    print(f"Model weights:          {model_size_gb:.2f} GB")
    print(f"Activations (forward):  {total_activations_gb:.2f} GB")
    print(f"Attention matrices:     {attn_matrices_gb:.2f} GB")
    print(f"Gradients:              {gradients_gb:.2f} GB")
    print(f"Optimizer states:       {optimizer_states_gb:.2f} GB")
    if use_grad_ckpt:
        print(f"(With gradient checkpt: -{total_activations_gb * 0.7:.2f} GB)")
    
    print(f"\n📈 TRAINING (batch_size={batch_size}):  {training_total:.2f} GB")
    print(f"📉 INFERENCE (batch_size={batch_size}): {inference_total:.2f} GB")
    print("="*60 + "\n")
    
    return training_total, inference_total

# Call memory estimator if requested
if args.estimate_memory:
    train_mem, infer_mem = estimate_vram_usage(
        tokenizer.vocab_size, args.d_model, args.n_layer, 
        args.seq_len, args.batch_size, args.grad_ckpt
    )
    sys.exit(0)

def get_lr(step, max_steps, base_lr, min_lr=None, warmup_steps=None):
    """Cosine learning rate schedule with warmup and minimum bound.
    
    Schedule:
    1. Warmup: linear ramp from base_lr/10 to base_lr over warmup_steps
    2. Decay: cosine annealing from base_lr to min_lr
    """
    if min_lr is None:
        min_lr = args.min_lr
    if warmup_steps is None:
        warmup_steps = args.warmup_steps if args.warmup_steps else max(1, int(0.1 * max_steps))
    
    # Linear warmup phase
    if step < warmup_steps:
        return base_lr * (0.1 + 0.9 * (step / warmup_steps))
    
    # Cosine annealing phase (after warmup)
    progress = (step - warmup_steps) / max(1, max_steps - warmup_steps)
    cosine_lr = base_lr * 0.5 * (1.0 + math.cos(math.pi * progress))
    
    # Clamp to minimum
    return max(cosine_lr, min_lr)

# Checkpoint validation function
def validate_checkpoint(ckpt_data, expected_vocab_size, expected_config=None):
    """Validate checkpoint compatibility before loading."""
    if not isinstance(ckpt_data, dict):
        raise ValueError("Checkpoint must be a dictionary")
    
    if "model" not in ckpt_data:
        raise ValueError("Checkpoint missing 'model' key")
    
    # Check vocab size from embedding layer
    model_state = ckpt_data["model"]
    if "token_emb.weight" in model_state:
        ckpt_vocab_size = model_state["token_emb.weight"].shape[0]
        if ckpt_vocab_size != expected_vocab_size:
            raise ValueError(f"Vocab size mismatch: checkpoint has {ckpt_vocab_size}, expected {expected_vocab_size}")
    
    # Check for required model keys
    required_keys = ["token_emb.weight", "head.weight", "ln_f.gamma", "ln_f.beta"]
    missing = [k for k in required_keys if k not in model_state]
    if missing:
        raise ValueError(f"Checkpoint missing required keys: {missing}")
    
    return True

# Load Checkpoint
start_step = 0
if os.path.exists(args.checkpoint):
    print("Loading checkpoint...", args.checkpoint)
    try:
        ckpt = torch.load(args.checkpoint, map_location=args.device, weights_only=False)
        
        # Validate checkpoint before loading
        validate_checkpoint(ckpt, tokenizer.vocab_size)
        
        state = ckpt.get("model", ckpt) if isinstance(ckpt, dict) else ckpt
        model.load_state_dict(state)
        if isinstance(ckpt, dict) and "optim" in ckpt:
            optimizer.load_state_dict(ckpt["optim"])
            start_step = ckpt.get("step", 0) + 1
        print(f"Resuming from step {start_step}")
    except Exception as e:
        print(f"❌ Checkpoint error ({type(e).__name__}): {e}")
        print(f"⚠️ Starting fresh training...")
        start_step = 0

# Load model-only checkpoint if provided
if args.import_model and os.path.exists(args.import_model):
    print(f"Loading model from {args.import_model}")
    try:
        model_state = torch.load(args.import_model, map_location=args.device, weights_only=True)
        
        # Validate model weights
        if "token_emb.weight" in model_state:
            ckpt_vocab = model_state["token_emb.weight"].shape[0]
            if ckpt_vocab != tokenizer.vocab_size:
                raise ValueError(f"Vocab mismatch: file has {ckpt_vocab}, expected {tokenizer.vocab_size}")
        
        model.load_state_dict(model_state)
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        sys.exit(1)

# -------------------------
# Model Export/Import Utils
# -------------------------
def export_model(model, path):
    """Export model weights only (no optimizer state)."""
    torch.save(model.state_dict(), path)
    print(f"✅ Model exported to {path}")

def import_model(model, path, device=args.device):
    """Import model weights only."""
    state_dict = torch.load(path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    print(f"✅ Model imported from {path}")
    return model

def export_onnx(model, output_path, input_shape=(1, 256)):
    """Export model to ONNX format for deployment."""
    try:
        import torch.onnx
        dummy_input = torch.randint(0, model.vocab_size, input_shape, device=args.device)
        torch.onnx.export(
            model, 
            (dummy_input, None, False),
            output_path,
            input_names=["input_ids", "kv_caches", "use_kv_cache"],
            output_names=["logits", "new_kv_caches"],
            opset_version=14
        )
        print(f"✅ Model exported to ONNX: {output_path}")
    except Exception as e:
        print(f"❌ ONNX export failed: {e}")

# -------------------------
# Generation Utils
# -------------------------
def sample(model, start_bytes, length=200, temp=0.6, top_k=40, top_p=None, repetition_penalty=1.5, device=args.device, eos_token=0, batch_size=1):
    """Generate tokens with KV cache, batch support, and device placement.
    
    Key optimizations:
    - KV cache: avoids recomputing attention on old tokens
    - Context sliding: keeps only last seq_len tokens to bound memory
    - Repetition penalty window: only penalizes last 50 tokens (O(1) instead of O(n))
    - Early stopping: halts on EOS token
    - Inactive sequence optimization: stops computing for finished sequences
    """
    # Validate generation parameters
    if temp <= 0:
        raise ValueError(f"Temperature must be positive, got {temp}")
    if repetition_penalty < 1.0:
        raise ValueError(f"Repetition penalty must be >= 1.0, got {repetition_penalty}")
    if top_k is not None and top_k <= 0:
        raise ValueError(f"top_k must be positive, got {top_k}")
    
    model.eval()
    
    # Handle both single sequence and batch
    if isinstance(start_bytes, list) and isinstance(start_bytes[0], int):
        start_bytes = [start_bytes]
    
    batch_size = len(start_bytes)
    max_len = max(len(s) for s in start_bytes)
    
    # Pad sequences to same length
    padded_bytes = []
    for seq in start_bytes:
        padded_seq = seq + [0] * (max_len - len(seq))
        padded_bytes.append(padded_seq)
    
    context = torch.tensor(padded_bytes, dtype=torch.long, device=device)
    kv_caches = None
    generated_ids = [[] for _ in range(batch_size)]
    active = torch.ones(batch_size, dtype=torch.bool, device=device)
    recent_window = 50  # Only penalize last 50 tokens for repetition
    
    with torch.no_grad():
        for step in range(length):
            if not active.any():
                break
            
            # MEMORY OPTIMIZATION: Aggressively slide context window
            # This keeps memory bounded regardless of generation length
            if context.size(1) > args.seq_len:
                # Slide window: keep only last seq_len tokens
                context = context[:, -args.seq_len:]
                kv_caches = None  # Reset cache at sliding boundary
                input_ids = context
            else:
                if step == 0:
                    input_ids = context
                else:
                    input_ids = next_token
            
            # Forward pass - ensure device placement
            input_ids = input_ids.to(device)
            logits, kv_caches = model(input_ids, kv_caches=kv_caches, use_kv_cache=(step > 0))
            
            # Ensure KV caches stay on device (DEVICE PLACEMENT FIX)
            if kv_caches is not None:
                kv_caches = [(k.to(device), v.to(device)) if isinstance(k, torch.Tensor) else (k, v) for k, v in kv_caches]
            
            logits = logits[:, -1, :].to(device)
            
            # Temperature scaling (applied to logits before softmax for proper distribution)
            if temp > 0:
                logits = logits / temp
            else:
                logits = logits / 1e-7

            # REPETITION PENALTY OPTIMIZATION: O(1) window instead of O(n) loop
            # Only penalize recent tokens, not entire context
            for b in range(batch_size):
                if not active[b]:
                    logits[b] = -float('inf')
                    continue
                    
                recent_ids = context[b, max(0, context.size(1) - recent_window):].tolist()
                for token_id in set(recent_ids):  # Use set() to avoid duplicate penalties
                    if 0 <= token_id < logits.size(1):
                        logits[b, token_id] /= repetition_penalty
            
            # NUMERICAL STABILITY: Prevent attention logits from overflowing
            # Clip extreme values before softmax
            max_logit = logits.abs().max(dim=-1, keepdim=True)[0]
            if (max_logit > 50.0).any():
                logits = torch.clamp(logits, min=-50.0, max=50.0)

            # Top-k filtering
            if top_k is not None and top_k > 0:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)), dim=-1)
                min_v = v[:, -1].unsqueeze(1)
                logits = logits.masked_fill(logits < min_v, float("-inf"))

            # Top-p (nucleus) filtering
            if top_p is not None and top_p < 1.0:
                logits = top_p_filtering(logits, top_p=top_p)

            # Sample next tokens
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1).to(device)
            
            # Track generated IDs and check for EOS
            for b in range(batch_size):
                if active[b]:
                    token_id = next_token[b].item()
                    generated_ids[b].append(token_id)
                    # EARLY STOPPING: Stop on EOS token
                    if token_id == eos_token:
                        active[b] = False
            
            context = torch.cat([context, next_token], dim=1)

    model.train()
    
    # Decode all sequences
    if batch_size == 1:
        return tokenizer.decode(generated_ids[0])
    else:
        return [tokenizer.decode(ids) for ids in generated_ids]

def chat_with_void(model, user_input, tokenizer, device=args.device, max_new_tokens=200):
    prompt = f"### User:\n{user_input}\n### V.O.I.D.:\n"
    start_ids = tokenizer.encode(prompt)
    
    # Determine EOS token
    eos_token = 0 if tokenizer.offline_mode else (getattr(tokenizer.enc, 'eot_token', None) or tokenizer.enc.encode("<|endoftext|>", allowed_special={"<|endoftext|>"})[0])
    
    raw_output = sample(
        model, 
        start_bytes=start_ids, 
        length=max_new_tokens, 
        temp=0.6, 
        top_k=40, 
        top_p=0.9, 
        device=device,
        eos_token=eos_token,
        batch_size=1
    )
    response = raw_output
    stop_markers = ["### User:", "<|endoftext|>", "### V.O.I.D.:"]
    for marker in stop_markers:
        if marker in response:
            response = response.split(marker)[0]
    return response.strip()

def batch_generate(model, prompts, tokenizer, device=args.device, max_new_tokens=200):
    """Generate responses for multiple prompts in parallel."""
    batch_ids = []
    for prompt in prompts:
        ids = tokenizer.encode(f"### User:\n{prompt}\n### V.O.I.D.:\n")
        batch_ids.append(ids)
    
    eos_token = 0 if tokenizer.offline_mode else (getattr(tokenizer.enc, 'eot_token', None) or tokenizer.enc.encode("<|endoftext|>", allowed_special={"<|endoftext|>"})[0])
    
    outputs = sample(
        model,
        start_bytes=batch_ids,
        length=max_new_tokens,
        temp=0.6,
        top_k=40,
        top_p=0.9,
        device=device,
        eos_token=eos_token,
        batch_size=len(prompts)
    )
    
    # Clean up outputs
    cleaned = []
    for output in outputs:
        response = output
        stop_markers = ["### User:", "<|endoftext|>", "### V.O.I.D.:"]
        for marker in stop_markers:
            if marker in response:
                response = response.split(marker)[0]
        cleaned.append(response.strip())
    
    return cleaned

# -------------------------
# Main Generation Wrapper (External Import)
# -------------------------
_model = None
_tokenizer = None

def _load_model_once():
    global _model, _tokenizer
    if _model is not None: return
    # Basic loading logic (same as original script)
    # ... (simplified for brevity, main script execution doesn't depend on this)
    pass

def generate(prompt_text, max_len=200, temp=0.6, top_k=40, top_p=0.9):
    # This function is used when importing the script
    if model is None: return "Model not loaded."
    token_ids = tokenizer.encode(prompt_text)
    return sample(model, token_ids, length=max_len, temp=temp, top_k=top_k, top_p=top_p)

# -------------------------
# Training Loop
# -------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ("--generate", "-g", "--test"):
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Write a greeting"
        print(generate(prompt))
        sys.exit(0)
    
    # Handle model export
    if args.export_model:
        print(f"Exporting model to {args.export_model}")
        export_model(model, args.export_model)
        sys.exit(0)
    
    # Handle model import (already done above, but can be used standalone)
    if args.import_model and not os.path.exists(args.checkpoint):
        print(f"Loading model from {args.import_model} (no training)")
        sys.exit(0)

    print("\n" + "="*60)
    print("Starting V.O.I.D. Transformer Training")
    print("="*60 + "\n")

    model.train()
    step = start_step
    max_steps = args.max_steps
    accum_counter = 0
    running_loss = 0.0
    step_loss = 0.0
    start_time = time.time()
    
    # Mixed Precision setup
    use_amp = (args.use_amp and torch.cuda.is_available())
    use_bf16 = use_amp and getattr(torch.cuda, "is_bf16_supported", lambda: False)()
    autocast_dtype = torch.bfloat16 if use_bf16 else torch.float16
    scaler = torch.amp.GradScaler(enabled=(use_amp and not use_bf16))

    print(f"Training from step {step} to {max_steps}...")
    print(f"Gradient accumulation: {args.grad_accum} steps\n")

    while step < max_steps:
        for xb, yb in dloader:
            step += 1
            xb, yb = xb.to(args.device), yb.to(args.device)

            # Forward / Backward
            if use_amp:
                with torch.cuda.amp.autocast(enabled=True, dtype=autocast_dtype):
                    # Calculate sequence lengths (non-padding tokens)
                    seq_lengths = (yb != 0).sum(dim=1)
                    logits, _ = model(xb, use_kv_cache=False, seq_lengths=seq_lengths)
                    # Mask out padding tokens (token 0) from loss
                    padding_mask = yb != 0
                    loss_unreduced = F.cross_entropy(logits.view(-1, tokenizer.vocab_size), yb.view(-1), reduction='none')
                    loss = (loss_unreduced * padding_mask.view(-1)).sum() / padding_mask.sum().clamp(min=1e-8)
                    loss = loss / args.grad_accum
                scaler.scale(loss).backward()
            else:
                # Calculate sequence lengths (non-padding tokens)
                seq_lengths = (yb != 0).sum(dim=1)
                logits, _ = model(xb, use_kv_cache=False, seq_lengths=seq_lengths)
                # Mask out padding tokens (token 0) from loss
                padding_mask = yb != 0
                loss_unreduced = F.cross_entropy(logits.view(-1, tokenizer.vocab_size), yb.view(-1), reduction='none')
                loss = (loss_unreduced * padding_mask.view(-1)).sum() / padding_mask.sum().clamp(min=1e-8)
                loss = loss / args.grad_accum
                loss.backward()

            # Track per-step loss (unscaled)
            step_loss_value = float(loss.item()) * args.grad_accum
            step_loss = step_loss_value
            running_loss += step_loss_value
            accum_counter += 1
            
            # Per-step loss logging (before accumulation)
            if step % 5 == 0:
                lr = get_lr(step, max_steps, args.lr, args.min_lr, args.warmup_steps)
                print(f"[step {step:5d}] loss={step_loss:.4f} (accum {accum_counter}/{args.grad_accum}) lr={lr:.2e}")

            # Optimizer Step
            if accum_counter >= args.grad_accum:
                # GRADIENT NORM CLIPPING: Prevent exploding gradients
                if args.grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=args.grad_clip)
                
                if use_amp:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                optimizer.zero_grad()
                accum_counter = 0

            # Learning rate update (with warmup and minimum bound)
            lr = get_lr(step, max_steps, args.lr, args.min_lr, args.warmup_steps)
            for param_group in optimizer.param_groups:
                param_group["lr"] = lr

            # Aggregated logging (every 10 optimizer steps)
            if step % 10 == 0:
                elapsed = time.time() - start_time
                avg_loss = running_loss / 10.0
                print(f"[OPTIM STEP {step:5d}/{max_steps}] avg_loss={avg_loss:.4f} lr={lr:.2e} elapsed={int(elapsed)}s")
                running_loss = 0.0
                start_time = time.time()

            # Generation Test
            if step % args.generate_every == 0:
                print(f"\n--- 🗣️ V.O.I.D. CHAT TEST (Step {step}) ---")
                test_query = "What is your system?"
                try:
                    resp = chat_with_void(model, test_query, tokenizer, args.device)
                    print(f"V.O.I.D.: {resp}")
                except Exception as e:
                    print(f"Generation failed: {e}")
                print("-------------------------------------------\n")

            # Validation Loop (Fixed Indentation and Logic)
            if step % 200 == 0:
                model.eval()
                val_losses = []
                print("Running validation...")
                with torch.no_grad():
                    # Evaluate on 5 batches
                    for _ in range(5):
                        vx, vy = get_batch("val", batch_size=args.batch_size, seq_len=args.seq_len)
                        vx, vy = vx.to(args.device), vy.to(args.device)
                        seq_lengths = (vy != 0).sum(dim=1)
                        vlogits, _ = model(vx, use_kv_cache=False, seq_lengths=seq_lengths)
                        # Mask out padding from validation loss
                        padding_mask = vy != 0
                        vloss_unreduced = F.cross_entropy(vlogits.view(-1, tokenizer.vocab_size), vy.view(-1), reduction='none')
                        vloss = (vloss_unreduced * padding_mask.view(-1)).sum() / padding_mask.sum().clamp(min=1e-8)
                        val_losses.append(vloss.item())
                print(f"Validation Loss: {sum(val_losses)/len(val_losses):.4f}")
                model.train()

            # Save Checkpoint (Fixed Indentation)
            if args.save_every and (step % args.save_every == 0):
                # Calculate and save warmup_steps for checkpoint
                warmup_steps_actual = args.warmup_steps if args.warmup_steps else max(1, int(0.1 * args.max_steps))
                ckpt_data = {
                    "model": model.state_dict(),
                    "optim": optimizer.state_dict(),
                    "step": step,
                    "warmup_steps": warmup_steps_actual,  # PRESERVE WARMUP SCHEDULE
                    "args": vars(args)
                }
                torch.save(ckpt_data, args.checkpoint)
                print(f"✓ Saved checkpoint: {args.checkpoint}")
                
                # Also save model-only version for easy deployment
                model_only_path = args.checkpoint.replace(".pt", "_model.pt")
                torch.save(model.state_dict(), model_only_path)
                print(f"✓ Saved model-only: {model_only_path}")

            if step >= max_steps:
                break
        
        if step >= max_steps:
            break

    # Final Save
    print("Training finished. Saving final model.")
    warmup_steps_actual = args.warmup_steps if args.warmup_steps else max(1, int(0.1 * args.max_steps))
    ckpt_data = {
        "model": model.state_dict(),
        "optim": optimizer.state_dict(),
        "step": step,
        "warmup_steps": warmup_steps_actual,  # PRESERVE WARMUP SCHEDULE
        "args": vars(args)
    }
    torch.save(ckpt_data, args.checkpoint)
    
    # Save model-only version
    model_only_path = args.checkpoint.replace(".pt", "_model.pt")
    torch.save(model.state_dict(), model_only_path)
    print(f"✓ Saved model-only: {model_only_path}")
    print(f"✓ Full checkpoint: {args.checkpoint}")