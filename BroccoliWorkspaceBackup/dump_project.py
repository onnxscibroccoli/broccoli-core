import os
import time
import binascii

def is_text_file(filepath, sample_size=1024):
    """
    Checks if a file is likely text or binary by reading a small chunk 
    and looking for null bytes.
    """
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(sample_size)
            if b'\0' in chunk:
                return False  # Contains null bytes, likely binary
            return True       # Likely text
    except Exception:
        return False # Fallback to binary/unreadable if there's an error

def dump_project_files(start_dir="broccoli", delay_per_line=0.02):
    """
    Finds all files in start_dir. If it's a text file (or has no extension), 
    prints contents line-by-line. If binary, prints a hex dump line-by-line.
    """
    if not os.path.exists(start_dir):
        print(f"Directory '{start_dir}' not found. Please run this from the parent directory or update the path.")
        return

    for root, _, files in os.walk(start_dir):
        for file in files:
            # Skip hidden directories like .git
            if '.git' in root:
                continue

            file_path = os.path.join(root, file)
            
            # Banner for each file header for easy LLM parsing
            banner = f"\n{'=' * 70}\nFILE: {file_path}\n{'=' * 70}\n"
            print(banner, flush=True)
            
            try:
                if is_text_file(file_path):
                    # Process as Text File
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            print(line, end="", flush=True)
                            time.sleep(delay_per_line)
                else:
                    # Process as Binary File (Hex Dump)
                    print("[BINARY FILE DETECTED - OUTPUTTING HEX DUMP]", flush=True)
                    with open(file_path, "rb") as f:
                        offset = 0
                        # Read in 16-byte chunks for a clean hex representation
                        while chunk := f.read(16):
                            hex_data = binascii.hexlify(chunk).decode('ascii')
                            # Space it out by bytes for readability (e.g., "ff 00 a1...")
                            spaced_hex = " ".join([hex_data[i:i+2] for i in range(0, len(hex_data), 2)])
                            print(f"{offset:08x}  {spaced_hex}", flush=True)
                            offset += 16
                            time.sleep(delay_per_line)
            except Exception as e:
                print(f"\n[Error reading {file_path}: {e}]", flush=True)

if __name__ == "__main__":
    # Pointing to the broccoli directory
    # delay_per_line = 0.02 for 1.5x speed
    dump_project_files(start_dir="broccoli", delay_per_line=0.02)
