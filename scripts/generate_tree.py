from pathlib import Path
root=Path(__file__).resolve().parents[1]
skip={".git",".venv","node_modules",".next","__pycache__"}
lines=[root.name+"/"]
def walk(path:Path,prefix=""):
    entries=sorted([p for p in path.iterdir() if p.name not in skip],key=lambda p:(p.is_file(),p.name.lower()))
    for i,item in enumerate(entries):
        last=i==len(entries)-1; lines.append(prefix+("└── " if last else "├── ")+item.name+("/" if item.is_dir() else ""))
        if item.is_dir(): walk(item,prefix+("    " if last else "│   "))
walk(root); (root/"PROJECT_TREE.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
