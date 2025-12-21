#!/usr/bin/env python3
import os, json, math
from pathlib import Path

ROOT = Path.home() / "nerf_project" / "data" / "room"
COL_TXT = ROOT / "sparse_txt" / "cameras.txt"
IM_TXT = ROOT / "sparse_txt" / "images.txt"
TRANS = ROOT / "nerfstudio" / "transforms.json"
BACKUP = ROOT / "nerfstudio" / "transforms_backup.json"

def parse_cameras(path):
    cams = {}
    if not path.exists():
        return cams
    with open(path,'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split()
            cam_id = parts[0]
            model = parts[1]
            width = int(parts[2]); height = int(parts[3])
            params = list(map(float, parts[4:])) if len(parts) > 4 else []
            cams[cam_id] = {'model':model, 'width':width, 'height':height, 'params':params}
    return cams

def parse_images(path):
    imgs = {}
    if not path.exists():
        return imgs
    with open(path,'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) < 10:
                continue
            image_id = parts[0]
            qw,qx,qy,qz = map(float, parts[1:5])
            tx,ty,tz = map(float, parts[5:8])
            cam_id = parts[8]
            name = parts[9]
            imgs[name] = {'id':image_id, 'qvec':[qw,qx,qy,qz], 'tvec':[tx,ty,tz], 'cam_id':cam_id}
    return imgs

def main():
    if not TRANS.exists():
        print("ERROR: transforms.json not found at", TRANS)
        return
    data = json.loads(TRANS.read_text())
    frames = data.get('frames', [])
    if not frames:
        print("ERROR: no frames in transforms.json")
        return

    cameras = parse_cameras(COL_TXT)
    images = parse_images(IM_TXT)
    if not cameras or not images:
        print("WARNING: cameras.txt or images.txt missing/empty. Will attempt to infer intrinsics from camera_angle_x if present.")

    # backup
    BACKUP.write_text(json.dumps(data, indent=2))
    print("Wrote backup to", BACKUP)

    updated = 0
    for fr in frames:
        if all(k in fr for k in ("fl_x","fl_y","cx","cy")):
            continue
        fp = os.path.basename(fr.get('file_path',''))
        info = images.get(fp)
        cam = None
        if info:
            cam_id = info.get('cam_id')
            cam = cameras.get(cam_id)
        if cam:
            params = cam.get('params', [])
            w = cam.get('width', 800)
            h = cam.get('height', 600)
            if len(params) >= 4:
                fx = float(params[0]); fy = float(params[1]); cx = float(params[2]); cy = float(params[3])
            elif len(params) == 3:
                fx = fy = float(params[0]); cx = float(params[1]); cy = float(params[2])
            elif len(params) == 2:
                fx = float(params[0]); fy = float(params[1]); cx = w/2.0; cy = h/2.0
            elif len(params) == 1:
                fx = fy = float(params[0]); cx = w/2.0; cy = h/2.0
            else:
                fx = fy = max(w,h)/2.0; cx = w/2.0; cy = h/2.0
            fr['fl_x'] = fx; fr['fl_y'] = fy; fr['cx'] = cx; fr['cy'] = cy
            updated += 1
        else:
            if 'camera_angle_x' in data:
                camax = float(data['camera_angle_x'])
                try:
                    from PIL import Image
                    im_path = ROOT / 'nerfstudio' / fr['file_path']
                    w,h = Image.open(im_path).size
                except Exception:
                    w,h = 800,600
                f = 0.5 * w / math.tan(0.5 * camax)
                fr['fl_x'] = fr['fl_y'] = float(f)
                fr['cx'] = float(w/2.0); fr['cy'] = float(h/2.0)
                updated += 1
            else:
                print("Could not determine intrinsics for", fp, "- leaving frame unchanged")

    with open(TRANS,'w') as f:
        json.dump(data, f, indent=2)
    print(f"Updated intrinsics for {updated} frames. Wrote {TRANS}")

if __name__ == '__main__':
    main()
