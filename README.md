# Upload emojis to Misskey instance

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
