class AccessibilityGraph:

    def __init__(self):
        self.nodes={}
        self.children={}

    def update_node(self,node):
        self.nodes[node["semantic_id"]]=node

    def remove_node(self,semantic_id):
        self.nodes.pop(semantic_id,None)

    def diff(self,new_nodes):

        added=[]
        updated=[]

        for n in new_nodes:
            sid=n["semantic_id"]

            if sid not in self.nodes:
                added.append(n)
            else:
                updated.append(n)

            self.nodes[sid]=n

        return {
            "added":added,
            "updated":updated
        }
