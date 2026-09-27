"""
********************************************************************************
* SPDX-License-Identifier: MIT
* SPDX-FileType: OTHER
* SPDX-FileCopyrightText: (c) 2024, OpenGateware authors and contributors
********************************************************************************
*
* Packaging Workflow
* Copyright (c) 2024, Marcus Andrade <marcus@opengateware.org>
*
* Permission is hereby granted, free of charge, to any person obtaining a copy
* of this software and associated documentation files (the "Software"), to deal
* in the Software without restriction, including without limitation the rights
* to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
* copies of the Software, and to permit persons to whom the Software is
* furnished to do so, subject to the following conditions:
*
* The above copyright notice and this permission notice shall be included in
* all copies or substantial portions of the Software.
*
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
* SOFTWARE.
********************************************************************************
"""

import glob
import os
import shutil
import zipfile
import tarfile
from datetime import date


def create_folders(config):
    """
    Clears existing and creates new stage and release folders as specified in the config.

    Parameters:
    - config (dict): Configuration object containing folder paths.

    Side effects:
    - Removes existing stage and release folders if they exist.
    - Creates new stage and release folders.
    """
    folders = config["release"]["folders"]
    stage_folder = folders["stage_folder"]
    release_folder = folders["release_folder"]
    try:
        shutil.rmtree(stage_folder, ignore_errors=True)
        os.makedirs(stage_folder)

        shutil.rmtree(release_folder, ignore_errors=True)
        os.makedirs(release_folder)

    except IOError as e:
        print(f"An error occurred: {e}")


def copy_packaging_folder(config, subpath=None):
    """
    Copies the packaging folder structure to the staging area.

    Parameters:
    - config (dict): Configuration object containing source and destination folder paths.

    Side effects:
    - Copies files and directories from the package folder to the staging folder.
    """
    # target = os.getenv('TARGET')
    folders = config["release"]["folders"]
    source = f"{folders['pkg_folder']}"
    if subpath != None:
        source = os.path.join(source, subpath)
    destination = folders["stage_folder"]

    print("Copying Package Files...")
    print("From:", source, "To:", destination)
    if not os.path.exists(destination):
        os.makedirs(destination)

    for item in os.listdir(source):
        src_path = os.path.join(source, item)
        dest_path = os.path.join(destination, item)
        print(item)
        print(src_path)
        print(dest_path)

        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dest_path)


def clean_up_files(config):
    """
    Removes specific file types from the staging folder.

    Parameters:
    - config (dict): Configuration object containing the path to the staging folder.

    Side effects:
    - Deletes files matching specified patterns (e.g., "*.png", "*.rom", "*.gitkeep").
    """
    folders = config["release"]["folders"]
    stage_folder = folders["stage_folder"]

    print("Cleaning Up Files...")
    # Define patterns for unwanted files
    file_patterns = ["*.png", "*.rom", ".gitkeep"]

    for pattern in file_patterns:
        # Use glob to find all files matching the pattern
        for filename in glob.glob(
            os.path.join(stage_folder, "**", pattern), recursive=True
        ):
            print(f"Removing {filename}...")
            os.remove(filename)


def create_tar_gz(source_dir, output_filename):
    """
    Creates a .tar.gz archive from the specified directory.

    Parameters:
    - source_dir (str): Path to the directory to be archived.
    - output_filename (str): Path where the output .tar.gz file will be saved.
    """
    print(f"Packing contents of {source_dir} into {output_filename}...")
    try:
        with tarfile.open(output_filename, "w:gz") as tar:
            # Walk through everything inside source_dir
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    # Full path to the file
                    file_path = os.path.join(root, file)
                    # Relative path to the file inside source_dir
                    arcname = os.path.relpath(str(file_path), start=source_dir)
                    tar.add(str(file_path), arcname=arcname)
        print(f"Archive {output_filename} created successfully.")
    except Exception as e:
        print(f"An error occurred while creating the archive: {e}")


def create_zip_file(source_dir, output_filename):
    """
    Creates a .zip archive containing only the contents of the specified directory.

    Parameters:
    - source_dir (str): Path to the directory to be archived.
    - output_filename (str): Path where the output .zip file will be saved.
    """
    print(f"Packing contents of {source_dir} into {output_filename}...")
    try:
        with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Walk through everything inside source_dir
            for root, dirs, files in os.walk(source_dir):
                if not files and not dirs:
                    # Write empty folder
                    arcname = os.path.relpath(str(root), start=source_dir)
                    print(f"Ziping empty folder {root} as {arcname}")
                    zip_info = zipfile.ZipInfo(arcname)
                    zip_info.external_attr = 0o40755 << 16  # drwxr-xr-x permissions
                    zipf.writestr(str(arcname) + "/", b"")
                    continue

                for file in files:
                    # Full path to the file
                    file_path = os.path.join(root, file)
                    # Relative path to the file inside source_dir
                    arcname = os.path.relpath(str(file_path), start=source_dir)
                    print(f"Zipping file {file_path} as {arcname}")
                    zipf.write(str(file_path), str(arcname))
        print(f"Archive {output_filename} created successfully.")
    except Exception as e:
        print(f"An error occurred while creating the archive: {e}")


def create_release_package(config, target):
    """
    Creates a release package as a zip file based on configuration and target environment.

    Parameters:
    - config (dict): Configuration object containing release information and file paths.

    Returns:
    - str: The filename of the created release package.
    """
    print("Creating release package...")
    current_date = date.today().strftime("%Y-%m-%d")
    version = os.getenv("GITHUB_REF").split("/")[-1]
    release_folder = config["release"]["folders"]["release_folder"]

    if "release_file" in config["release"]["target"][target]:
        stage_folder = config["release"]["folders"]["stage_folder"]
        release_file = config["release"]["target"][target]["release_file"].format(
            author=f"{config['author']}",
            core=f"{config['name']}",
            version=f"{version}",
            date=f"{current_date}",
            target=f"{target}",
        )

        create_zip_file(
            stage_folder, os.path.join(release_folder, f"{release_file}.zip")
        )
        # create_tar_gz(stage_folder, os.path.join(release_folder, f"{release_file}.tar.gz"))

        return f"{release_file}.zip"
    else:
        print("No information found for the release file")


def create_metadata_package(config, target):
    """
    Creates a metadata package as a zip file based on configuration and target environment.

    Parameters:
    - config (dict): Configuration object containing metadata information and file paths.

    Returns:
    - str: The filename of the created metadata package.
    """
    print("Creating metadata package...")
    current_date = date.today().strftime("%Y%m%d")
    version = os.getenv("GITHUB_REF").split("/")[-1]
    release_folder = config["release"]["folders"]["release_folder"]

    if "metadata_file" in config["release"]["target"][target]:
        meta_folder = config["release"]["folders"]["meta_folder"]
        meta_file = (
            config["release"]["target"][target]["metadata_file"]
            .format(
                author=f"{config['author']}",
                core=f"{config['name']}",
                version=f"{version}",
                date=f"{current_date}",
            )
            .lower()
        )

        create_zip_file(meta_folder, os.path.join(release_folder, f"{meta_file}.zip"))
        # create_tar_gz(meta_folder, os.path.join(release_folder, f"{meta_file}.tar.gz"))
        return f"{meta_file}.zip"
    else:
        print(
            "No metadata file configuration found. Skipping metadata package creation."
        )
        return None


def reverse_bitstream(source, destination):
    """
    Reverses the bitstream of an RBF file specified in the configuration.

    Parameters:
    - config (dict): Configuration object containing the path to the source RBF file and the target output path.

    Side effects:
    - Generates a new RBF file with reversed bitstream.
    """
    print("Reversing Bitstream...")
    # target = os.getenv('TARGET')
    # source_rbf_file = f"{config['release']['folders']['output_folder']}/{config['name']}_{target}.rbf"
    # reverse_rbf_file = f"{config['release']['folders']['stage_folder']}/Cores/{config['author']}.{config['name']}/bitstream.rbf_r"
    # Reverse the bits in each byte
    table = bytes(int(f"{i:08b}"[::-1], 2) for i in range(256))
    try:
        # Read the input file
        with open(source, "rb") as file:
            data = file.read()

        # Write the reversed bytes to the output file
        with open(destination, "wb") as file:
            file.write(data.translate(table))

        print(f"Reversed {len(data)} bytes and saved to {destination}")

    except IOError as e:
        print(f"An error occurred: {e}")
