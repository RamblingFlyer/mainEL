#!/usr/bin/env python3
"""
Fuzzy converter: match COLMAP images.txt names to files in nerfstudio/images using fuzzy matching.
Writes transforms.json acceptable to Nerfstudio.

Usage:
 python convert_colmap_fuzzy_to_transforms.py \
   --colmap_txt_dir ~/nerf_project/data/room/sparse_txt \
   --images_dir ~/nerf_project/data/room/nerfstudio/images \
   --out ~/nerf_project/data/room/nerfstudio/transforms.json
"""
import argparse, os, json, math
import numpy as np
from difflib import get_close_matches

def parse_cameras_txt(path):
    cams = {}
    with open(path,'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip(): continue
            parts = line.strip().split()
            cam_id = parts[0]; model = parts[1]; w=int(parts[2]); h=int(parts[3])
            params = list(map(float, parts[4:]))
            cams[cam_id] = {'model':model, 'width':w, 'height':h, 'params':params}
    return cams

def parse_images_txt(path):
    imgs = []
    with open(path,'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip(): continue
            parts = line.strip().split()
            if len(parts) < 9: continue
            img_id = parts[0]
            qw,qx,qy,qz = map(float, parts[1:5])
            tx,ty,tz = map(float, parts[5:8])
            cam_id = parts[8]
            name = parts[9]
            imgs.append({'id':img_id, 'qvec':[qw,qx,qy,qz], 'tvec':[tx,ty,tz], 'cam_id':cam_id, 'name':name})
    return imgs

def qvec2rotmat(q):
    qw,qx,qy,qz = q
    n = math.sqrt(qw*qw+qx*qx+qy*qy+qz*qz)
    qw,qx,qy,qz = qw/n,qx/n,qy/n,qz/n
    R = np.zeros((3,3))
    R[0,0] = 1 - 2*qy*qy - 2*qz*qz
    R[0,1] = 2*qx*qy - 2*qz*qw
    R[0,2] = 2*qx*qz + 2*qy*qw
    R[1,0] = 2*qx*qy + 2*qz*qw
    R[1,1] = 1 - 2*qx*qx - 2*qz*qz
    R[1,2] = 2*qy*qz - 2*qx*qw
    R[2,0] = 2*qx*qz - 2*qy*qw
    R[2,1] = 2*qy*qz + 2*qx*qw
    R[2,2] = 1 - 2*qx*qx - 2*qy*qy
    return R

def build_M(qvec,tvec):
    R = qvec2rotmat(qvec)
    t = np.array(tvec).reshape(3,)
    M = np.eye(4).tolist()
    M = np.array(M, dtype=float)
    M[:3,:3] = R
    M[:3,3] = t
    return M.tolist()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--colmap_txt_dir', required=True)
    p.add_argument('--images_dir', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()

    cams_path = os.path.join(args.colmap_txt_dir, 'cameras.txt')
    imgs_path = os.path.join(args.colmap_txt_dir, 'images.txt')
    if not os.path.exists(cams_path) or not os.path.exists(imgs_path):
        print("ERROR: Missing cameras.txt or images.txt in", args.colmap_txt_dir); return

    cams = parse_cameras_txt(cams_path)
    imgs = parse_images_txt(imgs_path)
    if len(cams)==0 or len(imgs)==0:
        print("ERROR: no cameras or no images parsed"); return

    # list available files
    available = sorted(os.listdir(args.images_dir))
    # build lookup by lowercase for more robust matching
    avail_lower = {fn.lower():fn for fn in available}

    # compute camera_angle_x from first camera
    first_cam = next(iter(cams.values()))
    f = first_cam['params'][0]; w = first_cam['width']
    camera_angle_x = 2.0 * math.atan(w/(2.0*f))

    frames=[]
    unmatched=[]
    matches=[]
    for im in imgs:
        colname = im['name']
        candidates = []
        # exact match
        if colname in available:
            chosen = colname
        elif colname.lower() in avail_lower:
            chosen = avail_lower[colname.lower()]
        else:
            # try ns prefix variants and common variants
            prefixed = 'frame_' + colname
            if prefixed in available:
                chosen = prefixed
            else:
                # try best fuzzy match by substring or difflib
                substr_matches = [fn for fn in available if colname in fn or colname.split('.')[0] in fn]
                if substr_matches:
                    chosen = substr_matches[0]
                else:
                    # difflib top match
                    best = get_close_matches(colname, available, n=1, cutoff=0.4)
                    if best:
                        chosen = best[0]
                    else:
                        chosen = None
        if not chosen:
            unmatched.append(colname)
            continue
        M = build_M(im['qvec'], im['tvec'])
        frames.append({'file_path': f"images/{chosen}", 'transform_matrix': M})
        matches.append((colname, chosen))

    out = {'camera_angle_x': camera_angle_x, 'frames': frames}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out,'w') as f:
        json.dump(out, f, indent=2)
    print(f"WROTE {args.out} with {len(frames)} frames. {len(unmatched)} unmatched.")

    if matches:
        print("\nSAMPLE matches (COLMAP_name -> matched_file):")
        for a,b in matches[:30]:
            print("  ", a, "->", b)
    if unmatched:
        print("\nUNMATCHED names (first 30):")
        for u in unmatched[:30]:
            print("  ", u)
    if unmatched:
        print("\nIf many names are unmatched, consider renaming the files in nerfstudio/images or copying files to names that match COLMAP image names.")
    print("\nDone.")
if __name__=='__main__':
    main()
