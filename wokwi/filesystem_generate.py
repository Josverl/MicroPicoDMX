import os
from pathlib import Path

from littlefs import LittleFS

# import subprocess

# workspace is one level above this file
workspace_dir = Path(__file__).parent.parent.absolute()


output_image = f"{workspace_dir}/littlefs.img"

fs = LittleFS(block_size=4096, block_count=512, prog_size=256)

# files = os.listdir(f"{workspace_dir}/src")
for filename in Path(f"{workspace_dir}/src").glob("*"):
    if filename.is_file():
        with open(filename, "rb") as src_file:
            # use the relative path to source as the littlefs filename
            lfs_fname = filename.relative_to(f"{workspace_dir}/src").as_posix()
            print(f"Adding {filename} to image as {lfs_fname}")
            with fs.open(lfs_fname, "wb") as lfs_file:
                lfs_file.write(src_file.read())

fs.fs_mkconsistent()

with open(output_image, "wb") as fh:
    fh.write(fs.context.buffer)
