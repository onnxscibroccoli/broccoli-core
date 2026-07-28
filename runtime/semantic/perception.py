class PerceptionRouter:

    def __init__(self,cache,observer,vision=None):
        self.cache=cache
        self.observer=observer
        self.vision=vision

    def acquire(self,goal):

        if self.cache.verify(goal):
            return self.cache.get(goal)

        result=self.observer.capture()

        if result:
            return result

        if self.vision:
            return self.vision.capture()

        return None
