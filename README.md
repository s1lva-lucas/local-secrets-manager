# Credential Manager 🔐

A secure command-line credential storage utility that leverages your system's keyring to safely store and manage secrets, API keys, and passwords with automatic prefix discovery and organization.

## 📦 Installation

[UV](https://github.com/astral-sh/uv) is a fast Python package and project manager written in Rust.

### Install UV

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup Project

```bash
# Clone the repository
git clone https://github.com/yourusername/credential-manager.git
cd credential-manager

# Create virtual environment
uv venv

# Install dependencies
uv pip install keyring keyrings.alt

# Run the tool
uv run python secrets_manager.py --help
```

### Install as Command Line Tool

```bash
# Install as editable package
uv pip install -e .

# Run as command
uv run credman --help
```

## 🚀 Quick Start

### Store a credential
```bash
# Store a GitHub token with default prefix "mcp"
uv run python secrets_manager.py --set -s github -v token

# Store with custom prefix "prod". The item will be saved as "database" and type "password".
uv run python secrets_manager.py --set -s database -v password -p prod
```

### Retrieve a credential
```bash
# Get a credential
uv run python secrets_manager.py --get -s github -v token

# Use in scripts (quiet mode)
export API_KEY=$(uv run python secrets_manager.py --get -s api -v key -p prod --quiet)
```

### List operations
```bash
# List all credentials for a prefix
uv run python secrets_manager.py --list -p prod

# List all discovered prefixes
uv run python secrets_manager.py --list-prefixes
```

## 📖 Usage

```
usage: secrets_manager.py [-h] (--set | --get | --delete | --list | --list-prefixes | --delete-prefix)
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
uv run python secrets_manager.py --set -s github -v token -p dev
uv run python secrets_manager.py --set -s aws -v secret_key -p prod

# Retrieve credentials
uv run python secrets_manager.py --get -s github -v token -p dev

# Delete a specific credential
uv run python secrets_manager.py --delete -s github -v token -p dev

# List all credentials for "prod" prefix
uv run python secrets_manager.py --list -p prod

# List all prefixes
uv run python secrets_manager.py --list-prefixes

# Delete all credentials with prefix "old-app"
uv run python secrets_manager.py --delete-prefix -p old-app --force
```

### Shell Integration

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Create an alias using UV
alias credman='uv run python /path/to/secrets_manager.py'

# Or as a function
credman() {
    uv run python /path/to/secrets_manager.py "$@"
}
```

### Use in Python Scripts

```python
import subprocess

def get_credential(service, variable, prefix):
    """Get a credential using the credential manager."""
    result = subprocess.run(
        ["uv", "run", "python", "secrets_manager.py", 
         "--get", "-s", service, "-v", variable, "-p", prefix, "--quiet"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None

# Usage
api_key = get_credential("database", "password", "prod")
print(api_key)
```

#### Via Wrapper
```python
# your_app.py
from credential_wrapper import CredentialManagerWrapper

# Initialize
creds = CredentialManagerWrapper(use_uv=False)  # Set use_uv=False if not using UV

# Use credentials
api_key = creds.get("database", "password", "prod") # Service, variable, prefix
print(api_key)
```

**Class-Based Integration**
```python
# app_with_secrets.py
from credential_wrapper import CredentialManagerWrapper

class SecureApp:
    def __init__(self):
        self.secrets = CredentialManagerWrapper(prefix="secure-app")
        
    def get_api_headers(self):
        """Build API headers with authentication."""
        token = self.secrets.get("api", "bearer_token")
        if not token:
            raise ValueError("API token not configured")
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get_database_config(self):
        """Get database configuration."""
        return {
            "host": self.secrets.get("db", "host") or "localhost",
            "port": self.secrets.get("db", "port") or "5432",
            "user": self.secrets.get("db", "user") or "postgres",
            "password": self.secrets.get("db", "password"),
            "database": self.secrets.get("db", "name") or "myapp"
        }

# Usage
app = SecureApp()
headers = app.get_api_headers()
db_config = app.get_database_config()
```

**Async Integration**
```python
# async_wrapper.py
import asyncio
from credential_wrapper import CredentialManagerWrapper

class AsyncCredentialWrapper:
    def __init__(self, prefix="mcp"):
        self.sync_wrapper = CredentialManagerWrapper(prefix=prefix)
    
    async def get(self, service: str, variable: str) -> str:
        """Async wrapper for get operation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.sync_wrapper.get, 
            service, 
            variable
        )
    
    async def set(self, service: str, variable: str, value: str) -> bool:
        """Async wrapper for set operation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.sync_wrapper.set,
            service,
            variable,
            value
        )

# Usage
async def main():
    creds = AsyncCredentialWrapper(prefix="async-app")
    token = await creds.get("api", "token")
    print(f"Token: {token}")

asyncio.run(main())
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
