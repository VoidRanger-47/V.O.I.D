import tiktoken
import torch
from typing import List, Dict, Union, Optional


class TiktokenTokenizer:
    """
    OpenAI o200k_base tokenizer using pure tiktoken, strictly without
    any Hugging Face dependencies.
    """

    def __init__(self, model_name: str = "o200k_base"):
        self.model_name = model_name
        base_encoding = tiktoken.get_encoding(model_name)

        # Define custom role & special tokens starting right after base n_vocab to prevent collisions
        self.custom_special_tokens = {
            "<|im_start|>": base_encoding.n_vocab,
            "<|im_end|>": base_encoding.n_vocab + 1,
            "<|pad|>": base_encoding.n_vocab + 2,
            "<|system|>": base_encoding.n_vocab + 3,
            "<|user|>": base_encoding.n_vocab + 4,
            "<|assistant|>": base_encoding.n_vocab + 5,
        }

        # Combine base special tokens with custom tokens
        all_special_tokens = {
            **base_encoding._special_tokens,
            **self.custom_special_tokens,
        }

        # Construct custom tiktoken Encoding instance
        self.encoding = tiktoken.Encoding(
            name=f"{model_name}_custom",
            pat_str=base_encoding._pat_str,
            mergeable_ranks=base_encoding._mergeable_ranks,
            special_tokens=all_special_tokens,
        )

        # Total vocabulary size: base n_vocab + len(custom_special_tokens)
        self.vocab_size = self.encoding.n_vocab
        self.pad_token_id = self.custom_special_tokens["<|pad|>"]
        self.eos_token_id = self.encoding.encode("<|endoftext|>", allowed_special="all")[0]
        self.im_start_id = self.custom_special_tokens["<|im_start|>"]
        self.im_end_id = self.custom_special_tokens["<|im_end|>"]

        # Backwards compatibility alias
        self.enc = self.encoding
        self.offline_mode = False

    def encode(self, text: str, allowed_special: Union[str, set] = "all") -> List[int]:
        """
        Encode text to token IDs.
        """
        if allowed_special == "all":
            return self.encoding.encode(text, allowed_special="all")
        elif isinstance(allowed_special, (set, list, tuple)):
            return self.encoding.encode(text, allowed_special=set(allowed_special))
        return self.encoding.encode(text)

    def decode(self, tokens: List[int]) -> str:
        """
        Decode token IDs back to a string.
        """
        return self.encoding.decode(tokens)

    def batch_encode(
        self,
        texts: List[str],
        max_length: Optional[int] = None,
        pad_to_max: bool = True,
    ) -> Dict[str, torch.Tensor]:
        """
        Batch encode multiple texts into PyTorch input_ids and attention_mask tensors.
        """
        batch_ids = [self.encode(text, allowed_special="all") for text in texts]

        if max_length is not None:
            batch_ids = [ids[:max_length] for ids in batch_ids]

        longest = max((len(ids) for ids in batch_ids), default=0)
        target_len = max_length if (pad_to_max and max_length is not None) else longest

        input_ids = []
        attention_mask = []

        for ids in batch_ids:
            cur_len = len(ids)
            pad_len = max(0, target_len - cur_len)
            padded = ids + [self.pad_token_id] * pad_len
            mask = [1] * cur_len + [0] * pad_len
            input_ids.append(padded[:target_len])
            attention_mask.append(mask[:target_len])

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        }


# Default singleton instance
tokenizer = TiktokenTokenizer()
