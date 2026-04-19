import networkx as nx

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
            
            # Create a directional edge for the neurosymbolic link
            self.graph.add_edge(subject, obj, relation=relation)
            self.save()

    def get_related_facts(self, entity):
        entity = entity.strip().lower()
        facts = []
        
        # Fuzzy/Substring match for nodes
        target_nodes = []
        for node in self.graph.nodes:
            if entity in node.lower():
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
        return facts

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
