import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import torch
from core.tokenizer import TiktokenTokenizer


def test_o200k_tokenizer():
    tokenizer = TiktokenTokenizer("o200k_base")

    # 1. Total vocab size
    print(f"Vocab size: {tokenizer.vocab_size}")
    assert tokenizer.vocab_size == 200025, f"Unexpected vocab size: {tokenizer.vocab_size}"
    assert tokenizer.pad_token_id == 200021, f"Unexpected pad token ID: {tokenizer.pad_token_id}"

    # 2. Custom role tokens round-trip
    text = (
        "<|im_start|>system\nYou are V.O.I.D.<|im_end|>\n"
        "<|im_start|>user\nHello V.O.I.D. assistant!<|im_end|>\n"
        "<|im_start|>assistant\nGreetings! Ready to assist.<|im_end|>"
    )
    tokens = tokenizer.encode(text, allowed_special="all")
    assert len(tokens) > 0
    decoded = tokenizer.decode(tokens)
    assert decoded == text, f"Decoded text mismatch:\nExpected: {text}\nGot: {decoded}"

    # 3. Batch encode & tensor output
    batch_texts = [
        "Short prompt.",
        "A longer prompt containing <|im_start|>user\nquery<|im_end|> with special tokens.",
    ]
    batch = tokenizer.batch_encode(batch_texts, max_length=32, pad_to_max=True)

    assert "input_ids" in batch and "attention_mask" in batch
    assert isinstance(batch["input_ids"], torch.Tensor)
    assert isinstance(batch["attention_mask"], torch.Tensor)
    assert batch["input_ids"].shape == (2, 32)
    assert batch["attention_mask"].shape == (2, 32)

    # Verify pad token placement and attention mask
    for i in range(2):
        pad_positions = (batch["input_ids"][i] == tokenizer.pad_token_id).nonzero(as_tuple=True)[0]
        for pos in pad_positions:
            assert batch["attention_mask"][i][pos].item() == 0, "Mask should be 0 at pad positions"

    print("✅ All unit tests passed successfully!")


if __name__ == "__main__":
    test_o200k_tokenizer()
