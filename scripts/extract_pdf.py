from pdf_utils import pdf_to_text, save_text
from pathlib import Path
import argparse


def process_pdf(pdf_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (pdf_path.stem + ".txt")
    try:
        print(f"Processing: {pdf_path}")
        text = pdf_to_text(str(pdf_path))
        save_text(text, str(out_path))
        print(f"Saved text to {out_path}\n")
    except Exception as e:
        print(f"Failed to process {pdf_path}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Extract text from PDFs in data/raw_pdf/")
    parser.add_argument("--file", "-f", type=str, default=None, help="Specific PDF file to process (path relative to project or absolute)")
    parser.add_argument("--all", "-a", action="store_true", help="Process all PDFs in data/raw_pdf/")
    args = parser.parse_args()

    raw_dir = Path("data/raw_pdf")
    out_dir = Path("data/processed")

    if args.file:
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            # allow shorthand: look in raw_dir
            candidate = raw_dir / args.file
            if candidate.exists():
                pdf_path = candidate
            else:
                print(f"PDF not found: {args.file}")
                return
        process_pdf(pdf_path, out_dir)
        return

    # If --all provided or no file, process all PDFs found
    pdfs = sorted(raw_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {raw_dir}. Place files there or pass --file <path>.")
        return

    for p in pdfs:
        process_pdf(p, out_dir)


if __name__ == "__main__":
    main()
