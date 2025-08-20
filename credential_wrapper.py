#!/usr/bin/env python3
"""
Wrapper for local-secrets-manager.py to use in other Python applications.
"""

import subprocess
import json
import os
from typing import Optional, List, Tuple, Dict
from pathlib import Path


class CredentialManagerWrapper:
    """Wrapper class for local-secrets-manager.py script."""
    
    def __init__(self, script_path: Optional[str] = None, prefix: str = "mcp", use_uv: bool = True):
        """
        Initialize the wrapper.
        
        Args:
            script_path: Path to local-secrets-manager.py (auto-detects if None)
            prefix: Default prefix to use
            use_uv: Whether to use uv run (True) or direct python (False)
        """
        if script_path:
            self.script_path = Path(script_path)
        else:
            # Auto-detect script path (same directory as this wrapper)
            self.script_path = Path(__file__).parent / "local-secrets-manager.py"
        
        if not self.script_path.exists():
            raise FileNotFoundError(f"local-secrets-manager.py not found at {self.script_path}")
        
        self.prefix = prefix
        self.use_uv = use_uv
        
        # Base command
        if self.use_uv:
            self.base_cmd = ["uv", "run", "python", str(self.script_path)]
        else:
            self.base_cmd = ["python", str(self.script_path)]
    
    def _run_command(self, args: List[str]) -> Tuple[int, str, str]:
        """
        Run a command and return the result.
        
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        cmd = self.base_cmd + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return 1, "", "Command timeout"
        except Exception as e:
            return 1, "", str(e)
    
    def get(self, service: str, variable: str, prefix: Optional[str] = None) -> Optional[str]:
        """
        Get a credential.
        
        Args:
            service: Service name
            variable: Variable name
            prefix: Optional prefix override
        
        Returns:
            The credential value or None if not found
        """
        args = ["--get", "-s", service, "-v", variable, "-p", prefix or self.prefix, "--quiet"]
        returncode, stdout, stderr = self._run_command(args)
        
        if returncode == 0:
            return stdout
        return None
    
    def set(self, service: str, variable: str, value: str, 
            prefix: Optional[str] = None, force: bool = True) -> bool:
        """
        Set a credential.
        
        Args:
            service: Service name
            variable: Variable name
            value: Credential value
            prefix: Optional prefix override
            force: Skip confirmation prompts
        
        Returns:
            True if successful, False otherwise
        """
        args = ["--set", "-s", service, "-v", variable, "-p", prefix or self.prefix]
        if force:
            args.append("--force")
        
        # Use stdin to provide the credential
        cmd = self.base_cmd + args
        
        try:
            # For set operation, we need to provide input
            if force:
                # With force, only one password prompt
                input_data = f"{value}\n"
            else:
                # Without force, two password prompts (credential and confirmation)
                input_data = f"{value}\n{value}\n"
            
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def delete(self, service: str, variable: str, 
               prefix: Optional[str] = None, force: bool = True) -> bool:
        """
        Delete a credential.
        
        Args:
            service: Service name
            variable: Variable name
            prefix: Optional prefix override
            force: Skip confirmation prompt
        
        Returns:
            True if successful, False otherwise
        """
        args = ["--delete", "-s", service, "-v", variable, "-p", prefix or self.prefix]
        if force:
            args.append("--force")
        
        returncode, _, _ = self._run_command(args)
        return returncode == 0
    
    def list_credentials(self, prefix: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        List all credentials for a prefix.
        
        Args:
            prefix: Optional prefix override
        
        Returns:
            List of (service, variable) tuples
        """
        args = ["--list", "-p", prefix or self.prefix]
        returncode, stdout, _ = self._run_command(args)
        
        if returncode != 0:
            return []
        
        credentials = []
        for line in stdout.split('\n'):
            # Parse output format: "  • service/variable"
            if '•' in line and '/' in line:
                line = line.split('•')[1].strip()
                if '/' in line:
                    service, variable = line.split('/', 1)
                    credentials.append((service, variable))
        
        return credentials
    
    def list_prefixes(self) -> List[str]:
        """
        List all available prefixes.
        
        Returns:
            List of prefix strings
        """
        args = ["--list-prefixes"]
        returncode, stdout, _ = self._run_command(args)
        
        if returncode != 0:
            return []
        
        prefixes = []
        for line in stdout.split('\n'):
            # Parse output format: "  • prefix"
            if '•' in line:
                prefix = line.split('•')[1].strip()
                if prefix:
                    prefixes.append(prefix)
        
        return prefixes
    
    def exists(self, service: str, variable: str, prefix: Optional[str] = None) -> bool:
        """
        Check if a credential exists.
        
        Args:
            service: Service name
            variable: Variable name
            prefix: Optional prefix override
        
        Returns:
            True if credential exists, False otherwise
        """
        return self.get(service, variable, prefix) is not None
    
    def get_or_prompt(self, service: str, variable: str, 
                      prefix: Optional[str] = None, prompt: Optional[str] = None) -> str:
        """
        Get a credential or prompt user to create it.
        
        Args:
            service: Service name
            variable: Variable name
            prefix: Optional prefix override
            prompt: Optional custom prompt message
        
        Returns:
            The credential value
        """
        value = self.get(service, variable, prefix)
        
        if value is None:
            import getpass
            if prompt is None:
                prompt = f"Enter credential for {service}/{variable}: "
            
            value = getpass.getpass(prompt)
            
            # Store it for future use
            if self.set(service, variable, value, prefix):
                print(f"Credential saved for {service}/{variable}")
            
        return value
    
    def bulk_get(self, credentials: List[Tuple[str, str]], 
                 prefix: Optional[str] = None) -> Dict[str, str]:
        """
        Get multiple credentials at once.
        
        Args:
            credentials: List of (service, variable) tuples
            prefix: Optional prefix override
        
        Returns:
            Dictionary mapping "service/variable" to credential values
        """
        results = {}
        for service, variable in credentials:
            value = self.get(service, variable, prefix)
            if value:
                results[f"{service}/{variable}"] = value
        return results


# Convenience functions for direct use
_default_wrapper = None

def get_credential(service: str, variable: str, prefix: str = "mcp") -> Optional[str]:
    """Get a credential using the default wrapper."""
    global _default_wrapper
    if _default_wrapper is None:
        _default_wrapper = CredentialManagerWrapper(prefix=prefix)
    return _default_wrapper.get(service, variable, prefix)


def set_credential(service: str, variable: str, value: str, prefix: str = "mcp") -> bool:
    """Set a credential using the default wrapper."""
    global _default_wrapper
    if _default_wrapper is None:
        _default_wrapper = CredentialManagerWrapper(prefix=prefix)
    return _default_wrapper.set(service, variable, value, prefix)


def delete_credential(service: str, variable: str, prefix: str = "mcp") -> bool:
    """Delete a credential using the default wrapper."""
    global _default_wrapper
    if _default_wrapper is None:
        _default_wrapper = CredentialManagerWrapper(prefix=prefix)
    return _default_wrapper.delete(service, variable, prefix)
