import xml.etree.ElementTree as ET
from pathlib import Path

env_dir = Path('~/odoo-env').expanduser()
src_dir = Path('~/src').expanduser()

if not env_dir.exists():
    print("odoo-env not found")
    exit(1)

for version_path in env_dir.iterdir():
    if not version_path.is_dir():
        continue

    ws_file = src_dir / version_path.name / '.idea' / 'workspace.xml'
    
    if not ws_file.exists():
        continue

    try:
        tree = ET.parse(ws_file)
        root = tree.getroot()
        run_mgr = root.find(".//component[@name='RunManager']")

        if run_mgr is not None:
            root.remove(run_mgr)
            tree.write(ws_file, encoding='utf-8', xml_declaration=True)
            print(f"Nuked RunManager in {version_path.name}")
            
    except Exception as e:
        print(f"Failed on {version_path.name}: {e}")
