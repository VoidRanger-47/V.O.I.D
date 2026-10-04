# providers/local_transformer.py
from typing import Generator, Dict, Any
from providers.base import BaseLLMProvider

class LocalTransformerProvider(BaseLLMProvider):
    """
    Local PyTorch GPT Transformer provider for V.O.I.D.
    Runs entirely on local GPU/CPU with no internet connection required.
    """
    def __init__(self):
        try:
            from from_scratch_transformer import model, tokenizer, args, device
            self.model = model
            self.tokenizer = tokenizer
            self.args = args
            self.device = device
            self.is_ready = True
        except Exception as e:
            print(f"⚠️  LocalTransformerProvider initialization error: {e}")
            self.is_ready = False

    def generate(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.7, **kwargs) -> str:
        if not self.is_ready:
            return "[Local Engine Error: PyTorch model unavailable]"

        import torch
        input_ids = self.tokenizer.encode(prompt)
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.device)

        if input_tensor.size(1) > self.args.seq_len:
            input_tensor = input_tensor[:, -self.args.seq_len:]

        self.model.eval()
        with torch.no_grad():
            generated = input_tensor
            for _ in range(max_new_tokens):
                if generated.size(1) > self.args.seq_len:
                    gen_cond = generated[:, -self.args.seq_len:]
                else:
                    gen_cond = generated

                output = self.model(gen_cond, use_kv_cache=False)
                logits = output[0] if isinstance(output, tuple) else output
                logits = logits[:, -1, :] / max(temperature, 1e-5)
                probs = torch.softmax(logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                generated = torch.cat((generated, next_token), dim=1)

        output_text = self.tokenizer.decode(generated[0].cpu().tolist())
        try:
            return output_text.split("### V.O.I.D.:")[-1].strip()
        except Exception:
            return output_text.strip()

    def generate_stream(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.7, **kwargs) -> Generator[str, None, None]:
        from chat import generate_stream_tokens
        yield from generate_stream_tokens(
            prompt=prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=kwargs.get("top_k", 40),
            top_p=kwargs.get("top_p", 0.9)
        )

    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": "LocalTransformer",
            "type": "Local PyTorch Neural Engine",
            "offline": True,
            "device": str(self.device) if hasattr(self, "device") else "unknown",
            "seq_len": self.args.seq_len if hasattr(self, "args") else 512
        }
