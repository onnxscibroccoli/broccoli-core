import os
import time

def dump_python_files(start_dir=".", delay_per_line=0.03):
    """
    Finds all .py files in start_dir and prints their contents
    line-by-line with a specified delay (in seconds).
    """
    for root, _, files in os.walk(start_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                
                # Banner for each file header
                banner = f"\n{'=' * 60}\nFILE: {file_path}\n{'=' * 60}\n"
                print(banner, flush=True)
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            print(line, end="", flush=True)
                            time.sleep(delay_per_line)
                except Exception as e:
                    print(f"\n[Error reading {file_path}: {e}]", flush=True)

if __name__ == "__main__":
    # Adjust delay_per_line to control speed (e.g., 0.03 = ~33 lines per second)
    dump_python_files(start_dir=".", delay_per_line=0.03)

