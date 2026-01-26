# Atlassian Uploader

## Overview

A utility for uploading large files to Atlassian Premier Support tickets by splitting them into manageable chunks. This tool handles large diagnostic bundles, log files, and other support artifacts that exceed size limits.

## What It Does

- **File Chunking**: Splits large files into smaller chunks for upload
- **Automated Upload**: Uploads chunks to Atlassian Premier Support tickets
- **Progress Tracking**: Tracks upload progress and provides status updates
- **Error Handling**: Handles upload failures and retries
- **Cleanup**: Optionally deletes chunks after successful upload

## Prerequisites

- Python 3.7+
- cURL command-line tool
- Atlassian Premier Support account
- Authentication token for Premier Support API

## Configuration

### Main Configuration: `atlassian_uploader.py`

Edit the configuration section in `atlassian_uploader.py`:

```python
# 1. Your Authentication Token
AUTH_TOKEN = "TOKEN"  # Replace TOKEN with actual token

# 2. The Jira/Premier Support Ticket Number
TICKET_ID = "PS-190255"

# 3. How many chunks to split the file into?
CHUNK_COUNT = 1

# 4. List of absolute paths to the files you want to process
FILES_TO_PROCESS = [
    "/path/to/file1.zip",
    "/path/to/file2.zip"
]

# 5. Delete chunks after successful upload to save disk space? (True/False)
DELETE_CHUNKS_AFTER_UPLOAD = True

# 6. Directory to store chunks ('.' for current dir, or None to use same dir as source file)
TEMP_CHUNK_DIR = "."
```

**Configuration Parameters:**
- `AUTH_TOKEN`: Atlassian Premier Support API token - **Replace "TOKEN" with actual token**
- `TICKET_ID`: Premier Support ticket number (format: PS-XXXXXX)
- `CHUNK_COUNT`: Number of chunks to split files into
- `FILES_TO_PROCESS`: List of file paths to upload
- `DELETE_CHUNKS_AFTER_UPLOAD`: Whether to delete chunks after upload
- `TEMP_CHUNK_DIR`: Directory for temporary chunk files

### Server Names and Locations

- **Premier Support API**: Hardcoded to Atlassian Premier Support endpoint
- **File Paths**: Configured in `FILES_TO_PROCESS` array

### Thresholds

- **File Size Limits**: Determined by Atlassian Premier Support limits (typically 100MB per attachment)
- **Chunk Size**: Calculated automatically based on `CHUNK_COUNT` and file size

## How to Use

### 1. Setup

```bash
# No additional dependencies needed (uses cURL)
# Configure AUTH_TOKEN and TICKET_ID in atlassian_uploader.py
# Replace "TOKEN" with actual authentication token
```

### 2. Configure Files

Edit `atlassian_uploader.py` and update:
- `AUTH_TOKEN`: Your Premier Support API token
- `TICKET_ID`: Your support ticket number
- `FILES_TO_PROCESS`: List of files to upload

### 3. Run Upload

```bash
python3 atlassian_uploader.py
```

The script will:
1. Split files into chunks
2. Upload each chunk to the ticket
3. Track progress
4. Clean up chunks (if configured)

## Credentials/Tokens

### Authentication Token

- **Token**: Atlassian Premier Support API token
- **Getting Token**: Contact Atlassian Premier Support or check your account settings
- **Replace "TOKEN"**: Replace "TOKEN" placeholder with actual token

### Security Notes

- **Never commit tokens to version control**
- Use environment variables for tokens in production
- Tokens provide access to your support tickets - keep secure
- Rotate tokens periodically

## Upload Process

1. **File Splitting**: Files are split into chunks based on `CHUNK_COUNT`
2. **Chunk Upload**: Each chunk is uploaded sequentially to the ticket
3. **Progress Tracking**: Progress is displayed for each chunk
4. **Error Handling**: Failed uploads are reported
5. **Cleanup**: Chunks are deleted after successful upload (if configured)

## Troubleshooting

### Common Issues

1. **Authentication Failed**: Verify `AUTH_TOKEN` is correct and not expired
2. **Ticket Not Found**: Check `TICKET_ID` is correct and you have access
3. **File Not Found**: Verify file paths in `FILES_TO_PROCESS` are correct
4. **Upload Failed**: Check network connectivity and file size limits
5. **Permission Denied**: Ensure write access to `TEMP_CHUNK_DIR`

### Getting Help

- Review error messages in console output
- Verify token and ticket ID are correct
- Check file paths and permissions
- Test with a small file first

## Example Workflow

```bash
# 1. Configure token and ticket
# Edit atlassian_uploader.py:
#   AUTH_TOKEN = "your_actual_token"
#   TICKET_ID = "PS-190255"
#   FILES_TO_PROCESS = ["/path/to/diagnostic_bundle.zip"]

# 2. Run upload
python3 atlassian_uploader.py

# 3. Monitor progress
# Watch console output for upload status

# 4. Verify upload
# Check Premier Support ticket for uploaded files
```

## Files Overview

- `atlassian_uploader.py`: Main upload script with configuration

---

**Note**: This is production-ready code. Replace "TOKEN" placeholder with actual Premier Support API token before execution.

