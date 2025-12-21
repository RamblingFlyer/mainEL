#!/usr/bin/env python3
"""
Aggressive Python matcher: creates symlinks in nerfstudio/images so COLMAP names exist,
then runs the fuzzy converter to generate transforms.json.

Run inside your venv:
python aggressive_symlink_and_convert.py
"""
import os,sys,shutil,subprocess
from difflib import get_close_matches

ROOT=os.path.expanduser('~/nerf_project/data/room')
COLMAP_TXT=os.path.join(ROOT, 'sparse_txt', 'images.txt')
IMAGES_DIR=os.path.join(ROOT, 'nerfstudio', 'images')
OUT_JSON=os.path.join(ROOT, 'nerfstudio', 'transforms.json')
PY_CONVERTER=os.path.join(ROOT, 'convert_colmap_fuzzy_to_transforms.py')

if not os.path.isfile(COLMAP_TXT):
    print("ERROR: missing", COLMAP_TXT); sys.exit(1)
if not os.path.isdir(IMAGES_DIR):
    print("ERROR: missing images dir", IMAGES_DIR); sys.exit(1)
if not os.path.isfile(PY_CONVERTER):
    print("ERROR: missing converter", PY_CONVERTER); sys.exit(1)

# read colmap names
colnames=[]
with open(COLMAP_TXT,'r') as f:
    for line in f:
        if line.startswith('#') or not line.strip(): continue
        parts=line.strip().split()
        if len(parts) >= 10:
            colnames.append(parts[9])

available = sorted(os.listdir(IMAGES_DIR))
available_lc = {fn.lower():fn for fn in available}

def norm(s):
    return ''.join(ch.lower() if ch.isalnum() or ch=='.' else ' ' for ch in s).strip()

created=0; unmatched=[]
for cname in colnames:
    target = os.path.join(IMAGES_DIR, cname)
    if os.path.exists(target):
        # already exists; skip
        continue

    # heuristics
    cname_l = cname.lower()
    found = None
    if cname_l in available_lc:
        found = available_lc[cname_l]
    else:
        # exact normalized match
        nc = norm(cname)
        for f in available:
            if norm(f) == nc or nc in norm(f):
                found = f; break
    if not found:
        # numeric token match
        import re
        nums = re.findall(r'\d+', cname)
        if nums:
            for f in available:
                for n in nums:
                    if n in f:
                        found = f; break
                if found: break
    if not found:
        # difflib fallback
        best = get_close_matches(cname, available, n=1, cutoff=0.3)
        if best: found = best[0]

    if not found:
        unmatched.append(cname)
        continue

    src = os.path.join(IMAGES_DIR, found)
    dst = target
    try:
        if os.path.exists(dst):
            pass
        else:
            # prefer symlink; if fails (FAT/permissions) copy the file
            try:
                os.symlink(src, dst)
            except Exception:
                shutil.copy2(src, dst)
        created += 1
        print("LINK", cname, "<--", found)
    except Exception as e:
        print("ERR creating link for", cname, e)
        unmatched.append(cname)

print("Created", created, "symlinks/copies. Unmatched:", len(unmatched))
if unmatched:
    print("Sample unmatched:", unmatched[:10])

# Run the existing fuzzy converter to build transforms.json
print("\nRunning fuzzy converter to build transforms.json...")
ret = subprocess.run([sys.executable, PY_CONVERTER, '--colmap_txt_dir', os.path.join(ROOT,'sparse_txt'),
                      '--images_dir', IMAGES_DIR, '--out', OUT_JSON], capture_output=True, text=True)
print(ret.stdout)
if ret.stderr:
    print("Converter stderr:\n", ret.stderr)

# Show result and frames count
if os.path.exists(OUT_JSON):
    print("\n----- transforms.json head -----")
    with open(OUT_JSON,'r') as f:
        for i,l in enumerate(f):
            if i>80: break
            print(l.rstrip())
    import json
    d=json.load(open(OUT_JSON))
    print("\nframes:", len(d.get('frames',[])))
else:
    print("ERROR: transforms.json not created.")
