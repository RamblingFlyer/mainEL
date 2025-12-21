#!/usr/bin/env python3
"""
convert_colmap_txt_to_transforms.py

Usage:
  python convert_colmap_txt_to_transforms.py \
    --colmap_txt_dir ~/nerf_project/data/room/sparse_txt \
    --images_dir ~/nerf_project/data/room/nerfstudio/images \
    --out ~/nerf_project/data/room/nerfstudio/transforms.json
"""
import argparse
import os
import json
import math
import numpy as np

def parse_cameras_txt(path):
    cameras = {}
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('#') or line.strip()=='':
                continue
            parts = line.strip().split()
            cam_id = parts[0]
            model = parts[1]
            width = int(parts[2])
            height = int(parts[3])
            params = list(map(float, parts[4:]))
            cameras[cam_id] = {
                'model': model,
                'width': width,
                'height': height,
                'params': params
            }
    return cameras

def qvec2rotmat(qvec):
    qw, qx, qy, qz = qvec
    n = math.sqrt(qw*qw + qx*qx + qy*qy + qz*qz)
    qw, qx, qy, qz = qw/n, qx/n, qy/n, qz/n
    R = np.zeros((3,3), dtype=float)
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

def parse_images_txt(path):
    images = []
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('#') or line.strip()=='':
                continue
            parts = line.strip().split()
            if len(parts) < 9:
                continue
            image_id = parts[0]
            qw, qx, qy, qz = map(float, parts[1:5])
            tx, ty, tz = map(float, parts[5:8])
            cam_id = parts[8]
            name = parts[9]
            images.append({
                'image_id': image_id,
                'qvec': [qw, qx, qy, qz],
                'tvec': [tx, ty, tz],
                'camera_id': cam_id,
                'name': name
            })
    return images

def build_transform_matrix(qvec, tvec):
    R = qvec2rotmat(qvec)
    t = np.array(tvec).reshape((3,1))
    M = np.eye(4)
    M[:3,:3] = R
    M[:3,3] = t.flatten()
    return M

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--colmap_txt_dir', required=True)
    parser.add_argument('--images_dir', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    cameras_txt = os.path.join(args.colmap_txt_dir, 'cameras.txt')
    images_txt = os.path.join(args.colmap_txt_dir, 'images.txt')

    cameras = parse_cameras_txt(cameras_txt)
    images = parse_images_txt(images_txt)

    # compute field of view from first camera
    first_cam = next(iter(cameras.values()))
    f = first_cam['params'][0]
    w = first_cam['width']
    camera_angle_x = 2.0 * math.atan(w / (2.0 * f))

    frames = []
    available_files = set(os.listdir(args.images_dir))

    for im in images:
        original_name = im['name']
        found_file = None

        # Try exact match
        if original_name in available_files:
            found_file = original_name
        else:
            # Try prefixed by ns-process-data
            prefixed = "frame_" + original_name
            if prefixed in available_files:
                found_file = prefixed
            else:
                # Try substring match
                for f in available_files:
                    if original_name in f:
                        found_file = f
                        break

        if not found_file:
            print("WARNING: Could not match image file for:", original_name)
            continue

        M = build_transform_matrix(im['qvec'], im['tvec'])

        frames.append({
            "file_path": f"images/{found_file}",
            "transform_matrix": M.tolist()
        })

    out = {
        "camera_angle_x": camera_angle_x,
        "frames": frames
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=2)

    print(f"✔ Wrote {args.out} with {len(frames)} frames.")

if __name__ == '__main__':
    main()


