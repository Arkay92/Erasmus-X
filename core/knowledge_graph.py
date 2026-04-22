import networkx as nx
import re

class KnowledgeGraph:
    def __init__(self, storage=None):
        """
        Initializes the Knowledge Graph.
        If storage (HypervectorDB) is provided, it uses it as the persistent backend.
        """
        self.storage = storage
        self.graph = nx.DiGraph()
        self.load()

    def add_triplet(self, subject, relation, obj):
        # Prevent empty additions
        if subject and relation and obj:
            subject = subject.strip().lower()
            obj = obj.strip().lower()
            relation = relation.strip().lower()
            
            # Check for existing triplet to prevent context bloating
            if self.graph.has_edge(subject, obj):
                if self.graph.edges[subject, obj].get('relation') == relation:
                    return # Exact duplicate found

            # Create a directional edge for the neurosymbolic link
            self.graph.add_edge(subject, obj, relation=relation)
            self.save()

    def get_related_facts(self, entity):
        entity = entity.strip().lower()
        facts = []
        
        # Fuzzy/Substring match for nodes
        target_nodes = []
        for node in self.graph.nodes:
            if entity in node.lower() or node.lower() in entity:
                target_nodes.append(node)
        
        for matched_node in target_nodes:
            # Outgoing edges
            for target in self.graph.successors(matched_node):
                rel = self.graph.edges[matched_node, target].get('relation', 'is')
                facts.append(f"{matched_node} {rel} {target}")
            # Incoming edges
            for source in self.graph.predecessors(matched_node):
                rel = self.graph.edges[source, matched_node].get('relation', 'is')
                facts.append(f"{source} {rel} {matched_node}")
        return list(set(facts)) # Dedup

    def get_related_facts_semantic(self, query_hv, brain, threshold=0.15):
        """
        Neurosymbolic Bridge: Finds the most similar CONCEPT in the KG 
        using hypervectors, then returns its symbolic relations.
        """
        if not self.graph.nodes:
            return []
            
        # 1. Collect semantic hit from the vector brain
        results = brain.search_by_hv(query_hv, threshold=threshold, top_k=1)
        
        if not results:
            return []
            
        # 2. For the top semantic hit, return its symbolic relations
        nearest_node = results[0][1].lower()
        return self.get_related_facts(nearest_node)

    def extract_from_llm_response(self, text):
        lines = text.split('\n')
        for line in lines:
            if '[FACT]' in line:
                try:
                    parts = line.replace('[FACT]', '').split('|')
                    if len(parts) >= 3:
                        self.add_triplet(parts[0], parts[1], parts[2])
                except Exception:
                    pass

    def save(self):
        """Syncs the graph data to the unified storage engine."""
        if self.storage:
            self.storage.graph_data = nx.node_link_data(self.graph, edges="edges")
            self.storage.save()

    def load(self):
        """Loads the graph data from the unified storage engine."""
        if self.storage and self.storage.graph_data:
            try:
                self.graph = nx.node_link_graph(self.storage.graph_data, edges="edges")
            except Exception:
                self.graph = nx.DiGraph()
        else:
            self.graph = nx.DiGraph()
