class Lifecycle:
    def startup(self, components):
        print("Runtime starting...")
        for c in components:
            print(f"  ✓ {c.__class__.__name__}")
        print("Runtime READY")
