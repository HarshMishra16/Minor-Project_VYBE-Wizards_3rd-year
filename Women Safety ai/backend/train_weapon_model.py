"""
╔══════════════════════════════════════════════════════════════════╗
║   SAKTI AI — Weapon Detection Model Training Pipeline           ║
║   train_weapon_model.py                                         ║
╠══════════════════════════════════════════════════════════════════╣
║   Run this script ONCE to:                                      ║
║   1. Inspect + validate your downloaded zip dataset             ║
║   2. Auto-detect and fix the folder structure                   ║
║   3. Generate the data.yaml config file                         ║
║   4. Train YOLOv8 on your weapon dataset                        ║
║   5. Validate the trained model                                  ║
║   6. Copy best.pt → best_weapon.pt (ready for app.py)           ║
║   7. Test inference on a sample image                           ║
╠══════════════════════════════════════════════════════════════════╣
║   Usage:                                                        ║
║   pip install ultralytics pillow                                ║
║   python train_weapon_model.py --zip path/to/dataset.zip        ║
║                                                                  ║
║   Optional flags:                                               ║
║   --epochs 50        (default: 50)                              ║
║   --imgsz  640       (default: 640)                             ║
║   --batch  8         (default: 8, use 4 if out of memory)       ║
║   --device cpu       (default: auto — GPU if available)         ║
║   --model  yolov8s.pt (default: yolov8n.pt  n=nano, s=small)   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import shutil
import zipfile
import argparse
import textwrap
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# ARGUMENT PARSER
# ═══════════════════════════════════════════════════════════════
def parse_args():
    p = argparse.ArgumentParser(
        description="Sakti AI — Weapon detection model training pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          python train_weapon_model.py --zip ~/Downloads/weapons.zip
          python train_weapon_model.py --zip dataset.zip --epochs 100 --batch 4
          python train_weapon_model.py --data ./dataset  # already extracted
        """)
    )
    p.add_argument("--zip",     type=str, help="Path to the downloaded dataset ZIP file")
    p.add_argument("--data",    type=str, default="weapon_dataset",
                   help="Where to extract / look for the dataset (default: ./weapon_dataset)")
    p.add_argument("--epochs",  type=int, default=50,   help="Training epochs (default: 50)")
    p.add_argument("--imgsz",   type=int, default=640,  help="Image size (default: 640)")
    p.add_argument("--batch",   type=int, default=8,    help="Batch size (default: 8)")
    p.add_argument("--model",   type=str, default="yolov8n.pt",
                   help="Base YOLO model (default: yolov8n.pt). Use yolov8s.pt for better accuracy.")
    p.add_argument("--device",  type=str, default="",
                   help="Device: '' = auto, 'cpu', '0' = GPU 0 (default: auto)")
    p.add_argument("--output",  type=str, default="best_weapon.pt",
                   help="Output model filename (default: best_weapon.pt)")
    p.add_argument("--test-image", type=str, default="",
                   help="Optional: path to a test image to run inference after training")
    return p.parse_args()


# ═══════════════════════════════════════════════════════════════
# STEP 1 — EXTRACT ZIP
# ═══════════════════════════════════════════════════════════════
def extract_zip(zip_path: str, dest: str) -> Path:
    zip_path = Path(zip_path)
    dest     = Path(dest)

    if not zip_path.exists():
        print(f"❌ ZIP file not found: {zip_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"📦 STEP 1 — Extracting dataset")
    print(f"{'='*60}")
    print(f"   Source : {zip_path}")
    print(f"   Dest   : {dest}")

    if dest.exists():
        print(f"   ⚠️  Destination already exists — skipping extraction.")
        print(f"      Delete '{dest}' and re-run to re-extract.")
    else:
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as z:
            members = z.namelist()
            print(f"   Files in ZIP: {len(members)}")
            print(f"   Extracting...")
            z.extractall(dest)
        print(f"   ✅ Extracted to: {dest}")

    return dest


# ═══════════════════════════════════════════════════════════════
# STEP 2 — INSPECT DATASET STRUCTURE
# ═══════════════════════════════════════════════════════════════
def inspect_dataset(root: Path) -> dict:
    """
    Walks the extracted folder and returns a dict describing
    what structure was found.  Supports all common formats:

    Format A — Roboflow YOLOv8 export (most common):
        root/
          train/
            images/  *.jpg
            labels/  *.txt
          valid/
            images/
            labels/
          test/          (optional)
          data.yaml

    Format B — flat split folders:
        root/
          images/
            train/  valid/  test/
          labels/
            train/  valid/  test/

    Format C — single flat folder:
        root/
          *.jpg  *.txt  (images and labels mixed)

    Format D — nested single class folder:
        root/
          weapon/  *.jpg
          (no labels — classification only, needs conversion)
    """
    print(f"\n{'='*60}")
    print(f"🔍 STEP 2 — Inspecting dataset structure")
    print(f"{'='*60}")
    print(f"   Root: {root}")

    # Print full tree (2 levels)
    for item in sorted(root.rglob("*")):
        depth = len(item.relative_to(root).parts)
        if depth <= 3:
            indent = "   " + "  " * (depth - 1)
            icon   = "📁" if item.is_dir() else "📄"
            print(f"{indent}{icon} {item.name}")

    # Count files by type
    all_files = list(root.rglob("*"))
    images    = [f for f in all_files if f.suffix.lower() in {".jpg",".jpeg",".png",".bmp",".webp"}]
    labels    = [f for f in all_files if f.suffix.lower() == ".txt"
                 and f.name != "classes.txt" and "label" in str(f).lower()]
    txts      = [f for f in all_files if f.suffix.lower() == ".txt"]
    yamls     = [f for f in all_files if f.suffix.lower() in {".yaml",".yml"}]

    print(f"\n   Summary:")
    print(f"   🖼  Images  : {len(images)}")
    print(f"   🏷  Labels  : {len(labels)}")
    print(f"   📄 TXT files: {len(txts)}")
    print(f"   📋 YAML files: {len(yamls)}")

    if yamls:
        print(f"\n   Found YAML files:")
        for y in yamls:
            print(f"     {y.relative_to(root)}")

    info = {
        "root":    root,
        "images":  images,
        "labels":  labels,
        "yamls":   yamls,
        "all":     all_files,
    }
    return info


# ═══════════════════════════════════════════════════════════════
# STEP 3 — DETECT / FIX STRUCTURE → produce standard layout
# ═══════════════════════════════════════════════════════════════
def normalise_structure(info: dict, dest: Path) -> dict:
    """
    Detects which format the dataset is in and converts it
    to the standard Roboflow/YOLOv8 layout:

        dest/
          train/images/  train/labels/
          valid/images/  valid/labels/
          data.yaml

    Returns dict with paths to train/valid splits.
    """
    print(f"\n{'='*60}")
    print(f"🔧 STEP 3 — Normalising dataset structure")
    print(f"{'='*60}")

    root = info["root"]

    # ── Check if data.yaml already exists ────────────────────
    yaml_path = None
    for y in info["yamls"]:
        if y.name in ("data.yaml", "dataset.yaml"):
            yaml_path = y
            break

    if yaml_path:
        print(f"   ✅ Found existing data.yaml: {yaml_path.relative_to(root)}")
        return _validate_yaml_paths(yaml_path, root, dest)

    # ── Detect Format A: train/ valid/ folders ────────────────
    train_img = root / "train" / "images"
    valid_img  = root / "valid" / "images"
    val_img    = root / "val"   / "images"

    if train_img.exists():
        v_dir = valid_img if valid_img.exists() else (val_img if val_img.exists() else None)
        print(f"   ✅ Format A detected (train/valid split folders)")
        return _build_yaml(root, root / "train", v_dir or root / "valid", dest)

    # ── Detect Format B: images/train, labels/train ───────────
    img_train = root / "images" / "train"
    lbl_train = root / "labels" / "train"
    if img_train.exists() and lbl_train.exists():
        print(f"   ✅ Format B detected (images/labels split folders)")
        # Restructure to Format A
        _restructure_B_to_A(root, dest)
        return _build_yaml(dest, dest / "train", dest / "valid", dest)

    # ── Detect Format C: flat folder ──────────────────────────
    flat_images = list(root.glob("*.jpg")) + list(root.glob("*.png"))
    flat_txts   = list(root.glob("*.txt"))
    if flat_images and flat_txts:
        print(f"   ✅ Format C detected (flat folder with {len(flat_images)} images)")
        _split_flat(root, dest)
        return _build_yaml(dest, dest / "train", dest / "valid", dest)

    # ── Search recursively for any images/labels pair ─────────
    print(f"   🔍 Non-standard structure — searching recursively...")
    all_imgs = list(root.rglob("*.jpg")) + list(root.rglob("*.png"))
    all_lbls = list(root.rglob("*.txt"))
    all_lbls = [f for f in all_lbls if f.name != "classes.txt"]

    if all_imgs and all_lbls:
        print(f"   Found {len(all_imgs)} images and {len(all_lbls)} labels recursively")
        print(f"   Collecting into a flat structure and splitting 80/20...")
        _collect_and_split(all_imgs, all_lbls, dest)
        return _build_yaml(dest, dest / "train", dest / "valid", dest)

    print("❌ Could not detect dataset structure.")
    print("   Expected one of:")
    print("   • Roboflow YOLOv8 export (train/valid/test + data.yaml)")
    print("   • images/train + labels/train folders")
    print("   • Flat folder with .jpg and .txt files")
    sys.exit(1)


def _validate_yaml_paths(yaml_path: Path, root: Path, dest: Path) -> dict:
    """Read existing yaml and fix any absolute paths inside it."""
    import yaml as _yaml   # PyYAML — installed with ultralytics

    with open(yaml_path, "r") as f:
        cfg = _yaml.safe_load(f)

    print(f"   Classes: {cfg.get('names', 'unknown')}")
    print(f"   nc     : {cfg.get('nc', '?')}")

    # Fix paths to be relative to yaml location
    for key in ("train", "val", "test"):
        if key in cfg:
            p = Path(cfg[key])
            if not p.is_absolute():
                abs_p = (yaml_path.parent / p).resolve()
                cfg[key] = str(abs_p)
                print(f"   Resolved {key}: {abs_p}")

    # Rewrite yaml with fixed paths
    fixed_yaml = dest / "data.yaml" if dest != root else yaml_path
    fixed_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(fixed_yaml, "w") as f:
        _yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    print(f"   ✅ data.yaml ready: {fixed_yaml}")
    return {"yaml": fixed_yaml, "names": cfg.get("names", []), "nc": cfg.get("nc", 1)}


def _build_yaml(root: Path, train_dir: Path, valid_dir: Path, dest: Path) -> dict:
    """Read classes.txt or auto-detect class names, write data.yaml."""
    import yaml as _yaml

    # Try to find class names
    classes_txt = root / "classes.txt"
    yaml_names  = None

    if classes_txt.exists():
        names = [l.strip() for l in classes_txt.read_text().splitlines() if l.strip()]
        print(f"   Found classes.txt: {names}")
        yaml_names = names
    else:
        # Try to infer from label files: each label line starts with class_id
        # Find max class id and use generic names
        max_id = 0
        lbl_files = list(train_dir.rglob("*.txt")) if train_dir.exists() else []
        for lf in lbl_files[:50]:   # sample first 50
            try:
                for line in lf.read_text().splitlines():
                    parts = line.strip().split()
                    if parts:
                        max_id = max(max_id, int(parts[0]))
            except Exception:
                pass
        if max_id == 0:
            yaml_names = ["weapon"]
        else:
            yaml_names = [f"class_{i}" for i in range(max_id + 1)]
        print(f"   Auto-detected {len(yaml_names)} classes: {yaml_names}")

    nc       = len(yaml_names)
    yaml_out = dest / "data.yaml"
    yaml_out.parent.mkdir(parents=True, exist_ok=True)

    cfg = {
        "path":  str(dest.resolve()),
        "train": str((train_dir / "images").resolve()),
        "val":   str(((valid_dir / "images") if valid_dir else (train_dir / "images")).resolve()),
        "nc":    nc,
        "names": yaml_names,
    }

    with open(yaml_out, "w") as f:
        _yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)

    print(f"   ✅ data.yaml written: {yaml_out}")
    print(f"   nc    : {nc}")
    print(f"   names : {yaml_names}")
    return {"yaml": yaml_out, "names": yaml_names, "nc": nc}


def _restructure_B_to_A(root: Path, dest: Path):
    """Convert images/train + labels/train → train/images + train/labels."""
    for split in ["train", "valid", "val", "test"]:
        src_img = root / "images" / split
        src_lbl = root / "labels" / split
        if src_img.exists():
            dst_img = dest / split / "images"
            dst_lbl = dest / split / "labels"
            dst_img.mkdir(parents=True, exist_ok=True)
            dst_lbl.mkdir(parents=True, exist_ok=True)
            for f in src_img.iterdir():
                shutil.copy2(f, dst_img / f.name)
            if src_lbl.exists():
                for f in src_lbl.iterdir():
                    shutil.copy2(f, dst_lbl / f.name)
    print(f"   ✅ Restructured to train/valid split format")


def _split_flat(root: Path, dest: Path, train_ratio: float = 0.8):
    """Split a flat folder of images+labels into train/valid."""
    import random
    images = sorted(list(root.glob("*.jpg")) + list(root.glob("*.png")) + list(root.glob("*.jpeg")))
    random.seed(42)
    random.shuffle(images)
    split  = int(len(images) * train_ratio)
    splits = {"train": images[:split], "valid": images[split:]}

    for sname, imgs in splits.items():
        (dest / sname / "images").mkdir(parents=True, exist_ok=True)
        (dest / sname / "labels").mkdir(parents=True, exist_ok=True)
        for img in imgs:
            shutil.copy2(img, dest / sname / "images" / img.name)
            lbl = img.with_suffix(".txt")
            if lbl.exists():
                shutil.copy2(lbl, dest / sname / "labels" / lbl.name)

    print(f"   ✅ Split: {len(splits['train'])} train, {len(splits['valid'])} valid")


def _collect_and_split(all_imgs, all_lbls, dest: Path, train_ratio: float = 0.8):
    """Collect images from anywhere in the tree, match labels by stem, split."""
    import random

    # Build stem → label path map
    lbl_map = {f.stem: f for f in all_lbls}

    paired   = [(img, lbl_map[img.stem]) for img in all_imgs if img.stem in lbl_map]
    unpaired = [img for img in all_imgs  if img.stem not in lbl_map]

    print(f"   Paired  (image+label): {len(paired)}")
    print(f"   Unpaired (image only): {len(unpaired)}")

    if not paired:
        print("⚠️  No image-label pairs found. Check that .txt label files exist.")
        print("    Using all images with no labels (may cause poor training results).")
        paired = [(img, None) for img in all_imgs]

    random.seed(42)
    random.shuffle(paired)
    split = int(len(paired) * train_ratio)

    for sname, subset in [("train", paired[:split]), ("valid", paired[split:])]:
        (dest / sname / "images").mkdir(parents=True, exist_ok=True)
        (dest / sname / "labels").mkdir(parents=True, exist_ok=True)
        for img, lbl in subset:
            shutil.copy2(img, dest / sname / "images" / img.name)
            if lbl:
                shutil.copy2(lbl, dest / sname / "labels" / lbl.name)

    print(f"   ✅ Collected + split: {split} train / {len(paired)-split} valid")


# ═══════════════════════════════════════════════════════════════
# STEP 4 — VALIDATE LABEL FORMAT
# ═══════════════════════════════════════════════════════════════
def validate_labels(yaml_info: dict):
    """
    Spot-check a sample of label files.
    YOLOv8 format: each line = "class_id cx cy w h"
    All values normalised 0–1.
    """
    print(f"\n{'='*60}")
    print(f"✅ STEP 4 — Validating label format (sample check)")
    print(f"{'='*60}")

    yaml_path = yaml_info["yaml"]
    data_dir  = yaml_path.parent

    issues   = 0
    checked  = 0
    lbl_files = list(data_dir.rglob("labels/**/*.txt"))

    if not lbl_files:
        print("   ⚠️  No label files found for validation.")
        return

    sample = lbl_files[:min(30, len(lbl_files))]

    for lf in sample:
        try:
            lines = lf.read_text().strip().splitlines()
            for i, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) != 5:
                    print(f"   ❌ {lf.name} line {i+1}: expected 5 values, got {len(parts)}: {line}")
                    issues += 1
                    continue
                cls_id = int(parts[0])
                vals   = [float(v) for v in parts[1:]]
                if any(v < 0 or v > 1 for v in vals):
                    print(f"   ❌ {lf.name} line {i+1}: bbox values out of 0-1 range: {vals}")
                    issues += 1
                if cls_id >= yaml_info.get("nc", 999):
                    print(f"   ❌ {lf.name} line {i+1}: class_id {cls_id} >= nc {yaml_info.get('nc')}")
                    issues += 1
            checked += 1
        except Exception as e:
            print(f"   ⚠️  Could not parse {lf.name}: {e}")

    if issues == 0:
        print(f"   ✅ Checked {checked} label files — all valid")
    else:
        print(f"   ⚠️  Found {issues} issues in {checked} label files")
        print(f"      Training can still proceed but accuracy may be affected.")


# ═══════════════════════════════════════════════════════════════
# STEP 5 — TRAIN
# ═══════════════════════════════════════════════════════════════
def train_model(yaml_info: dict, args) -> Path:
    print(f"\n{'='*60}")
    print(f"🚀 STEP 5 — Training YOLOv8 weapon detection model")
    print(f"{'='*60}")
    print(f"   Base model : {args.model}")
    print(f"   Epochs     : {args.epochs}")
    print(f"   Image size : {args.imgsz}px")
    print(f"   Batch size : {args.batch}")
    print(f"   Classes    : {yaml_info.get('names', [])}")
    print(f"   nc         : {yaml_info.get('nc', '?')}")

    try:
        from ultralytics import YOLO
    except ImportError:
        print("❌ ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)

    model     = YOLO(args.model)
    yaml_path = str(yaml_info["yaml"])

    device = args.device if args.device else ("0" if _has_gpu() else "cpu")
    print(f"   Device     : {device}")

    results = model.train(
        data       = yaml_path,
        epochs     = args.epochs,
        imgsz      = args.imgsz,
        batch      = args.batch,
        device     = device,
        name       = "sakti_weapon_detector",
        project    = "runs/detect",
        patience   = 20,           # early stopping if no improvement for 20 epochs
        save       = True,
        plots      = True,
        verbose    = True,
        exist_ok   = True,
    )

    # Find best.pt
    run_dir  = Path("runs") / "detect" / "sakti_weapon_detector"
    best_pt  = run_dir / "weights" / "best.pt"
    last_pt  = run_dir / "weights" / "last.pt"

    if best_pt.exists():
        print(f"\n   ✅ Training complete!")
        print(f"   Best weights: {best_pt}")
        return best_pt
    elif last_pt.exists():
        print(f"   ⚠️  best.pt not found — using last.pt")
        return last_pt
    else:
        print(f"   ❌ Could not find trained weights in {run_dir}")
        sys.exit(1)


def _has_gpu() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# STEP 6 — VALIDATE TRAINED MODEL
# ═══════════════════════════════════════════════════════════════
def validate_model(best_pt: Path, yaml_info: dict):
    print(f"\n{'='*60}")
    print(f"📊 STEP 6 — Validating trained model")
    print(f"{'='*60}")

    try:
        from ultralytics import YOLO
        model   = YOLO(str(best_pt))
        metrics = model.val(data=str(yaml_info["yaml"]), verbose=False)

        print(f"   mAP50       : {metrics.box.map50:.4f}   (higher = better, aim for >0.5)")
        print(f"   mAP50-95    : {metrics.box.map:.4f}")
        print(f"   Precision   : {metrics.box.mp:.4f}")
        print(f"   Recall      : {metrics.box.mr:.4f}")

        if metrics.box.map50 < 0.3:
            print("\n   ⚠️  mAP50 is low (<0.3). Suggestions:")
            print("      • Train for more epochs (--epochs 100)")
            print("      • Use a larger model (--model yolov8s.pt)")
            print("      • Add more training images (500+ per class recommended)")
            print("      • Check that labels are correct (run --validate-only)")
        elif metrics.box.map50 > 0.7:
            print("\n   🎉 Excellent mAP50 (>0.7) — model is production ready!")
        else:
            print("\n   ✅ Acceptable accuracy. Consider more epochs for improvement.")

    except Exception as e:
        print(f"   ⚠️  Validation error: {e}")
        print(f"      This is non-critical — model file is still usable.")


# ═══════════════════════════════════════════════════════════════
# STEP 7 — COPY TO PROJECT ROOT AS best_weapon.pt
# ═══════════════════════════════════════════════════════════════
def deploy_model(best_pt: Path, output_name: str):
    print(f"\n{'='*60}")
    print(f"📦 STEP 7 — Deploying model to project")
    print(f"{'='*60}")

    output = Path(output_name)
    shutil.copy2(best_pt, output)
    size_mb = output.stat().st_size / (1024 * 1024)

    print(f"   ✅ Model copied: {output}  ({size_mb:.1f} MB)")
    print(f"\n   Your app.py will automatically use this model.")
    print(f"   It looks for '{output_name}' in the same folder as app.py.")
    print(f"   No changes needed in app.py — restart Flask to activate.")


# ═══════════════════════════════════════════════════════════════
# STEP 8 — TEST INFERENCE (optional)
# ═══════════════════════════════════════════════════════════════
def test_inference(model_path: str, image_path: str, names: list):
    print(f"\n{'='*60}")
    print(f"🎯 STEP 8 — Test inference on: {image_path}")
    print(f"{'='*60}")

    if not Path(image_path).exists():
        print(f"   ⚠️  Test image not found: {image_path}")
        return

    try:
        from ultralytics import YOLO
        model   = YOLO(model_path)
        results = model(image_path, conf=0.25)

        for r in results:
            if not r.boxes or len(r.boxes) == 0:
                print("   No weapons detected in test image.")
            else:
                print(f"   Detections ({len(r.boxes)}):")
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf   = float(box.conf[0])
                    label  = names[cls_id] if cls_id < len(names) else f"class_{cls_id}"
                    xyxy   = [round(float(v), 1) for v in box.xyxy[0]]
                    print(f"     🔫 {label.upper()}  conf={conf:.2f}  bbox={xyxy}")

        # Save annotated result
        out_path = Path("test_result.jpg")
        results[0].save(str(out_path))
        print(f"   ✅ Annotated image saved: {out_path}")

    except Exception as e:
        print(f"   ⚠️  Inference test failed: {e}")


# ═══════════════════════════════════════════════════════════════
# PRINT FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════
def print_summary(output: str, yaml_info: dict):
    names = yaml_info.get("names", [])
    nc    = yaml_info.get("nc", "?")
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║   ✅  TRAINING COMPLETE — SAKTI AI WEAPON DETECTOR          ║
╠══════════════════════════════════════════════════════════════╣
║  Model file  : {output:<44} ║
║  Classes     : {str(nc):<44} ║
║  Labels      : {str(names[:4])[1:-1]:<44} ║
╠══════════════════════════════════════════════════════════════╣
║  NEXT STEPS:                                                 ║
║  1. Copy {output:<20} to your project folder      ║
║     (same folder as app.py)                                  ║
║  2. Restart Flask:  python app.py                            ║
║  3. The camera will now detect: {str(names[:3])[1:-1]:<27}║
║                                                              ║
║  To improve accuracy:                                        ║
║  • Run with --epochs 100 --model yolov8s.pt                  ║
║  • Add more images (500+ per class ideal)                    ║
║  • Check runs/detect/sakti_weapon_detector/ for plots        ║
╚══════════════════════════════════════════════════════════════╝
""")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    args = parse_args()

    print("""
╔══════════════════════════════════════════════════════════════╗
║   SAKTI AI — Weapon Detection Training Pipeline              ║
╚══════════════════════════════════════════════════════════════╝""")

    # Check ultralytics installed
    try:
        import ultralytics
        print(f"\n✅ ultralytics {ultralytics.__version__} found")
    except ImportError:
        print("\n❌ ultralytics not installed.")
        print("   Run: pip install ultralytics")
        sys.exit(1)

    dest = Path(args.data)

    # Step 1 — Extract zip if provided
    if args.zip:
        dest = extract_zip(args.zip, dest)
    elif not dest.exists():
        print(f"❌ Dataset folder not found: {dest}")
        print(f"   Provide --zip path/to/dataset.zip  OR  --data path/to/folder")
        sys.exit(1)

    # Step 2 — Inspect
    info = inspect_dataset(dest)

    # Step 3 — Normalise to standard layout
    yaml_info = normalise_structure(info, dest)

    # Step 4 — Validate labels
    validate_labels(yaml_info)

    # Step 5 — Train
    best_pt = train_model(yaml_info, args)

    # Step 6 — Validate metrics
    validate_model(best_pt, yaml_info)

    # Step 7 — Deploy
    deploy_model(best_pt, args.output)

    # Step 8 — Test inference (optional)
    if args.test_image:
        test_inference(args.output, args.test_image, yaml_info.get("names", []))

    # Summary
    print_summary(args.output, yaml_info)


if __name__ == "__main__":
    main()
