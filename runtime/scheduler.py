import time
class Scheduler:
    def __init__(self):
        self.jobs = []
    def add_job(self, job, interval):
        self.jobs.append((job, interval))
    def run_pending(self):
        for job, _ in self.jobs:
            try:
                job()
            except Exception as e:
                print("Job error:", e)
