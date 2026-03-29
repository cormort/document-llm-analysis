import json
import os

import networkx as nx
import structlog

logger = structlog.get_logger()

# Define data directory for backend
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

class GraphRAGService:
    def __init__(self, persist_path: str = None):
        """Initialize Graph RAG Service"""
        self.persist_path = persist_path or os.path.join(DATA_DIR, "knowledge_graph.json")
        self.graph = nx.Graph()
        self._load_graph()

    def _load_graph(self):
        """Load graph from file"""
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, encoding='utf-8') as f:
                    data = json.load(f)
                    # Reconstruct NetworkX Graph
                    for node_data in data.get("nodes", []):
                        self.graph.add_node(node_data["id"], **node_data.get("metadata", {}))
                    for edge_data in data.get("edges", []):
                        self.graph.add_edge(
                            edge_data["source"], 
                            edge_data["target"], 
                            relation=edge_data.get("relation", ""),
                            weight=edge_data.get("weight", 1.0)
                        )
                logger.info("Loaded Knowledge Graph", nodes=self.graph.number_of_nodes())
            except Exception as e:
                logger.error("Failed to load graph", error=str(e))
                self.graph = nx.Graph()
        else:
            self.graph = nx.Graph()

    def save_graph(self):
        """Save graph to file"""
        try:
            data = {
                "nodes": [{"id": n, "metadata": self.graph.nodes[n]} for n in self.graph.nodes()],
                "edges": [
                    {
                        "source": u, 
                        "target": v, 
                        "relation": d.get("relation", ""), 
                        "weight": d.get("weight", 1.0)
                    } 
                    for u, v, d in self.graph.edges(data=True)
                ]
            }
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("Saved Knowledge Graph", nodes=self.graph.number_of_nodes())
        except Exception as e:
            logger.error("Failed to save graph", error=str(e))

    def add_triplets(self, extraction_data: dict, chunk_id: str):
        """
        Add extracted triplets to graph (SA-RAG enhanced)
        """
        entities = extraction_data.get("entities", [])
        relations = extraction_data.get("relations", [])
        
        # 1. Add Document node
        self.graph.add_node(chunk_id, type="document")
        
        # 2. Process Entities
        for ent in entities:
            name = ent.get("name", "").strip()
            if not name: continue
            
            # Entity Node
            if name not in self.graph:
                self.graph.add_node(name, type="entity", aliases=ent.get("aliases", []), ent_type=ent.get("type", ""))
            
            # Document -> Entity (describes)
            self.graph.add_edge(chunk_id, name, relation="describes", type="describes", weight=1.0)
            
            # Description Node
            desc_text = ent.get("description", "").strip()
            if desc_text:
                desc_id = f"desc_{hash(desc_text)}"
                self.graph.add_node(desc_id, type="description", text=desc_text)
                # Description -> Entity (describes)
                self.graph.add_edge(desc_id, name, relation="describes", type="describes", weight=1.0)

        # 3. Process Relations (Entity -> Entity)
        for rel in relations:
            sub = rel.get("subject", "").strip()
            obj = rel.get("object", "").strip()
            rel_text = rel.get("relation", "").strip()
            
            if not sub or not obj: continue
            
            # Ensure nodes exist
            for node in [sub, obj]:
                if node not in self.graph:
                    self.graph.add_node(node, type="entity")
            
            # Create or update related_to edge
            if self.graph.has_edge(sub, obj):
                self.graph[sub][obj]['weight'] = self.graph[sub][obj].get('weight', 1.0) + 0.1
            else:
                self.graph.add_edge(sub, obj, type="related_to", relation=rel_text, weight=1.0)

    def spreading_activation(
        self, 
        seed_entities: list[str], 
        max_steps: int = 3, 
        decay: float = 0.7, 
        threshold: float = 0.5,
        c: float = 0.4
    ) -> list[str]:
        """
        Spreading Activation Algorithm (matches SA-RAG)
        """
        if not seed_entities:
            return []

        # Initialize activations
        activations = {entity: 1.0 for entity in seed_entities if entity in self.graph}
        
        # Start BFS spreading
        import collections
        queue = collections.deque(seed_entities)
        
        for _ in range(max_steps):
            if not queue: break
            level_size = len(queue)
            for _ in range(level_size):
                u = queue.popleft()
                ai = activations.get(u, 0)
                
                for v in self.graph.neighbors(u):
                    # Get original weight
                    w = self.graph[u][v].get('weight', 1.0)
                    
                    # Edge Rescaling
                    w_prime = max(0, (w - c) / (1 - c)) if w > c else 0
                    if w_prime == 0: continue
                    
                    # Propagation
                    delta = ai * w_prime * decay
                    old_aj = activations.get(v, 0)
                    new_aj = min(1.0, old_aj + delta)
                    
                    if new_aj > old_aj:
                        activations[v] = new_aj
                        if v not in queue:
                            queue.append(v)

        # Filter activated nodes and collect associated Documents
        activated_docs = []
        for node, val in activations.items():
            if val >= threshold:
                # If entity, find connected Documents
                if self.graph.nodes[node].get('type') == 'entity':
                    for neighbor in self.graph.neighbors(node):
                        if self.graph.nodes[neighbor].get('type') == 'document':
                            activated_docs.append(neighbor)
                # If Document itself
                elif self.graph.nodes[node].get('type') == 'document':
                    activated_docs.append(node)
        
        return list(set(activated_docs))

# Singleton
graph_rag_service = GraphRAGService()
