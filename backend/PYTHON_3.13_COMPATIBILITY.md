# Python 3.13 Compatibility Guide

## Overview

Python 3.13 was released in October 2024 and is the latest Python version. While Substrate AI supports Python 3.13, some packages may require newer versions or alternative installation methods, especially on Windows.

## ✅ Supported Python Versions

- **Recommended**: Python 3.11 or 3.12 (most stable)
- **Supported**: Python 3.13 (may require additional setup)
- **Minimum**: Python 3.10

## 🔧 Python 3.13 Installation on Windows

### Option 1: Use Updated Requirements (Recommended)

The `requirements.txt` has been updated with Python 3.13-compatible versions:

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Install Problematic Packages Individually

If some packages still fail, install them individually with newer versions:

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install packages that support Python 3.13
pip install gevent>=24.11.0
pip install pydantic>=2.9.0
pip install tiktoken>=0.8.0
pip install psycopg2-binary>=2.9.10

# Then install rest of requirements
pip install -r requirements.txt
```

### Option 3: Build from Source (If Wheels Unavailable)

If wheels are not available, you may need to build from source. This requires a C compiler:

```bash
# Install build tools (Windows)
# Download Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/
# Select "Desktop development with C++"

# Then install packages without binary wheels
pip install --no-binary :all: gevent
pip install --no-binary :all: psycopg2-binary
```

**Note**: Building from source can be complex on Windows. Consider using Option 4 instead.

### Option 4: Use Python 3.11 or 3.12 (Easiest)

If you encounter issues with Python 3.13, we recommend using Python 3.11 or 3.12, which have better package support:

1. Download Python 3.12 from https://www.python.org/downloads/
2. Install it alongside Python 3.13 (they can coexist)
3. Create a new virtual environment with Python 3.12:
   ```bash
   py -3.12 -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

## 📦 Package-Specific Notes

### gevent
- **Issue**: May not have Windows wheels for Python 3.13
- **Solution**: Use `gevent>=24.11.0` or build from source
- **Alternative**: The system uses `eventlet` as primary async library, `gevent` is only a fallback

### pydantic
- **Issue**: Version 2.5.0 doesn't support Python 3.13
- **Solution**: Use `pydantic>=2.9.0` (updated in requirements.txt)

### psycopg2-binary
- **Issue**: Version 2.9.9 may not have Python 3.13 wheels on Windows
- **Solution**: Use `psycopg2-binary>=2.9.10` (updated in requirements.txt)
- **Note**: Only needed if using PostgreSQL. SQLite works without it.

### tiktoken
- **Issue**: Version 0.5.2 doesn't support Python 3.13
- **Solution**: Use `tiktoken>=0.8.0` (updated in requirements.txt)

## 🐛 Troubleshooting

### Error: "No matching distribution found"

**Solution**: Upgrade pip and try again:
```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Error: "Failed building wheel"

**Solution**: Install build dependencies:
```bash
# Windows
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# If still failing, install Visual Studio Build Tools
```

### Error: "Microsoft Visual C++ 14.0 or greater is required"

**Solution**: Install Visual Studio Build Tools:
1. Download: https://visualstudio.microsoft.com/downloads/
2. Install "Desktop development with C++" workload
3. Restart terminal and try again

### Some Packages Still Fail

If specific packages continue to fail:

1. **Skip optional packages**: Some packages are optional (like `psycopg2-binary` if not using PostgreSQL)
2. **Install without binary wheels**: `pip install --no-binary <package> <package>`
3. **Use Python 3.12**: Most reliable option for now

## ✅ Verification

After installation, verify everything works:

```bash
python -c "import gevent; import pydantic; import tiktoken; print('All packages imported successfully!')"
```

## 📝 Reporting Issues

If you encounter issues with Python 3.13:

1. Check Python version: `python --version`
2. Check pip version: `pip --version`
3. Try upgrading: `python -m pip install --upgrade pip setuptools wheel`
4. Report the issue with:
   - Python version
   - Operating system
   - Full error message
   - Output of `pip list`

## 🔄 Updates

This document will be updated as more packages add Python 3.13 support. Last updated: January 2025.

