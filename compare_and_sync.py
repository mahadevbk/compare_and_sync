import streamlit as st
import os
import zipfile
import shutil
from pathlib import Path
import hashlib
from datetime import datetime

st.set_page_config(page_title="Dev's Folder Sync Tool", layout="wide")
st.title("🛠️ Dev's Robust Folder Comparison and Sync Tool")

# Compatibility info
with st.expander("📦 Click to view compatibility table"):
    st.markdown("""
    | OS / File System     | Supported? | Notes |
    |----------------------|------------|-------|
    | **Windows (NTFS)**   | ✅ Yes     | Fully supported |
    | **macOS (APFS)**     | ✅ Yes     | Fully supported |
    | **Linux (ext4)**     | ✅ Yes     | Fully supported |
    | **Network Drives**   | ⚠️ Partial | May have permission issues or latency |
    | **FAT32/ExFAT**      | ⚠️ Partial | May lose timestamp precision |
    | **Cloud Drives**     | ⚠️ Partial | Dropbox/OneDrive may delay sync |
    """)

# Drag and drop file upload
st.sidebar.markdown("### 📁 Drag and Drop Files to Compare")
folder1_files = st.sidebar.file_uploader("Drag files from Folder 1", type="*.*", accept_multiple_files=True)
folder2_files = st.sidebar.file_uploader("Drag files from Folder 2", type="*.*", accept_multiple_files=True)
use_hash = st.sidebar.checkbox("🔍 Use SHA256 comparison (more precise but slower)", value=False)

def get_folder_from_file(files):
    """Extract folder path from the uploaded files."""
    if files:
        # Extract folder path based on the relative file path
        file_paths = [Path(f.name) for f in files]
        common_parent = os.path.commonpath([str(f) for f in file_paths])
        return Path(common_parent)
    return None

def list_files_from_uploaded(files, folder):
    """List files in the folder based on the uploaded files."""
    if folder:
        files_dict = {}
        for file in files:
            file_path = Path(file.name)
            relative_path = file_path.relative_to(folder)
            files_dict[str(relative_path)] = file
        return files_dict
    return {}

def get_file_hash(file):
    try:
        hash_sha256 = hashlib.sha256()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        st.warning(f"⚠️ Hashing failed for {file}: {e}")
        return None

def get_actions(folder1, folder2, use_hash=False):
    # List files based on uploaded files and inferred folder paths
    files1 = list_files_from_uploaded(folder1_files, folder1)
    files2 = list_files_from_uploaded(folder2_files, folder2)
    all_keys = set(files1.keys()).union(files2.keys())

    actions = []

    for rel_path in all_keys:
        f1_file = files1.get(rel_path)
        f2_file = files2.get(rel_path)

        if f1_file and not f2_file:
            actions.append(("copy", f1_file, folder2 / rel_path))
        elif f2_file and not f1_file:
            actions.append(("copy", f2_file, folder1 / rel_path))
        elif f1_file and f2_file:
            if use_hash:
                hash1 = get_file_hash(f1_file)
                hash2 = get_file_hash(f2_file)
                if hash1 and hash2 and hash1 != hash2:
                    actions.append(("update", f1_file, folder2 / rel_path))
                    actions.append(("update", f2_file, folder1 / rel_path))
            else:
                f1_mtime = f1_file.stat().st_mtime
                f2_mtime = f2_file.stat().st_mtime
                if f1_mtime > f2_mtime:
                    actions.append(("update", f1_file, folder2 / rel_path))
                elif f2_mtime > f1_mtime:
                    actions.append(("update", f2_file, folder1 / rel_path))
    return actions

def show_summary(actions):
    st.subheader("📝 Planned Actions")
    for action, src, dst in actions:
        if action == "copy":
            st.write(f"📁 **Copy** `{src}` → `{dst}`")
        elif action == "update":
            st.write(f"🔄 **Update** `{dst}` ← `{src}` (with backup)")

def perform_sync(actions, folder1, folder2):
    progress = st.progress(0)
    total = len(actions)
    for i, (action, src, dst) in enumerate(actions):
        copy_with_backup(src, dst, folder1, folder2)
        progress.progress((i + 1) / total)
    st.success("✅ Sync complete!")

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

        log_action(folder1, "sync", src, dst)
        log_action(folder2, "sync", src, dst)

    except PermissionError:
        st.error(f"❌ Permission denied: {src} or {dst}")
    except Exception as e:
        st.error(f"❌ Failed to copy {src} to {dst}: {e}")

# Main execution
if folder1_files and folder2_files:
    folder1 = get_folder_from_file(folder1_files)
    folder2 = get_folder_from_file(folder2_files)

    st.write(f"📂 Folder 1: `{folder1}`")
    st.write(f"📂 Folder 2: `{folder2}`")

    actions = get_actions(folder1, folder2, use_hash)
    if actions:
        show_summary(actions)
        if st.button("✅ Confirm and Start Sync"):
            perform_sync(actions, folder1, folder2)
    else:
        st.info("✅ Folders are already in sync.")
else:
    st.info("👈 Please drag and drop files from both folders to begin.")
