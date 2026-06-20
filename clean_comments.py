import os
import re

def clean_comments(directory):
    pattern = re.compile(r'^#\s*[─═]+.*$', re.MULTILINE)
    for root, _, files in os.walk(directory):
        # Skip virtual environment and .git
        if '.venv' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith(('.py', '.txt', '.example', '.ini', '.md')) or file == 'Makefile':
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = pattern.sub('', content)
                    
                    # Also remove empty lines that might have been left behind by removing comments
                    # But be careful not to remove all empty lines. Actually, just leaving empty lines is fine or we can remove multiple consecutive empty lines.
                    new_content = re.sub(r'\n{3,}', '\n\n', new_content)
                    
                    if content != new_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Cleaned {filepath}")
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

if __name__ == '__main__':
    clean_comments(r'c:\rifle\foedus')
