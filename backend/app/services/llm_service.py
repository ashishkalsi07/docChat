"""
LLM service for generating responses using Azure OpenAI.
Handles RAG prompting and response generation.
"""
import re
from typing import List, Dict, Optional
from openai import AzureOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Azure OpenAI client using environment variables
client = AzureOpenAI(
    api_key=settings.AZURE_OPENAI_API_KEY,
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    api_version=settings.AZURE_OPENAI_API_VERSION,
)

async def call_llm(prompt: str) -> str:
    """Call Azure OpenAI API with the given prompt."""
    try:
        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a document-grounded assistant. Answer only from the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"❌ Azure OpenAI call failed: {e}")
        raise e

async def generate_response(query: str, context_chunks: List[Dict]) -> Dict:
    """Generate response using RAG approach."""
    if not context_chunks:
        return {
            "response": "I couldn't find specific information about that in your document. This might be because: 1) The content wasn't properly extracted from the PDF, 2) The question needs different keywords, or 3) The information isn't in the uploaded document. Try rephrasing your question or re-uploading the document.",
            "citations": [],
            "has_context": False
        }

    context_text = "\n\n".join(
        f"Chunk {i+1}:\n{chunk['content']}"
        for i, chunk in enumerate(context_chunks)
    )

    prompt = f"""
You are a document-based assistant.

Rules:
- You can Reply Casuall Greetings.
- You Must Not Return any citations for greetings.
- Answer ONLY using the provided context
- If the answer is not explicitly stated, say: "Not found in the document"
- Answer in clear, natural, complete sentences
- Be concise and factual

Context:
{context_text}

Question:
{query}
"""

    # Call LLM
    llm_answer = await call_llm(prompt)

    citations = [
        {
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk.get("page_number"),
            "similarity": chunk.get("similarity", 0)
        }
        for chunk in context_chunks
    ]

    return {
        "response": llm_answer,
        "citations": citations,
        "has_context": True
    }

async def format_rag_prompt(query: str, context_chunks: List[Dict]) -> str:
    """Format RAG prompt for LLM."""
    if not context_chunks:
        return f"Question: {query}\nAnswer: No Data Available in Document"

    context_text = "\n\n".join([
        f"Source {i+1} (Page {chunk.get('page_number', 'N/A')}):\n{chunk['content']}"
        for i, chunk in enumerate(context_chunks)
    ])

    prompt = f"""You are a helpful assistant that answers questions based on provided document context.

Context from document:
{context_text}

Question: {query}

Instructions:
1. Answer the question using ONLY the information provided in the context above
2. If the answer is not in the context, respond with "Not found in the document"
3. Include specific references to sources when possible
4. Be concise but informative
5. In case of greetings do not include references to sources

Answer:"""

    return prompt

def extract_citations_from_content(response: str, context_chunks: List[Dict]) -> List[Dict]:
    """Extract citation information from context chunks."""
    citations = []

    for i, chunk in enumerate(context_chunks):
        citations.append({
            "id": chunk["chunk_id"],
            "content": chunk["content"][:200] + "...",
            "page_number": chunk.get("page_number"),
            "chunk_index": chunk.get("chunk_index"),
            "similarity": chunk.get("similarity", 0),
            "source_number": i + 1
        })

    return citations