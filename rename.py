import os

def rename_project(directory):
    for root, dirs, files in os.walk(directory):
        # Exclude hidden directories like .git, .venv
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith(('.py', '.md', '.ini', '.yml', '.example', '.txt')) or file == 'Makefile':
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    new_content = new_content.replace('Foedus', 'Foedus')
                    new_content = new_content.replace('FOEDUS', 'FOEDUS')
                    new_content = new_content.replace('foedus', 'foedus')
                    
                    if content != new_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Renamed in {filepath}")
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

if __name__ == '__main__':
    rename_project(r'c:\rifle\foedus')
