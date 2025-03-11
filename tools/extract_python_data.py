
import os
import ast

def generate_markdown_for_directory(directory: str) -> str:
    """
    Scans the given directory (recursively) for Python files, extracts top-level functions and classes
    along with their docstrings, and returns a Markdown formatted text.

    Parameters:
        directory (str): The path to the directory to scan.

    Returns:
        str: The generated Markdown documentation as a string.
    """
    markdown_lines = []
    markdown_lines.append(f"# Documentation for Directory: `{directory}`\n")
    
    # Track already seen definitions: (type, name, docstring)
    seen_definitions = set()
    
    # Walk through the directory recursively.
    for root, _, files in os.walk(directory):
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue

            file_path = os.path.join(root, filename)
            # Get the relative path from the base directory for clarity.
            relative_file_path = os.path.relpath(file_path, directory)
            markdown_lines.append(f"## File: `{relative_file_path}`\n")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_contents = f.read()
                tree = ast.parse(file_contents, filename=filename)
            except Exception as e:
                markdown_lines.append(f"*Error parsing file: {e}*\n")
                continue

            # Extract definitions: functions and classes at the top level
            definitions_found = False
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node) or "*No docstring available.*"
                    key = ("Function", node.name, doc)
                    if key in seen_definitions:
                        continue
                    seen_definitions.add(key)
                    markdown_lines.append(f"### Function: `{node.name}`\n")
                    markdown_lines.append(f"{doc}\n")
                    definitions_found = True
                elif isinstance(node, ast.ClassDef):
                    doc = ast.get_docstring(node) or "*No docstring available.*"
                    key = ("Class", node.name, doc)
                    if key in seen_definitions:
                        continue
                    seen_definitions.add(key)
                    markdown_lines.append(f"### Class: `{node.name}`\n")
                    markdown_lines.append(f"{doc}\n")
                    definitions_found = True
            
            if not definitions_found:
                markdown_lines.append("*No functions or classes found in this file.*\n")
    
    return "\n".join(markdown_lines)

# Allow running the module as a standalone script for quick testing.
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python extract_python_data.py <directory_path>")
        sys.exit(1)
    directory_path = sys.argv[1]
    output = generate_markdown_for_directory(directory_path)
    print(output)
