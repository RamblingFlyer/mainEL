#!/usr/bin/env python3
# Creates symlinks in nerfstudio/images so COLMAP image names exist.
import os,sys
from difflib import get_close_matches

colmap_txt = os.path.expanduser('~/nerf_project/data/room/sparse_txt/images.txt')
images_dir = os.path.expanduser('~/nerf_project/data/room/nerfstudio/images')
if not os.path.exists(colmap_txt):
    print("Missing", colmap_txt); sys.exit(1)
if not os.path.isdir(images_dir):
    print("Missing images dir", images_dir); sys.exit(1)

# read colmap image names
names=[]
with open(colmap_txt,'r') as f:
    for line in f:
        if line.startswith('#') or not line.strip(): continue
        parts=line.strip().split()
        if len(parts) >= 10:
            names.append(parts[9])
# available files
available = sorted(os.listdir(images_dir))
print("Found", len(names), "COLMAP names and", len(available), "available files")

for colname in names:
    # if exact exists, skip
    target_path = os.path.join(images_dir, colname)
    if os.path.exists(target_path):
        continue
    # try to find best match
    best = None
    lowers = {fn.lower():fn for fn in available}
    if colname.lower() in lowers:
        best = lowers[colname.lower()]
    else:
        # substring
        for fn in available:
            if colname in fn or colname.split('.')[0] in fn:
                best = fn; break
        if not best:
            matches = get_close_matches(colname, available, n=1, cutoff=0.3)
            if matches: best = matches[0]
    if not best:
        print("NO MATCH for:", colname)
        continue
    src = os.path.join(images_dir, best)
    dst = target_path
    try:
        if os.path.exists(dst):
            continue
        os.symlink(src, dst)
        print("LINK", colname, "<--", best)
    except Exception as e:
        print("ERR symlink", colname, e)
print("Done.")
