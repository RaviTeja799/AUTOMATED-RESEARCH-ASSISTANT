"""
Test script for PDF ingestion pipeline.

This script demonstrates the complete PDF processing workflow:
1. Load a sample PDF
2. Process through the pipeline
3. Verify indexing
4. Query the indexed content
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document_service import DocumentService
from app.retrieval.elasticsearch_client import es_client
from app.services.embedding_service import embedding_service
from app.utils.logger import app_logger


async def test_pipeline(pdf_path: str):
    """
    Test the complete PDF ingestion pipeline.
    
    Args:
        pdf_path: Path to PDF file to process
    """
    print("=" * 80)
    print("PDF INGESTION PIPELINE TEST")
    print("=" * 80)
    
    # Initialize services
    print("\n1. Initializing services...")
    doc_service = DocumentService(
        es_client=es_client,
        embedding_service=embedding_service
    )
    
    # Initialize Elasticsearch
    await es_client.initialize()
    print("✓ Services initialized")
    
    # Load PDF
    print(f"\n2. Loading PDF: {pdf_path}")
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"✗ Error: File not found: {pdf_path}")
        return
    
    file_content = pdf_file.read_bytes()
    file_size_mb = len(file_content) / (1024 * 1024)
    print(f"✓ Loaded {file_size_mb:.2f} MB")
    
    # Process document
    print("\n3. Processing document through pipeline...")
    print("   - Extracting text from PDF")
    print("   - Preprocessing and cleaning")
    print("   - Detecting sections")
    print("   - Chunking semantically")
    print("   - Generating embeddings")
    print("   - Indexing in Elasticsearch")
    
    response = await doc_service.process_document(
        file_content=file_content,
        filename=pdf_file.name
    )
    
    # Display results
    print("\n" + "=" * 80)
    print("PROCESSING RESULTS")
    print("=" * 80)
    print(f"Status: {response.status}")
    print(f"Paper ID: {response.paper_id}")
    print(f"Message: {response.message}")
    print(f"Processing Time: {response.processing_time:.2f}s")
    print(f"Number of Chunks: {response.num_chunks}")
    
    if response.metadata:
        print("\nMetadata:")
        print(f"  Title: {response.metadata.title or 'N/A'}")
        print(f"  Authors: {', '.join(response.metadata.authors) or 'N/A'}")
        print(f"  Pages: {response.metadata.num_pages or 'N/A'}")
        print(f"  DOI: {response.metadata.doi or 'N/A'}")
        if response.metadata.abstract:
            print(f"  Abstract: {response.metadata.abstract[:200]}...")
        if response.metadata.keywords:
            print(f"  Keywords: {', '.join(response.metadata.keywords)}")
    
    if response.status == "success":
        # Get paper info
        print("\n4. Retrieving paper information...")
        paper_info = await doc_service.get_paper_info(response.paper_id)
        
        if paper_info:
            print(f"✓ Paper retrieved successfully")
            print(f"  Sections detected: {', '.join(paper_info.sections) or 'None'}")
            print(f"  Total chunks: {paper_info.num_chunks}")
        
        # Get paper sections
        print("\n5. Retrieving paper sections...")
        sections = await doc_service.get_paper_sections(response.paper_id)
        
        print(f"✓ Retrieved {len(sections)} sections:")
        for section_name, section_text in sections.items():
            word_count = len(section_text.split())
            print(f"  - {section_name}: {word_count} words")
            print(f"    Preview: {section_text[:150]}...")
        
        # Test search
        print("\n6. Testing search functionality...")
        query = "methodology"
        query_embedding = embedding_service.embed_query(query)
        
        results = await es_client.hybrid_search(
            query_text=query,
            query_embedding=query_embedding,
            top_k=3
        )
        
        print(f"✓ Search for '{query}' returned {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    Section: {result.get('section', 'N/A')}")
            print(f"    Page: {result.get('page_number', 'N/A')}")
            print(f"    Score: {result['score']:.4f}")
            print(f"    Text: {result['text'][:150]}...")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nPaper ID: {response.paper_id}")
        print("You can now query this paper using the API or agent.")
        
    else:
        print("\n✗ Processing failed")
        print(f"Error: {response.message}")
    
    # Cleanup
    await es_client.close()


async def list_all_papers():
    """List all papers in the system."""
    print("\n" + "=" * 80)
    print("LISTING ALL PAPERS")
    print("=" * 80)
    
    doc_service = DocumentService(
        es_client=es_client,
        embedding_service=embedding_service
    )
    
    await es_client.initialize()
    
    papers = await doc_service.list_papers(skip=0, limit=100)
    
    if not papers:
        print("No papers found in the system.")
    else:
        print(f"\nFound {len(papers)} papers:\n")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.metadata.title or 'Untitled'}")
            print(f"   ID: {paper.paper_id}")
            print(f"   Authors: {', '.join(paper.metadata.authors) or 'N/A'}")
            print(f"   Chunks: {paper.num_chunks}")
            print(f"   Sections: {', '.join(paper.sections) or 'N/A'}")
            print()
    
    await es_client.close()


async def delete_paper(paper_id: str):
    """Delete a paper from the system."""
    print(f"\nDeleting paper: {paper_id}")
    
    doc_service = DocumentService(
        es_client=es_client,
        embedding_service=embedding_service
    )
    
    await es_client.initialize()
    
    success = await doc_service.delete_paper(paper_id)
    
    if success:
        print("✓ Paper deleted successfully")
    else:
        print("✗ Paper not found")
    
    await es_client.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test PDF ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a PDF
  python test_pdf_pipeline.py process path/to/paper.pdf
  
  # List all papers
  python test_pdf_pipeline.py list
  
  # Delete a paper
  python test_pdf_pipeline.py delete PAPER_ID
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Process command
    process_parser = subparsers.add_parser("process", help="Process a PDF file")
    process_parser.add_argument("pdf_path", help="Path to PDF file")
    
    # List command
    subparsers.add_parser("list", help="List all papers")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a paper")
    delete_parser.add_argument("paper_id", help="Paper ID to delete")
    
    args = parser.parse_args()
    
    if args.command == "process":
        asyncio.run(test_pipeline(args.pdf_path))
    elif args.command == "list":
        asyncio.run(list_all_papers())
    elif args.command == "delete":
        asyncio.run(delete_paper(args.paper_id))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
