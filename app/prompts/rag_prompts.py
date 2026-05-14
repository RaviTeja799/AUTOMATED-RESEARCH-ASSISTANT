"""
RAG-specific prompt templates with citation-awareness and hallucination prevention.
"""
from typing import List, Dict, Any, Optional


class RAGPrompts:
    """Citation-aware RAG prompts with hallucination prevention."""
    
    SYSTEM_PROMPT = """You are a research assistant AI that helps users understand academic papers.

CRITICAL RULES FOR PREVENTING HALLUCINATIONS:
1. ONLY use information explicitly stated in the provided context
2. ALWAYS cite sources using [Paper Title, Authors] format after each claim
3. If information is NOT in the context, say: "I don't have information about this in the provided papers"
4. NEVER make assumptions or use external knowledge
5. NEVER infer information not explicitly stated
6. If papers contradict each other, mention both perspectives with citations
7. If you're uncertain, express that uncertainty explicitly

CITATION FORMAT:
- After each factual claim, add: [Paper Title, Authors, Year]
- Example: "Transformers use self-attention mechanisms [Attention Is All You Need, Vaswani et al., 2017]."

Your goal is to provide accurate, well-cited answers based SOLELY on the research papers provided."""
    
    @staticmethod
    def build_rag_prompt(
        question: str,
        context_chunks: List[Dict[str, Any]],
        include_confidence: bool = False
    ) -> str:
        """
        Build citation-aware RAG prompt.
        
        Args:
            question: User question
            context_chunks: Retrieved chunks with metadata
            include_confidence: Include confidence assessment
            
        Returns:
            Formatted prompt
        """
        # Build context with proper citations
        context_parts = []
        
        for i, chunk in enumerate(context_chunks, 1):
            paper_meta = chunk.get('paper_metadata', {})
            title = paper_meta.get('title', 'Unknown Paper')
            authors = paper_meta.get('authors', [])
            year = paper_meta.get('publication_year', 'N/A')
            section = chunk.get('section', 'unknown')
            page = chunk.get('page_number')
            text = chunk.get('text', '')
            score = chunk.get('score', 0.0)
            
            # Format authors
            if authors:
                if len(authors) > 3:
                    author_str = f"{authors[0]} et al."
                elif len(authors) > 1:
                    author_str = ", ".join(authors[:-1]) + f" and {authors[-1]}"
                else:
                    author_str = authors[0]
            else:
                author_str = "Unknown Authors"
            
            # Build citation reference
            citation = f"[{title}, {author_str}, {year}]"
            
            # Build context entry
            context_entry = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE {i}: {citation}
Section: {section.upper()}"""
            
            if page:
                context_entry += f" | Page: {page}"
            
            context_entry += f" | Relevance: {score:.2f}"
            context_entry += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{text}\n"
            
            context_parts.append(context_entry)
        
        context = "\n".join(context_parts)
        
        # Base prompt
        prompt = f"""Answer the following question based ONLY on the provided research paper excerpts.

═══════════════════════════════════════════════════════════════════════════
INSTRUCTIONS FOR CITATION-AWARE ANSWERING:
═══════════════════════════════════════════════════════════════════════════

1. USE ONLY THE SOURCES BELOW
   - Do not use any external knowledge
   - Do not make assumptions beyond what is stated
   
2. CITE EVERY CLAIM
   - After each factual statement, add the citation: [Paper Title, Authors, Year]
   - Example: "The model achieved 95% accuracy [Paper X, Smith et al., 2023]."
   
3. HANDLE MISSING INFORMATION
   - If the answer is not in the sources, say: "I don't have information about this in the provided papers."
   - Do not try to answer from general knowledge
   
4. HANDLE CONTRADICTIONS
   - If sources disagree, present both views with citations
   - Example: "Paper A found X [Citation A], while Paper B found Y [Citation B]."
   
5. EXPRESS UNCERTAINTY
   - If information is partial or unclear, say so explicitly
   - Use phrases like "Based on the limited information provided..." or "The sources suggest..."

═══════════════════════════════════════════════════════════════════════════
RESEARCH PAPER SOURCES:
═══════════════════════════════════════════════════════════════════════════

{context}

═══════════════════════════════════════════════════════════════════════════
QUESTION:
═══════════════════════════════════════════════════════════════════════════

{question}

═══════════════════════════════════════════════════════════════════════════
YOUR ANSWER (with citations after each claim):
═══════════════════════════════════════════════════════════════════════════
"""
        
        # Add confidence assessment if requested
        if include_confidence:
            prompt += """

After your answer, provide:

CONFIDENCE ASSESSMENT:
- Confidence Level: [High/Medium/Low]
- Reasoning: [Why this confidence level?]
- Information Gaps: [What information is missing or unclear?]
- Caveats: [Any important limitations or caveats?]
"""
        
        return prompt
    
    @staticmethod
    def build_verification_prompt(
        answer: str,
        context_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for verifying answer against sources.
        
        Args:
            answer: Generated answer to verify
            context_chunks: Source chunks
            
        Returns:
            Verification prompt
        """
        context = RAGPrompts._format_context_simple(context_chunks)
        
        prompt = f"""Verify the following answer against the provided sources.

ANSWER TO VERIFY:
{answer}

SOURCES:
{context}

VERIFICATION CHECKLIST:
1. Is every claim in the answer supported by the sources?
2. Are all citations accurate and present?
3. Is any information added that's not in the sources?
4. Are there any contradictions with the sources?
5. Is the answer complete based on available information?

For each claim in the answer, indicate:
✓ SUPPORTED - Claim is directly supported by sources
⚠ PARTIALLY SUPPORTED - Claim is partially supported
✗ NOT SUPPORTED - Claim is not found in sources
? UNCLEAR - Cannot determine from sources

VERIFICATION RESULT:
"""
        
        return prompt
    
    @staticmethod
    def build_multi_hop_prompt(
        question: str,
        context_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for multi-hop reasoning questions.
        
        Args:
            question: Complex question requiring multi-hop reasoning
            context_chunks: Retrieved chunks
            
        Returns:
            Multi-hop reasoning prompt
        """
        context = RAGPrompts._format_context_detailed(context_chunks)
        
        prompt = f"""Answer the following question that may require combining information from multiple sources.

QUESTION: {question}

SOURCES:
{context}

INSTRUCTIONS FOR MULTI-HOP REASONING:
1. Identify what information is needed to answer the question
2. Find relevant information across the sources
3. Combine information logically
4. Cite each piece of information used
5. Show your reasoning step-by-step

ANSWER FORMAT:
Step 1: [First piece of information needed] [Citation]
Step 2: [Second piece of information] [Citation]
...
Conclusion: [Final answer combining all information]

YOUR ANSWER:
"""
        
        return prompt
    
    @staticmethod
    def build_comparative_prompt(
        question: str,
        context_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for comparative questions.
        
        Args:
            question: Comparative question
            context_chunks: Retrieved chunks
            
        Returns:
            Comparative prompt
        """
        context = RAGPrompts._format_context_detailed(context_chunks)
        
        prompt = f"""Answer the following comparative question based on the provided sources.

QUESTION: {question}

SOURCES:
{context}

INSTRUCTIONS FOR COMPARISON:
1. Identify what is being compared
2. Extract relevant information for each item from sources
3. Present similarities and differences clearly
4. Cite sources for each point
5. Be balanced and objective

ANSWER FORMAT:
Similarities:
- [Point 1] [Citations]
- [Point 2] [Citations]

Differences:
- [Point 1] [Citations]
- [Point 2] [Citations]

Summary: [Brief summary of comparison]

YOUR ANSWER:
"""
        
        return prompt
    
    @staticmethod
    def _format_context_simple(chunks: List[Dict[str, Any]]) -> str:
        """Format context in simple format."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            title = chunk.get('paper_metadata', {}).get('title', 'Unknown')
            text = chunk.get('text', '')
            parts.append(f"[Source {i}] {title}:\n{text}")
        return "\n\n".join(parts)
    
    @staticmethod
    def _format_context_detailed(chunks: List[Dict[str, Any]]) -> str:
        """Format context with detailed metadata."""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk.get('paper_metadata', {})
            title = meta.get('title', 'Unknown')
            authors = meta.get('authors', [])
            year = meta.get('publication_year', 'N/A')
            section = chunk.get('section', 'unknown')
            text = chunk.get('text', '')
            
            author_str = ", ".join(authors[:2]) if authors else "Unknown"
            if len(authors) > 2:
                author_str += " et al."
            
            part = f"""[Source {i}] {title}
Authors: {author_str} ({year})
Section: {section}
Content: {text}
"""
            parts.append(part)
        return "\n---\n".join(parts)


class HallucinationPrevention:
    """Prompts and strategies for preventing hallucinations."""
    
    @staticmethod
    def get_grounding_instruction() -> str:
        """Get instruction for grounding answers in sources."""
        return """
GROUNDING RULES:
- Every sentence must be traceable to a source
- Use direct quotes when possible
- Paraphrase accurately without adding information
- If you cannot find information, say so explicitly
- Do not fill gaps with assumptions
"""
    
    @staticmethod
    def get_uncertainty_phrases() -> List[str]:
        """Get phrases for expressing uncertainty."""
        return [
            "Based on the provided sources",
            "According to the available information",
            "The sources suggest",
            "Limited information is available about",
            "The provided context does not fully address",
            "While the sources mention X, they do not specify Y",
            "This information is not explicitly stated in the sources"
        ]
    
    @staticmethod
    def build_fact_check_prompt(
        statement: str,
        context_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for fact-checking a statement.
        
        Args:
            statement: Statement to fact-check
            context_chunks: Source chunks
            
        Returns:
            Fact-checking prompt
        """
        context = RAGPrompts._format_context_simple(context_chunks)
        
        prompt = f"""Fact-check the following statement against the provided sources.

STATEMENT: {statement}

SOURCES:
{context}

FACT-CHECK ANALYSIS:
1. Verdict: [SUPPORTED / PARTIALLY SUPPORTED / NOT SUPPORTED / CONTRADICTED]
2. Evidence: [Quote relevant parts from sources]
3. Confidence: [High / Medium / Low]
4. Explanation: [Detailed explanation of verdict]
5. Caveats: [Any important nuances or limitations]

RESULT:
"""
        
        return prompt


# Export main class
__all__ = ['RAGPrompts', 'HallucinationPrevention']
