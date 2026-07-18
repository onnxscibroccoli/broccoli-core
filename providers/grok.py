class GrokProvider:
    def initialize(self):
        print("[grok] initialized")
        return True
    def send(self, request):
        return {"content": f"Reply to: {request.get('message','')}"}
