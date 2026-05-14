"""
Script to set up Elasticsearch indices with proper mappings.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import AsyncElasticsearch
from app.core.config import settings
from app.retrieval.index_manager import IndexManager
from app.utils.logger import app_logger


async def setup_indices():
    """Set up all Elasticsearch indices."""
    
    # Connect to Elasticsearch
    app_logger.info(f"Connecting to Elasticsearch: {settings.elasticsearch_url}")
    
    auth = None
    if settings.elasticsearch_username and settings.elasticsearch_password:
        auth = (settings.elasticsearch_username, settings.elasticsearch_password)
    
    client = AsyncElasticsearch(
        [settings.elasticsearch_url],
        basic_auth=auth,
    )
    
    try:
        # Test connection
        info = await client.info()
        app_logger.info(f"Connected to Elasticsearch {info['version']['number']}")
        
        # ============================================
        # 1. Create main papers index
        # ============================================
        index_name = settings.elasticsearch_index
        app_logger.info(f"Setting up index: {index_name}")
        
        # Delete if exists (for clean setup)
        if await client.indices.exists(index=index_name):
            app_logger.warning(f"Index {index_name} already exists. Deleting...")
            await client.indices.delete(index=index_name)
        
        # Create index with mapping
        mapping = IndexManager.get_papers_index_mapping()
        await client.indices.create(
            index=index_name,
            body=mapping
        )
        app_logger.info(f"✅ Created index: {index_name}")
        
        # ============================================
        # 2. Create papers summary index
        # ============================================
        summary_index = f"{index_name}_summaries"
        app_logger.info(f"Setting up index: {summary_index}")
        
        if await client.indices.exists(index=summary_index):
            app_logger.warning(f"Index {summary_index} already exists. Deleting...")
            await client.indices.delete(index=summary_index)
        
        summary_mapping = IndexManager.get_papers_summary_index_mapping()
        await client.indices.create(
            index=summary_index,
            body=summary_mapping
        )
        app_logger.info(f"✅ Created index: {summary_index}")
        
        # ============================================
        # 3. Create citation graph index
        # ============================================
        citation_index = f"{index_name}_citations"
        app_logger.info(f"Setting up index: {citation_index}")
        
        if await client.indices.exists(index=citation_index):
            app_logger.warning(f"Index {citation_index} already exists. Deleting...")
            await client.indices.delete(index=citation_index)
        
        citation_mapping = IndexManager.get_citation_graph_index_mapping()
        await client.indices.create(
            index=citation_index,
            body=citation_mapping
        )
        app_logger.info(f"✅ Created index: {citation_index}")
        
        # ============================================
        # 4. Create index template (optional)
        # ============================================
        template_name = f"{index_name}_template"
        app_logger.info(f"Setting up index template: {template_name}")
        
        template = IndexManager.create_index_template()
        await client.indices.put_index_template(
            name=template_name,
            body=template
        )
        app_logger.info(f"✅ Created index template: {template_name}")
        
        # ============================================
        # 5. Verify indices
        # ============================================
        app_logger.info("\n" + "="*60)
        app_logger.info("Index Setup Summary")
        app_logger.info("="*60)
        
        for idx in [index_name, summary_index, citation_index]:
            if await client.indices.exists(index=idx):
                stats = await client.indices.stats(index=idx)
                app_logger.info(f"✅ {idx}: Ready")
            else:
                app_logger.error(f"❌ {idx}: Not found")
        
        app_logger.info("="*60)
        app_logger.info("✅ Elasticsearch setup complete!")
        app_logger.info("="*60)
        
    except Exception as e:
        app_logger.error(f"Error setting up Elasticsearch: {e}", exc_info=True)
        raise
    finally:
        await client.close()


async def verify_indices():
    """Verify that indices are set up correctly."""
    
    app_logger.info("Verifying Elasticsearch indices...")
    
    auth = None
    if settings.elasticsearch_username and settings.elasticsearch_password:
        auth = (settings.elasticsearch_username, settings.elasticsearch_password)
    
    client = AsyncElasticsearch(
        [settings.elasticsearch_url],
        basic_auth=auth,
    )
    
    try:
        index_name = settings.elasticsearch_index
        
        # Check main index
        if await client.indices.exists(index=index_name):
            mapping = await client.indices.get_mapping(index=index_name)
            properties = mapping[index_name]['mappings']['properties']
            
            app_logger.info(f"\n{index_name} mapping:")
            app_logger.info(f"  - Fields: {len(properties)}")
            app_logger.info(f"  - Has embedding field: {'embedding' in properties}")
            app_logger.info(f"  - Has text field: {'text' in properties}")
            app_logger.info(f"  - Has paper_metadata: {'paper_metadata' in properties}")
            app_logger.info(f"  - Has citations: {'citations' in properties}")
            
            if 'embedding' in properties:
                emb_config = properties['embedding']
                app_logger.info(f"  - Embedding dims: {emb_config.get('dims')}")
                app_logger.info(f"  - Embedding similarity: {emb_config.get('similarity')}")
        else:
            app_logger.error(f"Index {index_name} not found!")
        
    except Exception as e:
        app_logger.error(f"Error verifying indices: {e}", exc_info=True)
    finally:
        await client.close()


async def delete_indices():
    """Delete all indices (use with caution!)."""
    
    app_logger.warning("⚠️  Deleting all indices...")
    
    response = input("Are you sure you want to delete all indices? (yes/no): ")
    if response.lower() != "yes":
        app_logger.info("Cancelled.")
        return
    
    auth = None
    if settings.elasticsearch_username and settings.elasticsearch_password:
        auth = (settings.elasticsearch_username, settings.elasticsearch_password)
    
    client = AsyncElasticsearch(
        [settings.elasticsearch_url],
        basic_auth=auth,
    )
    
    try:
        index_name = settings.elasticsearch_index
        indices = [
            index_name,
            f"{index_name}_summaries",
            f"{index_name}_citations"
        ]
        
        for idx in indices:
            if await client.indices.exists(index=idx):
                await client.indices.delete(index=idx)
                app_logger.info(f"✅ Deleted index: {idx}")
            else:
                app_logger.info(f"Index {idx} does not exist")
        
        # Delete template
        template_name = f"{index_name}_template"
        try:
            await client.indices.delete_index_template(name=template_name)
            app_logger.info(f"✅ Deleted template: {template_name}")
        except:
            pass
        
        app_logger.info("✅ All indices deleted")
        
    except Exception as e:
        app_logger.error(f"Error deleting indices: {e}", exc_info=True)
    finally:
        await client.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Elasticsearch index management")
    parser.add_argument(
        "action",
        choices=["setup", "verify", "delete"],
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    if args.action == "setup":
        asyncio.run(setup_indices())
    elif args.action == "verify":
        asyncio.run(verify_indices())
    elif args.action == "delete":
        asyncio.run(delete_indices())


if __name__ == "__main__":
    main()
