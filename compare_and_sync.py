import streamlit as st
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Robust Folder Sync Tool", layout="wide")
st.title("🔐 Robust Folder Comparison and Sync Tool")

st.markdown("""
### 📦 Compatibility Table

| OS / File System     | Supported? | Notes |
|----------------------|------------|-------|
| **Windows (NTFS)**   | ✅ Yes     | Fully supported |
| **macOS (APFS)**     | ✅ Yes     | Fully supported |
| **Linux (ext4)**     | ✅ Yes     | Fully supported |
| **Network Drives**   | ⚠️ Partial | May have permission issues or latency |
| **FAT32/ExFAT**      | ⚠️ Partial | May lose timestamp precision |
| **Cloud Drives**     | ⚠️ Partial | Dropbox/OneDrive may delay sync |
""")

folder1 = st.sidebar.text_input("📁 Folder 1 Path")
folder2 = st.sidebar.text_input("📁 Folder 2 Path")
use_hash = st.sidebar.checkbox("🔍 Use SHA256 comparison (more precise but slower)", value=False)

def list_files(folder):
    return {str(f.relative_to(folder)): f for f in Path(folder).rglob("*") if f.is_file()}

def get_file_hash(file_path):
    try:
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        st.warning(f"⚠️ Hashing failed for {file_path}: {e}")
        return None

def get_actions(f1, f2, use_hash=False):
    f1 = Path(f1)
    f2 = Path(f2)
    files1 = list_files(f1)
    files2 = list_files(f2)
    all_keys = set(files1.keys()).union(files2.keys())

    actions = []

    for rel_path in all_keys:
        f1_file = files1.get(rel_path)
        f2_file = files2.get(rel_path)

        if f1_file and not f2_file:
            actions.append(("copy", f1_file, f2 / rel_path))
        elif f2_file and not f1_file:
            actions.append(("copy", f2_file, f1 / rel_path))
        elif f1_file and f2_file:
            if use_hash:
                hash1 = get_file_hash(f1_file)
                hash2 = get_file_hash(f2_file)
                if hash1 and hash2 and hash1 != hash2:
                    actions.append(("update", f1_file, f2 / rel_path))
                    actions.append(("update", f2_file, f1 / rel_path))
            else:
                f1_mtime = f1_file.stat().st_mtime
                f2_mtime = f2_file.stat().st_mtime
                if f1_mtime > f2_mtime:
                    actions.append(("update", f1_file, f2 / rel_path))
                elif f2_mtime > f1_mtime:
                    actions.append(("update", f2_file, f1 / rel_path))
    return actions

def log_action(folder, action, src, dst):
    log_path = Path(folder) / "sync_log.txt"
    with open(log_path, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {action.upper()} | {src} -> {dst}\n")

def show_summary(actions):
    st.subheader("📝 Planned Actions")
    for action, src, dst in actions:
        if action == "copy":
            st.write(f"📁 **Copy** `{src}` → `{dst}`")
        elif action == "update":
            st.write(f"🔄 **Update** `{dst}` ← `{src}` (with backup)")

def copy_with_backup(src, dst, folder1, folder2):
    try:
        dst = Path(dst)
        backup_folder = dst.parent / ".backup"
        backup_folder.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            backup_path = backup_folder / (dst.name + ".bak")
            shutil.move(str(dst), str(backup_path))

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))

        # Log to both folders
        log_action(folder1, "sync", src, dst)
        log_action(folder2, "sync", src, dst)

    except PermissionError:
        st.error(f"❌ Permission denied: {src} or {dst}")
    except Exception as e:
        st.error(f"❌ Failed to copy {src} to {dst}: {e}")

def perform_sync(actions, folder1, folder2):
    progress = st.progress(0)
    total = len(actions)
    for i, (action, src, dst) in enumerate(actions):
        copy_with_backup(src, dst, folder1, folder2)
        progress.progress((i + 1) / total)
    st.success("✅ Sync complete!")

# Main logic
if folder1 and folder2 and Path(folder1).is_dir() and Path(folder2).is_dir():
    actions = get_actions(folder1, folder2, use_hash)
    if actions:
        show_summary(actions)
        if st.button("✅ Confirm and Start Sync"):
            perform_sync(actions, folder1, folder2)
    else:
        st.info("✅ Folders are already in sync.")
else:
    st.warning("Please provide valid paths for both folders.")

