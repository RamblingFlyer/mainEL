#!/usr/bin/env python3
from pathlib import Path
import json, os
ROOT = Path.home() / "nerf_project" / "data" / "room"
COL_TXT = ROOT / "sparse_txt" / "cameras.txt"
TRANS = ROOT / "nerfstudio" / "transforms.json"
BACKUP = ROOT / "nerfstudio" / "transforms_with_intrinsics_backup.json"

def parse_cameras(path):
    cams = {}
    if not path.exists(): return cams
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip(): continue
            parts = line.strip().split()
            cam_id = parts[0]
            model = parts[1]
            w = int(parts[2]); h = int(parts[3])
            params = list(map(float, parts[4:])) if len(parts) > 4 else []
            cams[cam_id] = {'model': model, 'width': w, 'height': h, 'params': params}
    return cams

def main():
    if not TRANS.exists():
        print("ERROR: transforms.json missing at", TRANS); return
    data = json.loads(TRANS.read_text())
    frames = data.get('frames', [])
    if not frames:
        print("ERROR: transforms.json has no frames"); return

    cams = parse_cameras(COL_TXT)

    # backup
    BACKUP.write_text(json.dumps(data, indent=2))
    print("Backup saved to", BACKUP)

    updated = 0
    missing = []
    for fr in frames:
        # if w and h already present skip
        if 'w' in fr and 'h' in fr:
            continue

        filename = os.path.basename(fr.get('file_path',''))
        w = h = None

        # try to find camera id via cameras.txt->images.txt mapping if possible
        # fallback: read actual image file size
        # first: try cameras.txt via images.txt
        cam_found = None
        images_txt = ROOT / "sparse_txt" / "images.txt"
        if images_txt.exists():
            with open(images_txt, 'r') as f:
                for line in f:
                    if line.startswith('#') or not line.strip(): continue
                    parts = line.strip().split()
                    if len(parts) >= 10:
                        name = parts[9]
                        if name == filename:
                            cam_id = parts[8]
                            cam_found = cam_id
                            break
        if cam_found and cam_found in cams:
            w = cams[cam_found]['width']
            h = cams[cam_found]['height']
        else:
            # try to inspect the actual image file in nerfstudio/images
            try:
                from PIL import Image
                imgp = ROOT / 'nerfstudio' / 'images' / filename
                with Image.open(imgp) as im:
                    w,h = im.size
            except Exception:
                w=h=None

        if w is None or h is None:
            missing.append(filename)
            # set safe defaults (common)
            w,h = 1600, 1200

        fr['w'] = int(w)
        fr['h'] = int(h)
        updated += 1

    # write back
    with open(TRANS, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Updated w/h for {updated} frames. {len(missing)} frames used fallback defaults.")
    if missing:
        print("Fallback applied to:", missing[:20])

if __name__ == '__main__':
    main()
