import os
import shutil
import hashlib
from tkinter import (
    Tk, filedialog, Label, Button, Text, END, ttk,
    messagebox, StringVar, BooleanVar, Checkbutton, Entry
)
from pathlib import Path
import threading

# --------- File Comparison Functions --------- #
def get_file_hash(file_path):
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def list_files(folder):
    file_dict = {}
    for root, _, files in os.walk(folder):
        for file in files:
            abs_path = Path(root) / file
            rel_path = abs_path.relative_to(folder)
            file_dict[str(rel_path)] = abs_path
    return file_dict

def get_sync_actions(folder1, folder2, use_hash=False):
    files1 = list_files(folder1)
    files2 = list_files(folder2)
    all_keys = set(files1.keys()).union(files2.keys())

    actions = []

    for rel_path in all_keys:
        f1 = files1.get(rel_path)
        f2 = files2.get(rel_path)

        if f1 and not f2:
            actions.append(("copy", f1, Path(folder2) / rel_path))
        elif f2 and not f1:
            actions.append(("copy", f2, Path(folder1) / rel_path))
        elif f1 and f2:
            if use_hash:
                h1 = get_file_hash(f1)
                h2 = get_file_hash(f2)
                if h1 != h2:
                    actions.append(("update", f1, f2))
                    actions.append(("update", f2, f1))
            else:
                if f1.stat().st_mtime > f2.stat().st_mtime:
                    actions.append(("update", f1, f2))
                elif f2.stat().st_mtime > f1.stat().st_mtime:
                    actions.append(("update", f2, f1))
    return actions

def backup_and_copy(src, dst):
    dst = Path(dst)
    if dst.exists():
        backup_folder = dst.parent / ".backup"
        backup_folder.mkdir(exist_ok=True)
        shutil.move(str(dst), str(backup_folder / (dst.name + ".bak")))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))

# --------- GUI Functions --------- #
def browse_folder(var):
    path = filedialog.askdirectory()
    if path:
        var.set(path)

def sync_folders(actions, progress_bar, log_area):
    total = len(actions)
    for i, (action, src, dst) in enumerate(actions):
        backup_and_copy(src, dst)
        log_area.insert(END, f"{action.upper()}: {src} -> {dst}\n")
        progress_bar["value"] = ((i + 1) / total) * 100
        root.update_idletasks()
    messagebox.showinfo("Done", "Synchronization complete!")

def start_sync():
    folder1 = folder1_path.get()
    folder2 = folder2_path.get()

    if not folder1 or not folder2:
        messagebox.showwarning("Missing folders", "Please select both folders.")
        return

    if not Path(folder1).is_dir() or not Path(folder2).is_dir():
        messagebox.showerror("Invalid paths", f"One or both paths are invalid:\n{folder1}\n{folder2}")
        return

    actions = get_sync_actions(folder1, folder2, use_hash.get())
    log_area.delete("1.0", END)

    if not actions:
        log_area.insert(END, "✅ Folders are already in sync.\n")
        return

    log_area.insert(END, "📝 Planned Actions:\n")
    for act, src, dst in actions:
        log_area.insert(END, f"{act.upper()}: {src} -> {dst}\n")

    confirm = messagebox.askyesno("Confirm", "Proceed with synchronization?")
    if confirm:
        threading.Thread(target=sync_folders, args=(actions, progress_bar, log_area)).start()

# --------- GUI Setup --------- #
root = Tk()
root.title("Dev's Robust Folder Comparison and Sync Tool")
root.geometry("780x600")

folder1_path = StringVar()
folder2_path = StringVar()
use_hash = BooleanVar()

Label(root, text="📁 Select Folder 1:").pack()
entry1 = Entry(root, textvariable=folder1_path, width=90)
entry1.pack()
Button(root, text="Browse", command=lambda: browse_folder(folder1_path)).pack(pady=(0, 10))

Label(root, text="📁 Select Folder 2:").pack()
entry2 = Entry(root, textvariable=folder2_path, width=90)
entry2.pack()
Button(root, text="Browse", command=lambda: browse_folder(folder2_path)).pack(pady=(0, 10))

Checkbutton(root, text="Use SHA256 hash (slower but more accurate)", variable=use_hash).pack(pady=5)

Button(root, text="🔄 Compare and Sync", command=start_sync).pack(pady=5)

progress_bar = ttk.Progressbar(root, orient="horizontal", length=700, mode="determinate")
progress_bar.pack(pady=10)

log_area = Text(root, height=20, width=100)
log_area.pack(pady=5)

root.mainloop()

