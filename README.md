# Credential Manager 🔐

A secure command-line credential storage utility that leverages your system's keyring to safely store and manage secrets, API keys, and passwords with automatic prefix discovery and organization.

## 📦 Installation

### Using UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a fast Python package and project manager written in Rust.

```bash
# Create virtual environment if it doesn't exist
uv venv

# Install keyring directly
uv pip install keyring

# Run your script
uv run python local-secrets-manager.py --help
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/yourusername/credential-manager.git
cd credential-manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install keyring keyrings.alt

# Run the tool
python local-secrets-manager.py --help
```

### Install as Command Line Tool

```bash
# With UV
uv pip install -e .
uv run credman --help

# With pip
pip install -e .
credman --help
```

## 🚀 Quick Start

### Store a credential
```bash
# Store a GitHub token with default prefix "mcp"
python local-secrets-manager.py --set -s github -v token

# Store with custom prefix "prod"
python local-secrets-manager.py --set -s database -v password -p prod
```

### Retrieve a credential
```bash
# Get a credential
python local-secrets-manager.py --get -s github -v token

# Use in scripts (quiet mode)
export API_KEY=$(python local-secrets-manager.py --get -s api -v key -p prod --quiet)
```

### List operations
```bash
# List all credentials for a prefix
python local-secrets-manager.py --list -p prod

# List all discovered prefixes
python local-secrets-manager.py --list-prefixes
```

## 📖 Usage

```
usage: local-secrets-manager.py [-h] (--set | --get | --delete | --list | --list-prefixes | --delete-prefix)
                             [--service SERVICE] [--variable VARIABLE] [--prefix PREFIX]
                             [--force] [--quiet] [--debug] [--use-filesystem]

Secure credential storage utility with automatic prefix discovery

options:
  -h, --help            show this help message and exit
  --set                 Store a credential
  --get                 Retrieve a credential
  --delete              Delete a credential
  --list                List all credentials for a prefix
  --list-prefixes       List all discovered prefixes
  --delete-prefix       Delete all credentials with a prefix
  --service SERVICE, -s SERVICE
                        Service name
  --variable VARIABLE, -v VARIABLE
                        Variable/credential name
  --prefix PREFIX, -p PREFIX
                        Prefix for namespacing (default: mcp)
  --force, -f           Force operation without confirmation
  --quiet, -q           Suppress non-essential output
  --debug               Enable debug output
  --use-filesystem      Use filesystem for metadata storage (more reliable listing)
```

## 🔍 Examples

### Basic Operations

```bash
# Store credentials
./local-secrets-manager.py --set -s github -v token -p dev
./local-secrets-manager.py --set -s aws -v secret_key -p prod

# Retrieve credentials
./local-secrets-manager.py --get -s github -v token -p dev

# Delete a specific credential
./local-secrets-manager.py --delete -s github -v token -p dev

# List all credentials for "prod" prefix
./local-secrets-manager.py --list -p prod

# List all prefixes
./local-secrets-manager.py --list-prefixes

# Delete all credentials with prefix "old-app"
./local-secrets-manager.py --delete-prefix -p old-app --force
```

### Shell Integration

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Create an alias
alias credman='python /path/to/local-secrets-manager.py'

# Or as a function
credman() {
    python /path/to/local-secrets-manager.py "$@"
}
```

### Use in Python Scripts

```python
import subprocess

def get_credential(service, variable, prefix="mcp"):
    """Get a credential using the credential manager."""
    result = subprocess.run(
        ["python", "local-secrets-manager.py", 
         "--get", "-s", service, "-v", variable, "-p", prefix, "--quiet"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None

# Usage
api_key = get_credential("github", "token", "prod")
```

## 🔒 Security

The security of stored credentials depends on your system's keyring backend:

| Platform | Backend | Security Level |
|----------|---------|---------------|
| macOS | Keychain | High - Hardware encrypted |
| Windows | Credential Locker | High - DPAPI encrypted |
| Linux (GNOME) | Secret Service | High - Session encrypted |
| Linux (KDE) | KWallet | High - Session encrypted |
| Fallback | Encrypted file | Medium - Password protected |


## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

