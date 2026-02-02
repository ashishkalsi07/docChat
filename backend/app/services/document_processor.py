"""
Document processing service for handling PDF files.
Extracts text, creates chunks, and prepares documents for embedding.
"""
import os
import uuid
import logging
from typing import List, Dict, Optional, Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread pool for CPU-intensive operations
executor = ThreadPoolExecutor(max_workers=2)

async def extract_pdf_text(file_path: str) -> Dict:
    """Extract text from PDF file."""
    print(f"📄 PDF_EXTRACT: Starting PDF text extraction from {file_path}")
    try:
        # Check if file exists and is readable
        import os
        if not os.path.exists(file_path):
            raise Exception(f"PDF file not found: {file_path}")

        file_size = os.path.getsize(file_path)
        print(f"📄 PDF_EXTRACT: File exists, size: {file_size} bytes")

        # Run in thread pool to avoid blocking
        print(f"📄 PDF_EXTRACT: Starting sync extraction in thread pool...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, _extract_pdf_sync, file_path)

        print(f"📄 PDF_EXTRACT: Extraction completed, success: {result.get('success', False)}")
        if result.get('success'):
            print(f"📄 PDF_EXTRACT: Extracted {len(result.get('pages', []))} pages")
        else:
            print(f"📄 PDF_EXTRACT: Extraction failed: {result.get('error', 'Unknown error')}")

        return result
    except Exception as e:
        logger.error(f"❌ PDF extraction failed: {e}")
        print(f"❌ PDF_EXTRACT: Exception occurred: {e}")
        return {"success": False, "error": str(e), "pages": []}

def _extract_pdf_sync(file_path: str) -> Dict:
    """Synchronous PDF extraction using PyPDF2."""
    print(f"📖 PDF_SYNC: Starting synchronous PDF extraction")
    try:
        print(f"📖 PDF_SYNC: Importing PyPDF2...")
        import PyPDF2
        print(f"✅ PDF_SYNC: PyPDF2 imported successfully")

        print(f"📖 PDF_SYNC: Opening PDF file: {file_path}")
        pages = []
        with open(file_path, 'rb') as file:
            print(f"📖 PDF_SYNC: Creating PdfReader...")
            pdf_reader = PyPDF2.PdfReader(file)

            total_pages = len(pdf_reader.pages)
            print(f"📖 PDF_SYNC: PDF has {total_pages} pages")

            for page_num, page in enumerate(pdf_reader.pages, 1):
                print(f"📖 PDF_SYNC: Processing page {page_num}/{total_pages}")
                try:
                    text = page.extract_text()
                    text_length = len(text.strip())
                    print(f"📖 PDF_SYNC: Page {page_num} extracted {text_length} characters")

                    if text.strip():  # Only add non-empty pages
                        pages.append({
                            "page_number": page_num,
                            "text": text.strip()
                        })
                        print(f"✅ PDF_SYNC: Page {page_num} added to results")
                    else:
                        print(f"⚠️ PDF_SYNC: Page {page_num} is empty, skipping")
                except Exception as e:
                    print(f"❌ PDF_SYNC: Failed to extract page {page_num}: {e}")
                    logger.warning(f"⚠️ Failed to extract page {page_num}: {e}")
                    continue

        print(f"✅ PDF_SYNC: Successfully extracted {len(pages)} non-empty pages from PDF")
        logger.info(f"✅ Extracted {len(pages)} pages from PDF")

        return {
            "success": True,
            "pages": pages,
            "total_pages": len(pages)
        }

    except ImportError:
        error_msg = "PyPDF2 not installed. Install with: pip install PyPDF2"
        print(f"❌ PDF_SYNC: {error_msg}")
        logger.error(f"❌ {error_msg}")
        return {"success": False, "error": "PyPDF2 not installed", "pages": []}
    except Exception as e:
        print(f"❌ PDF_SYNC: PDF extraction error: {e}")
        logger.error(f"❌ PDF extraction error: {e}")
        return {"success": False, "error": str(e), "pages": []}

def chunk_text(
    pages: List[Dict],
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[Dict]:
    """Create overlapping chunks from extracted text."""
    print(f"✂️ CHUNKING: Starting text chunking process")

    if chunk_size is None:
        chunk_size = settings.chunk_size
    if chunk_overlap is None:
        chunk_overlap = settings.chunk_overlap

    print(f"✂️ CHUNKING: Settings - chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}")
    print(f"✂️ CHUNKING: Input - {len(pages)} pages to process")

    chunks = []
    chunk_index = 0

    for page_idx, page in enumerate(pages):
        page_text = page["text"]
        page_number = page["page_number"]

        print(f"✂️ CHUNKING: Processing page {page_idx + 1}/{len(pages)} (page number {page_number})")
        print(f"✂️ CHUNKING: Page text length: {len(page_text)} characters")

        # Split text into sentences for better chunking
        print(f"✂️ CHUNKING: Splitting page {page_number} into sentences...")
        sentences = _split_into_sentences(page_text)
        print(f"✂️ CHUNKING: Page {page_number} split into {len(sentences)} sentences")

        current_chunk = ""
        current_sentences = []

        for sentence_idx, sentence in enumerate(sentences):
            sentence_len = len(sentence)
            proposed_chunk_len = len(current_chunk + " " + sentence)

            print(f"✂️ CHUNKING: Sentence {sentence_idx + 1}/{len(sentences)} - length: {sentence_len}, proposed total: {proposed_chunk_len}")

            # Check if adding this sentence would exceed chunk size
            if proposed_chunk_len <= chunk_size:
                current_chunk += (" " + sentence) if current_chunk else sentence
                current_sentences.append(sentence)
                print(f"✂️ CHUNKING: Added sentence to current chunk (new length: {len(current_chunk)})")
            else:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunk_id = f"chunk_{chunk_index}_{uuid.uuid4().hex[:8]}"
                    chunk_data = {
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_index,
                        "content": current_chunk.strip(),
                        "page_number": page_number,
                        "sentence_count": len(current_sentences)
                    }
                    chunks.append(chunk_data)
                    print(f"✅ CHUNKING: Saved chunk {chunk_index} - {len(current_chunk)} chars, {len(current_sentences)} sentences")
                    chunk_index += 1

                # Start new chunk with overlap
                if chunk_overlap > 0 and current_sentences:
                    overlap_count = max(1, chunk_overlap // 100)
                    overlap_sentences = current_sentences[-overlap_count:] if len(current_sentences) > overlap_count else current_sentences
                    current_chunk = " ".join(overlap_sentences)
                    current_sentences = overlap_sentences.copy()
                    print(f"✂️ CHUNKING: Started new chunk with {len(overlap_sentences)} overlap sentences")
                else:
                    current_chunk = ""
                    current_sentences = []
                    print(f"✂️ CHUNKING: Started new chunk with no overlap")

                # Add the sentence that didn't fit
                current_chunk += (" " + sentence) if current_chunk else sentence
                current_sentences.append(sentence)
                print(f"✂️ CHUNKING: Added overflow sentence to new chunk")

        # Don't forget the last chunk
        if current_chunk.strip():
            chunk_id = f"chunk_{chunk_index}_{uuid.uuid4().hex[:8]}"
            chunk_data = {
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "content": current_chunk.strip(),
                "page_number": page_number,
                "sentence_count": len(current_sentences)
            }
            chunks.append(chunk_data)
            print(f"✅ CHUNKING: Saved final chunk {chunk_index} - {len(current_chunk)} chars")
            chunk_index += 1

        print(f"✅ CHUNKING: Completed page {page_number} - created {chunk_index} chunks so far")

    print(f"🎉 CHUNKING: Completed! Created {len(chunks)} total chunks from {len(pages)} pages")
    logger.info(f"✅ Created {len(chunks)} chunks from {len(pages)} pages")

    # Show chunk statistics
    if chunks:
        avg_length = sum(len(chunk["content"]) for chunk in chunks) / len(chunks)
        min_length = min(len(chunk["content"]) for chunk in chunks)
        max_length = max(len(chunk["content"]) for chunk in chunks)
        print(f"📊 CHUNKING: Statistics - avg: {avg_length:.0f} chars, min: {min_length}, max: {max_length}")

    return chunks

def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using simple rules."""
    import re

    # Simple sentence splitting on periods, exclamation marks, question marks
    sentences = re.split(r'[.!?]+', text)

    # Clean and filter sentences
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        # Only keep sentences with reasonable length
        if sentence and len(sentence) > 10:
            cleaned_sentences.append(sentence)

    return cleaned_sentences

async def process_document_file(
    file_path: str,
    document_id: str,
    filename: str
) -> Dict:
    """Complete document processing pipeline."""
    print(f"🔄 DOC_PROCESS: Starting complete document processing pipeline")
    print(f"🔄 DOC_PROCESS: File path: {file_path}")
    print(f"🔄 DOC_PROCESS: Document ID: {document_id}")
    print(f"🔄 DOC_PROCESS: Filename: {filename}")

    try:
        logger.info(f"🔄 Processing document: {filename}")

        # Extract text from PDF
        print(f"📄 DOC_PROCESS: Step 1 - Extracting text from PDF...")
        extraction_result = await extract_pdf_text(file_path)

        if not extraction_result["success"]:
            error_msg = extraction_result["error"]
            print(f"❌ DOC_PROCESS: Text extraction failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "chunks": []
            }

        pages = extraction_result["pages"]
        print(f"✅ DOC_PROCESS: Text extraction successful - {len(pages)} pages extracted")

        if not pages:
            error_msg = "No text content found in PDF"
            print(f"❌ DOC_PROCESS: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "chunks": []
            }

        # Show page statistics
        total_chars = sum(len(page["text"]) for page in pages)
        print(f"📊 DOC_PROCESS: Total characters extracted: {total_chars}")

        # Create chunks
        print(f"✂️ DOC_PROCESS: Step 2 - Creating chunks from {len(pages)} pages...")
        chunks = chunk_text(pages)

        if not chunks:
            error_msg = "Failed to create chunks from document"
            print(f"❌ DOC_PROCESS: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "chunks": []
            }

        print(f"✅ DOC_PROCESS: Chunking successful - {len(chunks)} chunks created")

        # Add document metadata to chunks
        print(f"📝 DOC_PROCESS: Adding metadata to chunks...")
        for i, chunk in enumerate(chunks):
            chunk["document_id"] = document_id
            chunk["filename"] = filename
            if i < 3:  # Show first 3 chunks
                print(f"📝 DOC_PROCESS: Chunk {i+1} - ID: {chunk['chunk_id']}, length: {len(chunk['content'])}")

        logger.info(f"✅ Document processing complete: {len(chunks)} chunks created")

        result = {
            "success": True,
            "chunks": chunks,
            "total_pages": len(pages),
            "total_chunks": len(chunks)
        }

        print(f"🎉 DOC_PROCESS: Document processing pipeline completed successfully!")
        print(f"📊 DOC_PROCESS: Summary - Pages: {len(pages)}, Chunks: {len(chunks)}, Total chars: {total_chars}")

        return result

    except Exception as e:
        print(f"❌ DOC_PROCESS: Critical error in document processing: {e}")
        logger.error(f"❌ Document processing failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "chunks": []
        }

def validate_pdf_file(file_path: str) -> Dict:
    """Validate PDF file before processing."""
    try:
        if not os.path.exists(file_path):
            return {"valid": False, "error": "File does not exist"}

        file_size = os.path.getsize(file_path)
        if file_size > settings.max_file_size:
            return {
                "valid": False,
                "error": f"File too large: {file_size} bytes > {settings.max_file_size} bytes"
            }

        if file_size == 0:
            return {"valid": False, "error": "File is empty"}

        # Check file extension
        if not file_path.lower().endswith('.pdf'):
            return {"valid": False, "error": "File must be a PDF"}

        # Try to open with PyPDF2 to validate
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                if len(pdf_reader.pages) == 0:
                    return {"valid": False, "error": "PDF has no pages"}
        except ImportError:
            logger.warning("⚠️ PyPDF2 not available for validation")
        except Exception as e:
            return {"valid": False, "error": f"Invalid PDF file: {e}"}

        return {"valid": True}

    except Exception as e:
        return {"valid": False, "error": f"Validation error: {e}"}

# Metadata extraction functions
def extract_pdf_metadata(file_path: str) -> Dict:
    """Extract metadata from PDF file."""
    try:
        import PyPDF2

        metadata = {}
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            # Basic info
            metadata["page_count"] = len(pdf_reader.pages)

            # Document info
            if pdf_reader.metadata:
                doc_info = pdf_reader.metadata
                metadata.update({
                    "title": doc_info.get("/Title", ""),
                    "author": doc_info.get("/Author", ""),
                    "subject": doc_info.get("/Subject", ""),
                    "creator": doc_info.get("/Creator", ""),
                    "producer": doc_info.get("/Producer", ""),
                    "creation_date": str(doc_info.get("/CreationDate", "")),
                    "modification_date": str(doc_info.get("/ModDate", ""))
                })

        return metadata

    except Exception as e:
        logger.warning(f"⚠️ Could not extract PDF metadata: {e}")
        return {"page_count": 0}