from typing import Annotated, List, Optional
from langchain_core.tools import tool
from app.services.rag_service import RAGService

# Singleton instance - in a real app this might be dependency injected
rag_service = RAGService()

@tool
async def retrieve_documents(
    query: str,
    collection_names: Optional[List[str]] = None,
    n_results: int = 5
) -> str:
    """
    Retrieve relevant documents or context based on a query.
    Use this tool when you need to answer questions based on the provided documents.
    
    Args:
        query: The search query.
        collection_names: Optional list of specific collections to search in.
        n_results: Number of results to return.
    """
    try:
        # Initialize if not already
        rag_service._lazy_init()
        
        # If collection names are provided, use search_across_collections or specific search
        if collection_names:
            if len(collection_names) == 1:
                results = await rag_service.search(query, n_results=n_results, collection_name=collection_names[0])
            else:
                results = await rag_service.search_across_collections(query, collection_names, n_results=n_results)
        else:
            # Default search (search in currently active or all - simple fallback)
            results = await rag_service.search(query, n_results=n_results)
            
        if not results:
            return "No relevant documents found."
            
        formatted_results = []
        for i, res in enumerate(results, 1):
            content = res.get('content', '')
            source = res.get('metadata', {}).get('file_name', 'Unknown')
            formatted_results.append(f"[Source: {source}]\n{content}\n")
            
        return "\n---\n".join(formatted_results)
        
    except Exception as e:
        return f"Error retrieving documents: {str(e)}"
