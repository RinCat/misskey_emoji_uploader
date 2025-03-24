#!/usr/bin/env python3

# Copyright (C) 2024  Rin Cat (鈴猫) <rincat@rincat.dev>
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Upload emojis to Misskey instance.

This Python script will upload emojis from a local file or directory to the
Misskey instance using the Misskey API.

## Emoji name

The file name will be used as the emoji name.

**Antything after the first "." in the file name will be ignored.**

The emoji name will be converted to lowercase and "-" will be replaced with "_".

Use non-alphanumeric characters as the emoji name is not recommended.
You will run into compatibility issues when using them.

## Requirements

Python 3.9+ is required to run this script.

Python "requests" library is required.

## User API Token

User needs to provide misskey instance URL and token as environment variables.

`MISSKEY_URL`: URL of the Misskey instance, e.g. `https://example.com`

`MISSKEY_TOKEN`: User token for the Misskey instance. Sometimg like
`UgBX0DQprCwKrqRTfqTaoADy3QnVhThz`

You can create the token from the Misskey settings page.
`https://example.com/settings/api`

Make sure the API token has the necessary permissions to upload emojis.
You will most likely need to be an admin to upload emojis.

The following permissions are required:

- Access your Drive files and folders
- Edit or delete your Drive files and folders
- Manage emoji
- View emoji

The files will be uploaded to the API token owner's Drive.

## Usage

Set the environment variable "MISSKEY_URL" and "MISSKEY_TOKEN" before running:

```bash
export MISSKEY_URL="https://example.com"
export MISSKEY_TOKEN="your_token_here"
./misskey_emoji_uploader.py /path/to/emojis
```

Check the help for more options:

```bash
./misskey_emoji_uploader.py --help
```

Contrct `@RinCat@pika.moe` on any ActivityPub if you have any questions.
"""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print('Please install the "requests" Python library.')  # noqa: T201
    sys.exit(1)

TIMEOUT = 10
RATE_LIMIT_WAIT = 60

MISSKEY_URL = os.environ.get("MISSKEY_URL", "")
MISSKEY_TOKEN = os.environ.get("MISSKEY_TOKEN", "")
MISSKEY_API = MISSKEY_URL + "/api"

logging.basicConfig(format="%(message)s", level=logging.INFO)
mimetypes.init()


def emojis_get_current_list() -> list[dict[str, Any]]:
    """Get all custom emojis on the Misskey instance.

    https://misskey.io/api-doc#tag/meta/operation/emojis
    """
    url = MISSKEY_API + "/emojis"

    logging.debug("Getting current emojis list from %s", url)

    response = requests.get(url, timeout=TIMEOUT)

    return json.loads(response.text)["emojis"]


def emoji_add(  # noqa: PLR0913
    emoji_name: str,
    file_id: str,
    category: str,
    license_: str,
    *,
    sensitive: bool,
    local_only: bool,
) -> dict[str, Any]:
    """Create a custom emoji on the Misskey instance.

    https://misskey.io/api-doc#tag/admin/operation/admin___emoji___add
    """
    url = MISSKEY_API + "/admin/emoji/add"

    logging.debug("Adding emoji %s with file id: %s", emoji_name, file_id)

    response = requests.post(
        url,
        json={
            "i": MISSKEY_TOKEN,
            "name": emoji_name,
            "fileId": file_id,
            "category": category,
            "license": license_,
            "isSensitive": sensitive,
            "localOnly": local_only,
        },
        timeout=TIMEOUT,
    )

    return json.loads(response.text)


def drive_get_folders(folder_id: str | None = None) -> list[dict[str, Any]]:
    """Get Drive folders list in the Misskey instance.

    https://misskey.io/api-doc#tag/drive/operation/drive___folders
    """
    url = MISSKEY_API + "/drive/folders"

    logging.debug("Getting drive folders list with folder id: %s", folder_id)

    response = requests.post(
        url,
        json={"i": MISSKEY_TOKEN, "folderId": folder_id},
        timeout=TIMEOUT,
    )

    return json.loads(response.text)


def drive_show_folders(folder_id: str | None) -> dict[str, Any]:
    """Show Drive folders list in Misskey instance.

    if folder_id is None, it will show the root folder.

    https://misskey.io/api-doc#tag/drive/operation/drive___folders___show
    """
    url = MISSKEY_API + "/drive/folders/show"

    logging.debug("Getting drive folder with folder id: %s", folder_id)

    response = requests.post(
        url,
        json={"i": MISSKEY_TOKEN, "folderId": folder_id},
        timeout=TIMEOUT,
    )

    return json.loads(response.text)


def create_drive_folder(name: str, parent_id: str | None = None) -> dict[str, Any]:
    """Create a folder in Drive in the Misskey instance.

    https://misskey.io/api-doc#tag/drive/operation/drive___folders___create
    """
    url = MISSKEY_API + "/drive/folders/create"

    logging.info("Creating folder %s with parent id: %s", name, parent_id)

    while True:
        response = requests.post(
            url,
            json={"i": MISSKEY_TOKEN, "name": name, "parentId": parent_id},
            timeout=TIMEOUT,
        )

        data = json.loads(response.text)

        if "error" in data:
            if data["error"]["code"] == "RATE_LIMIT_EXCEEDED":
                logging.warning(
                    "Rate limit exceeded. Waiting for %s seconds.",
                    RATE_LIMIT_WAIT,
                )
                time.sleep(RATE_LIMIT_WAIT)
            else:
                raise RuntimeError(data)
        else:
            break
    return data


def create_drive_folder_path(path: str) -> dict[str, Any]:
    """Create a series of folders in Drive in the Misskey instance.

    If the folder already exists, it will return the existing folder data.

    The path should be a string with folders separated by "/".
    e.g. "folder1/folder2/folder3"
    """
    path_split = path.split("/")
    parent_id = None
    folder_data = None

    for folder in path_split:
        folders = drive_get_folders(parent_id)
        folder_exists = False

        # Check if the folder already exists
        for f in folders:
            if f["name"] == folder:
                folder_exists = True
                parent_id = f["id"]
                break

        if not folder_exists:
            folder_data = create_drive_folder(folder, parent_id)
            parent_id = folder_data["id"]

    # Get the last folder data if it already exists
    if folder_data is None:
        folder_data = drive_show_folders(parent_id)

    return folder_data


def drive_upload_file(
    file_path: Path,
    folder_id: str | None,
    file_name: str,
) -> dict[str, Any]:
    """Upload a file to Drive in Misskey instance.

    https://misskey.io/api-doc#tag/drive/operation/drive___files___create
    """
    url = MISSKEY_API + "/drive/files/create"
    mime_type, _ = mimetypes.guess_type(file_name)

    if mime_type is None:
        mime_type = "application/octet-stream"

    logging.debug("Mime type of file %s is %s", file_name, mime_type)

    while True:
        logging.debug("Uploading file %s to folder id: %s", file_name, folder_id)

        with file_path.open("rb") as file:
            response = requests.post(
                url,
                files={"file": (file_name, file, mime_type)},
                data={"i": MISSKEY_TOKEN, "folderId": folder_id},
                timeout=TIMEOUT,
            )

        data = json.loads(response.text)

        if "error" in data:
            if data["error"]["code"] == "RATE_LIMIT_EXCEEDED":
                logging.warning(
                    "Rate limit exceeded. Waiting for %s seconds.",
                    RATE_LIMIT_WAIT,
                )
                time.sleep(RATE_LIMIT_WAIT)
            else:
                raise RuntimeError(data["error"])
        else:
            break

    logging.debug("File %s uploaded successfully with fileid %s", file_name, data["id"])
    return data


def start(  # noqa: PLR0913
    emoji_path_list: list[Path],
    drive_path: str = "",
    category: str = "",
    license_: str = "",
    *,
    sensitive: bool = False,
    local_only: bool = False,
) -> None:
    """Start the emoji uploading process."""
    total_emojis = len(emoji_path_list)
    success_count = 0
    skipped_count = 0
    # Get the current emojis list to avoid duplicates
    current_emojis = emojis_get_current_list()
    emoji_dict = {emoji["name"]: emoji for emoji in current_emojis}

    # Create the drive folder path if user provided
    if drive_path:
        folder_data = create_drive_folder_path(drive_path)
        folder_id = folder_data["id"]
    else:
        folder_id = None

    # Upload emojis to Misskey instance
    for emoji_path in emoji_path_list:
        # Convert the emoji name if needed.
        emoji_name = emoji_path.stem.split(".")[0].lower().replace("-", "_")

        # Skip if emoji already exists
        if emoji_name in emoji_dict:
            logging.warning("Emoji %s already exists. Skipping.", emoji_name)
            skipped_count += 1
            continue

        # Upload the emoji file to the drive
        logging.info("Uploading emoji %s...", emoji_name)
        file_data = drive_upload_file(emoji_path, folder_id, emoji_path.name)
        file_id = file_data["id"]
        logging.info(
            "Emoji %s uploaded successfully with file id %s",
            emoji_name,
            file_id,
        )

        # Create the emoji on the Misskey instance using the new file
        emoji_data = emoji_add(
            emoji_name=emoji_name,
            file_id=file_id,
            category=category,
            license_=license_,
            sensitive=sensitive,
            local_only=local_only,
        )

        if "error" in emoji_data:
            if emoji_data["error"]["code"] == "DUPLICATE_NAME":
                logging.warning("Emoji %s already exists. Skipping.", emoji_name)
                skipped_count += 1
                continue
            raise RuntimeError(emoji_data["error"])

        success_count += 1
        logging.info(
            "Emoji %s created successfully with id %s",
            emoji_name,
            emoji_data["id"],
        )
        logging.info("")

    logging.info(
        "Finished uploading emojis. %s out of %s emojis uploaded.",
        success_count,
        total_emojis,
    )

    if skipped_count:
        logging.info("Skipped %s emojis due to duplicate.", skipped_count)


def main() -> None:
    """Prepare the arguments and start the emoji uploading process."""
    parser = argparse.ArgumentParser(
        prog="ProgramName",
        description="What the program does",
        epilog="Text at the bottom of help",
    )

    parser.add_argument("path", help="Path to the local emojis folder or single file")
    parser.add_argument(
        "-d",
        "--drive-path",
        help="Path to the upload misskey drive folder",
        default="emojis",
    )
    parser.add_argument("-c", "--category", help="Category of the emojis", default="")
    parser.add_argument("-L", "--license", help="License of the emojis", default="")
    parser.add_argument(
        "-s",
        "--sensitive",
        action="store_true",
        help="Set the Sensitive of the emojis",
    )
    parser.add_argument(
        "-l",
        "--local_only",
        action="store_true",
        help="Set the emojis local only",
    )
    parser.add_argument(
        "-R",
        "--reverse",
        action="store_true",
        help="Reverse the emojis uploading order",
    )
    parser.add_argument(
        "--log",
        help="Set logging level",
        default="INFO",
    )

    args = parser.parse_args()

    logging.getLogger().setLevel(args.log.upper())

    # Check Misskey URL and token
    if not MISSKEY_URL:
        msg = "MISSKEY_URL environment variable is not set."
        raise OSError(msg)

    if not MISSKEY_TOKEN:
        msg = "MISSKEY_TOKEN environment variable is not set."
        raise OSError(msg)

    local_emoji_path = Path(args.path)
    emoji_path_list = None

    # Check the path
    if not local_emoji_path.exists():
        msg = f"Path {args.path} does not exist."
        raise FileNotFoundError(msg)

    if local_emoji_path.is_dir():
        # Get all files in the directory
        emoji_path_list = [
            p for p in local_emoji_path.absolute().glob("*") if p.is_file()
        ]

    if local_emoji_path.is_file():
        emoji_path_list = [local_emoji_path]

    if not emoji_path_list:
        msg = f"No files found in {args.path}."
        raise FileNotFoundError(msg)

    # Sort the emoji file list
    emoji_path_list.sort(reverse=args.reverse)

    start(
        emoji_path_list=emoji_path_list,
        drive_path=args.drive_path,
        category=args.category,
        license_=args.license,
        sensitive=args.sensitive,
        local_only=args.local_only,
    )


if __name__ == "__main__":
    main()
