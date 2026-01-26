# Atlassian Binary Compare

## Overview

A utility script for comparing `setenv.sh` configuration files between different versions of Atlassian Jira or Confluence. This tool automatically downloads the specified versions, extracts only the `setenv.sh` file, and provides a detailed diff comparison to help identify configuration changes between versions.

## What It Does

- **Automated Download**: Downloads Jira or Confluence tarballs for specified versions
- **Selective Extraction**: Extracts only the `setenv.sh` file from archives (efficient, no full extraction)
- **Version Comparison**: Performs unified diff comparison between two versions
- **Change Detection**: Identifies differences in configuration files between versions
- **Safe Migration Guidance**: Provides recommendations for configuration migration
- **Automatic Cleanup**: Cleans up temporary files automatically

## Prerequisites

### Software Requirements
- **Bash Shell**: Bash 4.0 or higher (standard on Linux/macOS)
- **curl**: Command-line tool for downloading files (usually pre-installed)
- **tar**: Archive extraction tool (standard on Unix systems)
- **diff**: File comparison utility (standard on Unix systems)
- **Operating System**: Linux or macOS (Windows requires WSL or Git Bash)

### Connectivity Requirements
- **Network Access**:
  - Internet connectivity to Atlassian download servers
  - Access to `https://product-downloads.atlassian.com`
  - Sufficient bandwidth for downloading tarballs (typically 200-500 MB per version)
- **File System Access**:
  - Write access to temporary directory (uses `mktemp`)
  - Sufficient disk space for temporary files (typically 500 MB - 1 GB)

### Folder Structure
The framework expects the following structure:
```
atl-binary-compare/
├── compare_setenv.sh          # Main comparison script
└── README.md                   # This file
```

**Important**:
- Script must have execute permissions: `chmod +x compare_setenv.sh`
- Temporary files are created in system temp directory (automatically cleaned up)
- No configuration files required - all parameters passed via command line

### Access & Credentials
- **Network Access**:
  - Public internet access to Atlassian download servers
  - No authentication required (public downloads)
- **File System Permissions**:
  - Write access to temporary directory
  - No special credentials needed

### Pre-Execution Checks
Before running comparison, verify:
1. ✅ Bash shell available: `bash --version`
2. ✅ curl installed: `curl --version`
3. ✅ tar installed: `tar --version`
4. ✅ diff installed: `diff --version`
5. ✅ Network connectivity: `curl -I https://product-downloads.atlassian.com`
6. ✅ Sufficient disk space: `df -h` (check available space)
7. ✅ Script has execute permissions: `chmod +x compare_setenv.sh`
8. ✅ Valid version numbers: Check Atlassian release notes for available versions

## Configuration

### Command Line Usage

The script requires three arguments:

```bash
./compare_setenv.sh <product> <version1> <version2>
```

**Parameters:**
- `product`: Either `jira` or `confluence`
- `version1`: Source version (e.g., "10.3.12")
- `version2`: Target version (e.g., "10.3.15")

### Examples

```bash
# Compare Jira versions
./compare_setenv.sh jira 10.3.12 10.3.15

# Compare Confluence versions
./compare_setenv.sh confluence 9.2.5 9.2.12
```

### Server Names and Locations

- **Download URLs**: Automatically configured based on product type
  - Jira: `https://product-downloads.atlassian.com/software/jira/downloads`
  - Confluence: `https://product-downloads.atlassian.com/software/confluence/downloads`
- **Temporary Directory**: Created automatically using `mktemp` (cleaned up on exit)

### Thresholds

- **Version Format**: Must match Atlassian version format (e.g., "10.3.12", "9.2.5")
- **File Size**: Tarballs typically 200-500 MB each
- **Timeout**: Default curl timeout applies (adjust if needed for slow connections)

## How to Use

### 1. Setup

```bash
# Ensure script has execute permissions
chmod +x compare_setenv.sh
```

### 2. Run Comparison

```bash
# Compare Jira versions
./compare_setenv.sh jira 10.3.12 10.3.15

# Compare Confluence versions
./compare_setenv.sh confluence 9.2.5 9.2.12
```

### 3. Review Output

The script will:
1. Download both version tarballs
2. Extract only the `setenv.sh` files
3. Compare the files
4. Display results:
   - If identical: Confirmation that files match
   - If different: Unified diff showing changes

## Credentials/Tokens

### Network Access

- **No Authentication Required**: Atlassian downloads are publicly accessible
- **No Credentials Needed**: Script uses public download URLs

### Security Notes

- **Temporary Files**: All temporary files are automatically cleaned up
- **No Sensitive Data**: Script only downloads and compares public configuration files
- **Network Traffic**: Downloads are over HTTPS (secure)

## Comparison Features

### Identical Files
- If `setenv.sh` files are identical, script confirms you can safely copy existing configuration

### Different Files
- Shows unified diff with color highlighting (if supported)
- Displays changes in format: `< Source | > Target`
- Provides recommendation to manually apply customizations

### Error Handling
- Validates input parameters
- Checks download success
- Verifies file extraction
- Handles network errors gracefully

## Troubleshooting

### Common Issues

1. **Invalid Version**: Version number doesn't exist
   - **Solution**: Check Atlassian release notes for valid version numbers
   - **Check**: Verify version format matches (e.g., "10.3.12" not "10.3.12.0")

2. **Download Failed**: Network error or version not found
   - **Solution**: Check network connectivity and verify version exists
   - **Check**: `curl -I <download_url>` to test URL

3. **File Not Found in Archive**: `setenv.sh` not found in tarball
   - **Solution**: Atlassian may have changed archive structure (rare)
   - **Check**: Review script output for internal path detection

4. **Permission Denied**: Cannot write to temp directory
   - **Solution**: Check disk space and temp directory permissions
   - **Check**: `df -h` and `ls -ld /tmp`

5. **Slow Downloads**: Large tarballs take time
   - **Solution**: Normal behavior, script shows progress
   - **Check**: Network bandwidth and server response times

### Getting Help

- Review error messages in console output
- Verify version numbers are correct
- Check network connectivity
- Ensure sufficient disk space

## Example Workflow

```bash
# 1. Prepare for upgrade from Jira 10.3.12 to 10.3.15
./compare_setenv.sh jira 10.3.12 10.3.15

# 2. Review the diff output
# If identical: Copy existing setenv.sh to new installation
# If different: Manually merge customizations into new file

# 3. For Confluence upgrade from 9.2.5 to 9.2.12
./compare_setenv.sh confluence 9.2.5 9.2.12

# 4. Review and apply changes as needed
```

## Files Overview

- `compare_setenv.sh`: Main comparison script that downloads, extracts, and compares `setenv.sh` files

---

**Note**: This is production-ready code. Ensure network connectivity and sufficient disk space before running comparisons.
