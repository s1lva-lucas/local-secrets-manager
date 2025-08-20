#!/usr/bin/env python3
"""
Secure credential storage utility using system keyring.
Provides storage, retrieval, deletion, and listing of credentials with automatic prefix discovery.
"""

import keyring
import argparse
import getpass
import sys
import logging
import json
import os
from typing import Optional, List, Tuple, Set
from pathlib import Path
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Default prefix for backward compatibility
DEFAULT_PREFIX = "secrets"


class CredentialManager:
    """Manages credentials in the system keyring with automatic prefix tracking."""
    
    def __init__(self, prefix: str = DEFAULT_PREFIX):
        """Initialize with a specific prefix."""
        self.prefix = self._sanitize_prefix(prefix)
        self._registry_service = "_credential_manager_registry"
        self._registry_key = "prefixes"
    
    @staticmethod
    def _sanitize_prefix(prefix: str) -> str:
        """Sanitize and format the prefix."""
        if not prefix:
            raise ValueError("Prefix cannot be empty")
        # Remove trailing dot if present, we'll add it when needed
        prefix = prefix.rstrip('.')
        # Basic validation - alphanumeric, dots, hyphens, underscores only
        if not all(c.isalnum() or c in '.-_' for c in prefix):
            raise ValueError("Prefix can only contain alphanumeric characters, dots, hyphens, and underscores")
        return prefix
    
    def _make_service_name(self, service: str) -> str:
        """Create the full service name with prefix."""
        return f"{self.prefix}.{service}"
    
    def _register_prefix(self, prefix: str) -> None:
        """Register a prefix in the registry."""
        prefixes = self._get_registered_prefixes()
        if prefix not in prefixes:
            prefixes.add(prefix)
            self._save_registered_prefixes(prefixes)
    
    def _get_registered_prefixes(self) -> Set[str]:
        """Get all registered prefixes from the registry."""
        try:
            # Try to get from keyring first (most reliable)
            data = keyring.get_password(self._registry_service, self._registry_key)
            if data:
                return set(json.loads(data))
        except Exception as e:
            logger.debug(f"Could not load prefixes from keyring: {e}")
        
        return set()
    
    def _save_registered_prefixes(self, prefixes: Set[str]) -> None:
        """Save registered prefixes to the registry."""
        try:
            keyring.set_password(self._registry_service, self._registry_key, json.dumps(list(prefixes)))
        except Exception as e:
            logger.debug(f"Could not save prefixes to keyring: {e}")
    
    def retrieve(self, service: str, variable: str) -> Optional[str]:
        """Retrieve a credential from the keyring."""
        try:
            full_service = self._make_service_name(service)
            return keyring.get_password(full_service, variable)
        except Exception as e:
            logger.error(f"Error retrieving credential: {e}")
            return None
    
    def store(self, service: str, variable: str, credential: str) -> bool:
        """Store a credential in the keyring."""
        try:
            full_service = self._make_service_name(service)
            keyring.set_password(full_service, variable, credential)
            # Register the prefix automatically
            self._register_prefix(self.prefix)
            # Also store a reference for listing
            self._store_credential_reference(service, variable)
            return True
        except Exception as e:
            logger.error(f"Error storing credential: {e}")
            return False
    
    def delete(self, service: str, variable: str) -> bool:
        """Delete a credential from the keyring."""
        try:
            full_service = self._make_service_name(service)
            keyring.delete_password(full_service, variable)
            # Remove reference
            self._remove_credential_reference(service, variable)
            return True
        except keyring.errors.PasswordDeleteError:
            logger.error(f"Credential not found: {service}/{variable}")
            return False
        except Exception as e:
            logger.error(f"Error deleting credential: {e}")
            return False
    
    def _store_credential_reference(self, service: str, variable: str) -> None:
        """Store a reference to a credential for listing purposes."""
        try:
            # Store a list of credentials for each prefix
            registry_key = f"_refs_{self.prefix}"
            existing = keyring.get_password(self._registry_service, registry_key)
            
            if existing:
                refs = set(json.loads(existing))
            else:
                refs = set()
            
            refs.add(f"{service}|{variable}")
            keyring.set_password(self._registry_service, registry_key, json.dumps(list(refs)))
        except Exception as e:
            logger.debug(f"Could not store credential reference: {e}")
    
    def _remove_credential_reference(self, service: str, variable: str) -> None:
        """Remove a credential reference."""
        try:
            registry_key = f"_refs_{self.prefix}"
            existing = keyring.get_password(self._registry_service, registry_key)
            
            if existing:
                refs = set(json.loads(existing))
                refs.discard(f"{service}|{variable}")
                
                if refs:
                    keyring.set_password(self._registry_service, registry_key, json.dumps(list(refs)))
                else:
                    # Clean up empty reference list
                    try:
                        keyring.delete_password(self._registry_service, registry_key)
                    except:
                        pass
        except Exception as e:
            logger.debug(f"Could not remove credential reference: {e}")
    
    def list_credentials(self) -> List[Tuple[str, str]]:
        """List all credentials for the current prefix."""
        try:
            registry_key = f"_refs_{self.prefix}"
            existing = keyring.get_password(self._registry_service, registry_key)
            
            if existing:
                refs = json.loads(existing)
                credentials = []
                for ref in refs:
                    if '|' in ref:
                        service, variable = ref.split('|', 1)
                        # Verify it still exists
                        if self.retrieve(service, variable) is not None:
                            credentials.append((service, variable))
                        else:
                            # Clean up stale reference
                            self._remove_credential_reference(service, variable)
                return sorted(credentials)
        except Exception as e:
            logger.debug(f"Could not list credentials: {e}")
        
        return []
    
    @classmethod
    def list_all_prefixes(cls) -> List[str]:
        """List all registered prefixes."""
        manager = cls()
        return sorted(list(manager._get_registered_prefixes()))
    
    def delete_prefix(self, prefix: str, force: bool = False) -> bool:
        """Delete all credentials with a given prefix."""
        if not force:
            logger.warning(f"This will delete ALL credentials with prefix '{prefix}'")
            if not confirm_action("Are you sure?"):
                return False
        
        # Get all credentials for this prefix
        old_prefix = self.prefix
        self.prefix = prefix
        credentials = self.list_credentials()
        
        deleted_count = 0
        for service, variable in credentials:
            if self.delete(service, variable):
                deleted_count += 1
        
        # Remove prefix from registry
        prefixes = self._get_registered_prefixes()
        prefixes.discard(prefix)
        self._save_registered_prefixes(prefixes)
        
        # Clean up reference list
        try:
            registry_key = f"_refs_{prefix}"
            keyring.delete_password(self._registry_service, registry_key)
        except:
            pass
        
        self.prefix = old_prefix
        logger.info(f"Deleted {deleted_count} credentials with prefix '{prefix}'")
        return True


class AlternativeStorage:
    """Alternative storage backend using filesystem for metadata when keyring doesn't support it."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "credential-manager"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.config_dir / "registry.json"
    
    def get_registry(self) -> dict:
        """Load registry from file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"prefixes": [], "credentials": {}}
    
    def save_registry(self, registry: dict) -> None:
        """Save registry to file."""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save registry: {e}")
    
    def register_credential(self, prefix: str, service: str, variable: str) -> None:
        """Register a credential in the filesystem registry."""
        registry = self.get_registry()
        
        # Add prefix if not exists
        if prefix not in registry["prefixes"]:
            registry["prefixes"].append(prefix)
        
        # Add credential reference
        if prefix not in registry["credentials"]:
            registry["credentials"][prefix] = []
        
        cred_ref = f"{service}|{variable}"
        if cred_ref not in registry["credentials"][prefix]:
            registry["credentials"][prefix].append(cred_ref)
        
        self.save_registry(registry)
    
    def unregister_credential(self, prefix: str, service: str, variable: str) -> None:
        """Remove a credential from the filesystem registry."""
        registry = self.get_registry()
        
        if prefix in registry["credentials"]:
            cred_ref = f"{service}|{variable}"
            if cred_ref in registry["credentials"][prefix]:
                registry["credentials"][prefix].remove(cred_ref)
                
                # Clean up empty prefix
                if not registry["credentials"][prefix]:
                    del registry["credentials"][prefix]
                    if prefix in registry["prefixes"]:
                        registry["prefixes"].remove(prefix)
        
        self.save_registry(registry)
    
    def list_prefixes(self) -> List[str]:
        """List all registered prefixes."""
        registry = self.get_registry()
        return sorted(registry.get("prefixes", []))
    
    def list_credentials(self, prefix: str) -> List[Tuple[str, str]]:
        """List all credentials for a prefix."""
        registry = self.get_registry()
        credentials = []
        
        if prefix in registry.get("credentials", {}):
            for ref in registry["credentials"][prefix]:
                if '|' in ref:
                    service, variable = ref.split('|', 1)
                    credentials.append((service, variable))
        
        return sorted(credentials)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Secure credential storage utility with automatic prefix discovery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --set -s github -v token -p myapp
  %(prog)s --get -s github -v token -p myapp
  %(prog)s --delete -s github -v token -p myapp
  %(prog)s --list -p myapp
  %(prog)s --list-prefixes
  %(prog)s --delete-prefix -p old-app --force
        """
    )
    
    # Operation group
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--set', action="store_true", help="Store a credential")
    group.add_argument('--get', action="store_true", help="Retrieve a credential")
    group.add_argument('--delete', action="store_true", help="Delete a credential")
    group.add_argument('--list', action="store_true", help="List all credentials for a prefix")
    group.add_argument('--list-prefixes', action="store_true", 
                      help="List all discovered prefixes")
    group.add_argument('--delete-prefix', action="store_true",
                      help="Delete all credentials with a prefix")
    
    # Parameters
    parser.add_argument('--service', '-s', help="Service name - It means the name that will be save in the Keychains")
    parser.add_argument('--variable', '-v', help="Variable/credential name - It will be added to the \"account\" field in the Keychains")
    parser.add_argument('--prefix', '-p', default=DEFAULT_PREFIX, 
                       help=f"Prefix for namespacing - Easy way for tagging and finding data (default: {DEFAULT_PREFIX})")
    
    # Optional flags
    parser.add_argument('--force', '-f', action="store_true", 
                       help="Force operation without confirmation")
    parser.add_argument('--quiet', '-q', action="store_true", 
                       help="Suppress non-essential output")
    parser.add_argument('--debug', action="store_true", 
                       help="Enable debug output")
    parser.add_argument('--use-filesystem', action="store_true",
                       help="Use filesystem for metadata storage (more reliable listing)")
    
    return parser.parse_args()


def validate_args(args):
    """Validate argument combinations."""
    if args.set or args.get or args.delete:
        if not args.service or not args.variable:
            logger.error("--service and --variable are required for set/get/delete operations")
            sys.exit(1)


def confirm_action(message: str) -> bool:
    """Ask for user confirmation."""
    response = input(f"{message} (y/N): ").lower().strip()
    return response in ['y', 'yes']


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    
    # Validate arguments
    validate_args(args)
    
    try:
        # Create credential manager with specified prefix
        manager = CredentialManager(prefix=args.prefix)
        
        # Optional: Use filesystem for metadata
        alt_storage = AlternativeStorage() if args.use_filesystem else None
        
        if args.set:
            # Check if credential already exists
            existing = manager.retrieve(args.service, args.variable)
            if existing and not args.force:
                if not confirm_action(f"Credential already exists for {args.service}/{args.variable}. Overwrite?"):
                    logger.info("Operation cancelled")
                    sys.exit(0)
            
            # Get credential securely
            credential = getpass.getpass(f"Enter credential for {args.service}/{args.variable}: ")
            
            # Optional: confirm credential
            if not args.force:
                credential_confirm = getpass.getpass("Confirm credential: ")
                if credential != credential_confirm:
                    logger.error("Credentials do not match")
                    sys.exit(1)
            
            # Store credential
            if manager.store(args.service, args.variable, credential):
                if alt_storage:
                    alt_storage.register_credential(args.prefix, args.service, args.variable)
                logger.info(f"✓ Credential stored successfully for {args.service}/{args.variable}")
            else:
                logger.error("Failed to store credential")
                sys.exit(1)
        
        elif args.get:
            result = manager.retrieve(args.service, args.variable)
            if result:
                print(result)
            else:
                logger.error(f"No credential found for {args.service}/{args.variable}")
                sys.exit(1)
        
        elif args.delete:
            if manager.delete(args.service, args.variable):
                if alt_storage:
                    alt_storage.unregister_credential(args.prefix, args.service, args.variable)
                logger.info(f"✓ Credential deleted successfully for {args.service}/{args.variable}")
            else:
                logger.error("Failed to delete credential")
                sys.exit(1)
        
        elif args.list:
            if alt_storage:
                credentials = alt_storage.list_credentials(args.prefix)
            else:
                credentials = manager.list_credentials()
            
            if credentials:
                logger.info(f"Credentials for prefix '{args.prefix}':")
                for service, variable in credentials:
                    logger.info(f"  • {service}/{variable}")
            else:
                logger.info(f"No credentials found for prefix '{args.prefix}'")
        
        elif args.list_prefixes:
            if alt_storage:
                prefixes = alt_storage.list_prefixes()
            else:
                prefixes = CredentialManager.list_all_prefixes()
            
            if prefixes:
                logger.info("Discovered prefixes:")
                for prefix in prefixes:
                    logger.info(f"  • {prefix}")
            else:
                logger.info("No prefixes found")
        
        elif args.delete_prefix:
            if manager.delete_prefix(args.prefix, force=args.force):
                logger.info(f"✓ Successfully deleted all credentials with prefix '{args.prefix}'")
            else:
                logger.error("Failed to delete prefix")
                sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
