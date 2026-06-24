#!/usr/bin/env python3
import os
import sys

def convert_file(path):
    try:
        with open(path, 'rb') as fp:
            content = fp.read()
        if b'\r\n' in content:
            # Do a quick check to avoid converting binary files
            if b'\x00' not in content[:8192]:
                with open(path, 'wb') as fp:
                    fp.write(content.replace(b'\r\n', b'\n'))
                print(f"Converted to LF: {path}")
    except Exception as e:
        pass

def main():
    if len(sys.argv) < 2:
        print("Usage: convert_lf.py <repo_dir>")
        sys.exit(1)
    repo_dir = sys.argv[1]
    
    for root, dirs, files in os.walk(repo_dir):
        # Skip .git directories
        if '.git' in dirs:
            dirs.remove('.git')
        for f in files:
            path = os.path.join(root, f)
            convert_file(path)

if __name__ == '__main__':
    main()
