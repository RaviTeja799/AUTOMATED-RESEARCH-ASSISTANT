"""
Centralized prompt templates for LLM interactions.
"""

# ============================================================================
# RAG Query Prompts
# ============================================================================

RAG_SYSTEM_PROMPT = """You are a helpful research assistant with expertise in academic literature.
Your role is to answer questions based on the provided research paper excerpts.

Guidelines:
- Answer based ONLY on the provided context
- If the context doesn't contain enough information, explicitly say so
- Cite sources using [Paper Title, Page X] format
- Be precise and academic in your language
- Never hallucinate or make up information
- If multiple papers are relevant, synthesize information from all of them
"""

RAG_QUERY_TEMPLATE = """Context from research papers:

{context}

Question: {question}

Please provide a comprehensive answer based on the context above. Include citations for all claims."""

RAG_QUERY_WITH_CITATIONS_TEMPLATE = """Context from research papers:

{context}

Question: {question}

Instructions:
1. Answer the question using ONLY the information from the context
2. For each claim, include a citation in the format [Source N]
3. If the context is insufficient, state: "The provided context does not contain enough information to answer this question."
4. Be specific and reference exact findings from the papers

Answer:"""

# ============================================================================
# Summarization Prompts
# ============================================================================

SUMMARIZE_BRIEF_TEMPLATE = """Provide a brief summary (2-3 paragraphs) of the following research paper:

Title: {title}
Authors: {authors}

Content:
{content}

Summary should include:
- Main research question or objective
- Key methodology
- Primary findings
- Significance

Brief Summary:"""

SUMMARIZE_COMPREHENSIVE_TEMPLATE = """Provide a comprehensive summary of the following research paper:

Title: {title}
Authors: {authors}

Content:
{content}

Your summary should include:
1. Research Context and Motivation (1 paragraph)
2. Research Questions/Objectives (bullet points)
3. Methodology (1-2 paragraphs)
4. Key Findings (bullet points)
5. Conclusions and Implications (1 paragraph)
6. Limitations (if mentioned)

Comprehensive Summary:"""

SUMMARIZE_TECHNICAL_TEMPLATE = """Provide a technical summary of the following research paper, focusing on methodology and technical details:

Title: {title}
Authors: {authors}

Content:
{content}

Your technical summary should include:
1. Technical Problem Statement
2. Proposed Approach/Method (detailed)
3. Experimental Setup
4. Results and Metrics
5. Technical Contributions
6. Comparison with Baselines

Technical Summary:"""

EXTRACT_KEY_FINDINGS_TEMPLATE = """Extract the key findings from this research paper:

{content}

List 3-7 key findings as bullet points. Each finding should be:
- Specific and concrete
- Supported by the paper's results
- Clearly stated

Key Findings:"""

# ============================================================================
# Literature Review Prompts
# ============================================================================

LITERATURE_REVIEW_TEMPLATE = """Generate a literature review on the topic: {topic}

Based on the following research papers:

{papers_summary}

Your literature review should include:

1. OVERVIEW (1-2 paragraphs)
   - Introduce the topic and its significance
   - Scope of the review

2. KEY THEMES
   - Identify 3-5 major themes across the papers
   - For each theme, discuss which papers address it and how

3. METHODOLOGICAL APPROACHES
   - Summarize the different methodologies used
   - Compare and contrast approaches

4. MAIN FINDINGS AND CONSENSUS
   - What do most papers agree on?
   - What are the consistent findings?

5. CONTRADICTIONS AND DEBATES
   - Where do papers disagree?
   - What questions remain unresolved?

6. RESEARCH GAPS
   - What hasn't been studied?
   - What are the limitations of current research?

7. FUTURE DIRECTIONS
   - What are promising areas for future research?
   - What questions should be addressed next?

Literature Review:"""

COMPARE_PAPERS_TEMPLATE = """Compare and contrast the following research papers:

{papers}

Comparison should cover:
1. Research Questions/Objectives
2. Methodologies
3. Key Findings
4. Strengths and Limitations
5. How they relate to each other

Comparison:"""

# ============================================================================
# Agent Prompts
# ============================================================================

AGENT_SYSTEM_PROMPT = """You are a research assistant agent with access to tools for analyzing academic papers.

Your capabilities:
- Search and retrieve relevant papers
- Summarize papers
- Answer questions using RAG
- Compare multiple papers
- Generate literature reviews

When given a task:
1. Analyze what information you need
2. Use appropriate tools to gather information
3. Synthesize information to answer the user's question
4. Always cite sources

Be thorough, accurate, and academic in your responses."""

ROUTE_QUERY_TEMPLATE = """Analyze the following user query and determine the best approach:

Query: {query}

Options:
1. SIMPLE_QA - Direct question answering using RAG
2. SUMMARIZE - User wants a summary of a specific paper
3. COMPARE - User wants to compare multiple papers
4. LITERATURE_REVIEW - User wants a comprehensive review of a topic
5. SEARCH - User wants to find relevant papers

Respond with just the option name (e.g., "SIMPLE_QA")

Classification:"""

# ============================================================================
# Citation Extraction Prompts
# ============================================================================

EXTRACT_CITATIONS_TEMPLATE = """Extract all citations/references from the following text:

{text}

List each citation in the format:
- Authors (Year). Title. Journal/Conference.

Citations:"""

# ============================================================================
# Quality Check Prompts
# ============================================================================

CHECK_ANSWER_QUALITY_TEMPLATE = """Evaluate the quality of this answer:

Question: {question}
Answer: {answer}
Context: {context}

Check:
1. Is the answer supported by the context?
2. Are there any unsupported claims?
3. Are citations accurate?
4. Is the answer complete?

Evaluation:"""

# ============================================================================
# Helper Functions
# ============================================================================

def format_context_for_rag(chunks: list) -> str:
    """Format retrieved chunks for RAG prompt."""
    context_parts = []
    
    for i, chunk in enumerate(chunks, 1):
        paper_title = chunk.get("paper_metadata", {}).get("title", "Unknown")
        page = chunk.get("page_number", "?")
        text = chunk.get("text", "")
        
        context_parts.append(
            f"[Source {i}] {paper_title} (Page {page}):\n{text}\n"
        )
    
    return "\n".join(context_parts)


def format_papers_for_review(papers: list) -> str:
    """Format papers for literature review prompt."""
    papers_text = []
    
    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "Unknown")
        authors = ", ".join(paper.get("authors", []))
        summary = paper.get("summary", "")
        
        papers_text.append(
            f"{i}. {title}\n"
            f"   Authors: {authors}\n"
            f"   Summary: {summary}\n"
        )
    
    return "\n".join(papers_text)
