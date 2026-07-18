import sys
sys.path.insert(0, '.')

from governor.engine import Governor

def main():
    print("🚀 Broccoli Core - Phase 3.10: Advanced Governor + Plugins\n")
    governor = Governor()
    try:
        governor.start()
    except KeyboardInterrupt:
        governor.stop()
        print("\n✅ Governor shutdown complete.")

if __name__ == "__main__":
    main()
