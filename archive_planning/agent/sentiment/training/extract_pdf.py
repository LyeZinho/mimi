"""
Extract text from PDF files for sentiment training corpus.

Usage:
    python -m agent.sentiment.training.extract_pdf \
        --input-dir ./data/sentiment_dataset \
        --output-dir ./data/corpus \
        --min-chars 50
"""

import argparse
import logging
import re
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from PDF file."""
    try:
        import pdfplumber
        
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        return "\n".join(text_parts)
        
    except ImportError:
        # Fallback to PyPDF2
        try:
            from PyPDF2 import PdfReader
            
            text_parts = []
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n".join(text_parts)
            
        except ImportError:
            logger.error("Neither pdfplumber nor PyPDF2 installed")
            raise ImportError("Install pdfplumber or PyPDF2: pip install pdfplumber")


def clean_pdf_text(text: str) -> str:
    """Clean extracted PDF text for NLP training."""
    # Remove page numbers (standalone numbers)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    
    # Remove headers/footers (repeated text patterns)
    text = re.sub(r'\n-{3,}\n', '\n', text)
    
    # Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove PDF artifacts
    text = re.sub(r'[^\w\s.,!?;:\'"()-]', ' ', text)
    
    return text.strip()


def split_into_sentences(text: str, min_length: int = 20) -> List[str]:
    """Split text into sentences for training."""
    # Portuguese sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter short/empty sentences
    return [s.strip() for s in sentences if len(s.strip()) >= min_length]


def process_pdf_directory(
    input_dir: str,
    output_dir: str,
    min_chars: int = 50,
) -> int:
    """Process all PDFs in directory and save extracted text."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    total_sentences = 0
    pdf_files = list(input_path.glob("*.pdf"))
    
    logger.info(f"Found {len(pdf_files)} PDF files in {input_dir}")
    
    for pdf_file in pdf_files:
        try:
            logger.info(f"Processing: {pdf_file.name}")
            
            # Extract text
            raw_text = extract_text_from_pdf(str(pdf_file))
            
            if len(raw_text) < min_chars:
                logger.warning(f"  Skipping (too short: {len(raw_text)} chars)")
                continue
            
            # Clean
            cleaned = clean_pdf_text(raw_text)
            
            # Split into sentences
            sentences = split_into_sentences(cleaned)
            
            if not sentences:
                logger.warning(f"  No sentences extracted")
                continue
            
            # Save to corpus file
            output_file = output_path / f"{pdf_file.stem}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(sentences))
            
            total_sentences += len(sentences)
            logger.info(f"  Extracted {len(sentences)} sentences ({len(cleaned)} chars)")
            
        except Exception as e:
            logger.error(f"  Error processing {pdf_file.name}: {e}")
    
    logger.info(f"Total: {total_sentences} sentences from {len(pdf_files)} PDFs")
    return total_sentences


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract text from PDFs for sentiment training"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="./data/sentiment_dataset",
        help="Directory containing PDF files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./data/corpus",
        help="Directory to save extracted text",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=50,
        help="Minimum characters to process a PDF",
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    
    process_pdf_directory(args.input_dir, args.output_dir, args.min_chars)


if __name__ == "__main__":
    main()
