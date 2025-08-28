"""
Cloud provider abstraction layer for TerraVision.

This package provides a pluggable architecture for supporting multiple cloud providers
(AWS, GCP, Azure, etc.) with consistent interfaces for resource handling and visualization.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from enum import Enum


class CloudProvider(Enum):
    """Enumeration of supported cloud providers."""
    AWS = "aws"
    GCP = "gcp" 
    AZURE = "azure"
    GENERIC = "generic"


class BaseCloudProvider(ABC):
    """
    Abstract base class for cloud provider implementations.
    
    This class defines the interface that all cloud providers must implement
    to work with TerraVision's graph generation and visualization system.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the cloud provider."""
        pass
    
    @property
    @abstractmethod
    def resource_prefix(self) -> str:
        """Return the resource prefix used in Terraform (e.g., 'aws_', 'google_')."""
        pass
    
    @property
    @abstractmethod
    def reverse_arrow_list(self) -> List[str]:
        """Return list of resources that should have reversed arrow directions."""
        pass
    
    @property
    @abstractmethod
    def implied_connections(self) -> Dict[str, str]:
        """Return mapping of keywords to implied resource connections."""
        pass
    
    @property
    @abstractmethod
    def group_nodes(self) -> Set[str]:
        """Return set of resource types that should be treated as groups."""
        pass
    
    @property
    @abstractmethod
    def consolidated_nodes(self) -> Dict[str, str]:
        """Return mapping of resources that should be consolidated."""
        pass
    
    @property
    @abstractmethod
    def special_resources(self) -> Dict[str, str]:
        """Return mapping of resource types to their special handler functions."""
        pass
    
    @property
    @abstractmethod
    def shared_services(self) -> Set[str]:
        """Return set of resource types that are shared services."""
        pass
    
    @abstractmethod
    def get_resource_variant(self, resource_name: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Determine the variant of a resource based on its metadata.
        
        Args:
            resource_name: Name of the resource
            metadata: Resource metadata dictionary
            
        Returns:
            Variant name if applicable, None otherwise
        """
        pass
    
    @abstractmethod
    def get_resource_icon_path(self, resource_type: str, variant: Optional[str] = None) -> str:
        """
        Get the icon path for a resource type.
        
        Args:
            resource_type: Type of resource (e.g., 'aws_ec2_instance')
            variant: Optional variant of the resource
            
        Returns:
            Path to the resource icon
        """
        pass
    
    @abstractmethod
    def should_consolidate(self, resource_name: str) -> Optional[str]:
        """
        Check if a resource should be consolidated and return the consolidated name.
        
        Args:
            resource_name: Name of the resource to check
            
        Returns:
            Consolidated name if resource should be consolidated, None otherwise
        """
        pass
    
    @abstractmethod
    def get_forced_destinations(self) -> Set[str]:
        """Return set of resource types that should be forced as destinations."""
        pass
    
    @abstractmethod
    def get_forced_origins(self) -> Set[str]:
        """Return set of resource types that should be forced as origins."""
        pass
    
    def is_resource_of_provider(self, resource_name: str) -> bool:
        """
        Check if a resource belongs to this provider.
        
        Args:
            resource_name: Name of the resource to check
            
        Returns:
            True if resource belongs to this provider
        """
        return resource_name.startswith(self.resource_prefix)
    
    def get_resource_category(self, resource_type: str) -> str:
        """
        Get the category of a resource type for organization.
        
        Args:
            resource_type: Type of resource
            
        Returns:
            Category name (e.g., 'compute', 'network', 'storage')
        """
        # Default implementation - providers can override
        if 'compute' in resource_type or 'instance' in resource_type:
            return 'compute'
        elif 'network' in resource_type or 'vpc' in resource_type or 'subnet' in resource_type:
            return 'network'
        elif 'storage' in resource_type or 'bucket' in resource_type or 'disk' in resource_type:
            return 'storage'
        elif 'database' in resource_type or 'db' in resource_type:
            return 'database'
        elif 'security' in resource_type or 'iam' in resource_type:
            return 'security'
        else:
            return 'other'


class CloudProviderRegistry:
    """Registry for managing cloud provider implementations."""
    
    def __init__(self):
        self._providers: Dict[str, BaseCloudProvider] = {}
        self._default_provider: Optional[BaseCloudProvider] = None
    
    def register(self, provider: BaseCloudProvider, set_as_default: bool = False) -> None:
        """
        Register a cloud provider.
        
        Args:
            provider: Provider instance to register
            set_as_default: Whether to set as the default provider
        """
        self._providers[provider.provider_name] = provider
        
        if set_as_default or self._default_provider is None:
            self._default_provider = provider
    
    def get(self, provider_name: str) -> Optional[BaseCloudProvider]:
        """Get a provider by name."""
        return self._providers.get(provider_name)
    
    def get_default(self) -> Optional[BaseCloudProvider]:
        """Get the default provider."""
        return self._default_provider
    
    def get_provider_for_resource(self, resource_name: str) -> Optional[BaseCloudProvider]:
        """
        Get the appropriate provider for a resource.
        
        Args:
            resource_name: Name of the resource
            
        Returns:
            Provider that can handle this resource, or None if not found
        """
        for provider in self._providers.values():
            if provider.is_resource_of_provider(resource_name):
                return provider
        
        return self._default_provider
    
    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())
    
    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()
        self._default_provider = None


# Global registry instance
_provider_registry = CloudProviderRegistry()


def register_provider(provider: BaseCloudProvider, set_as_default: bool = False) -> None:
    """Register a cloud provider with the global registry."""
    _provider_registry.register(provider, set_as_default)


def get_provider(provider_name: str) -> Optional[BaseCloudProvider]:
    """Get a provider by name from the global registry."""
    return _provider_registry.get(provider_name)


def get_provider_for_resource(resource_name: str) -> Optional[BaseCloudProvider]:
    """Get the appropriate provider for a resource from the global registry."""
    return _provider_registry.get_provider_for_resource(resource_name)


def get_default_provider() -> Optional[BaseCloudProvider]:
    """Get the default provider from the global registry."""
    return _provider_registry.get_default()


def list_providers() -> List[str]:
    """List all registered providers."""
    return _provider_registry.list_providers()
