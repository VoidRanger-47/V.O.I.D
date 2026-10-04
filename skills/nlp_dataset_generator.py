# skills/nlp_dataset_generator.py
import os
import json

class NLP_Dataset_Generator:
    """
    Tiny helper to add custom examples into nlp_dataset/custom.jsonl
    """

    def __init__(self, path="nlp_dataset/custom.jsonl"):
        self.path = path
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        open(self.path, "a").close()

    def add_example(self, instruction: str, input_text: str, output_text: str) -> str:
        example = {
            "instruction": instruction,
            "input": input_text,
            "output": output_text
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
        return f"Appended example to {self.path}"
