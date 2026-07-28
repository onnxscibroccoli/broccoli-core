class PathMemory:

    def __init__(self):
        self.paths={}

    def remember(self,goal,path):
        self.paths[goal]=path

    def recall(self,goal):
        return self.paths.get(goal,[])

    def successful(self,goal):
        return goal in self.paths
