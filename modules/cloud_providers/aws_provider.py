"""
AWS cloud provider implementation for TerraVision.

This module implements the BaseCloudProvider interface for Amazon Web Services,
providing AWS-specific resource handling, relationships, and visualization logic.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

from . import BaseCloudProvider
import modules.cloud_config as cloud_config


logger = logging.getLogger(__name__)


class AWSProvider(BaseCloudProvider):
    """AWS cloud provider implementation."""
    
    @property
    def provider_name(self) -> str:
        """Return the name of the AWS provider."""
        return "aws"
    
    @property
    def resource_prefix(self) -> str:
        """Return the resource prefix for AWS resources."""
        return "aws_"
    
    @property
    def reverse_arrow_list(self) -> List[str]:
        """Return list of AWS resources that should have reversed arrow directions."""
        return cloud_config.AWS_REVERSE_ARROW_LIST
    
    @property
    def implied_connections(self) -> Dict[str, str]:
        """Return mapping of keywords to implied AWS resource connections."""
        return cloud_config.AWS_IMPLIED_CONNECTIONS
    
    @property
    def group_nodes(self) -> Set[str]:
        """Return set of AWS resource types that should be treated as groups."""
        return set(cloud_config.AWS_GROUP_NODES)
    
    @property
    def consolidated_nodes(self) -> Dict[str, str]:
        """Return mapping of AWS resources that should be consolidated."""
        return cloud_config.AWS_CONSOLIDATED_NODES
    
    @property
    def special_resources(self) -> Dict[str, str]:
        """Return mapping of AWS resource types to their special handler functions."""
        return cloud_config.AWS_SPECIAL_RESOURCES
    
    @property
    def shared_services(self) -> Set[str]:
        """Return set of AWS resource types that are shared services."""
        return set(cloud_config.AWS_SHARED_SERVICES)
    
    def get_resource_variant(self, resource_name: str, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Determine the variant of an AWS resource based on its metadata.
        
        This method analyzes AWS resource metadata to determine specific variants
        like instance types, storage types, database engines, etc.
        
        Args:
            resource_name: Name of the AWS resource
            metadata: Resource metadata dictionary
            
        Returns:
            Variant name if applicable, None otherwise
        """
        try:
            resource_type = resource_name.split(".")[0]
            
            # EC2 instance variants based on instance type
            if resource_type == "aws_instance":
                instance_type = metadata.get("instance_type", "")
                if instance_type:
                    # Map instance families to variants
                    if instance_type.startswith("t"):
                        return "aws_ec2_t_instance"
                    elif instance_type.startswith("m"):
                        return "aws_ec2_m_instance" 
                    elif instance_type.startswith("c"):
                        return "aws_ec2_c_instance"
                    elif instance_type.startswith("r"):
                        return "aws_ec2_r_instance"
                    elif instance_type.startswith("x"):
                        return "aws_ec2_x_instance"
                    
            # RDS variants based on engine
            elif resource_type == "aws_db_instance":
                engine = metadata.get("engine", "")
                if "mysql" in engine:
                    return "aws_rds_mysql_instance"
                elif "postgres" in engine:
                    return "aws_rds_postgresql_instance"
                elif "oracle" in engine:
                    return "aws_rds_oracle_instance"
                elif "mariadb" in engine:
                    return "aws_rds_mariadb_instance"
                elif "sqlserver" in engine:
                    return "aws_rds_sqlserver_instance"
                    
            # ELB variants based on type
            elif resource_type == "aws_lb":
                load_balancer_type = metadata.get("load_balancer_type", "")
                if load_balancer_type == "application":
                    return "aws_elb_application_load_balancer"
                elif load_balancer_type == "network":
                    return "aws_elb_network_load_balancer"
                elif load_balancer_type == "gateway":
                    return "aws_elb_gateway_load_balancer"
                    
            # S3 variants based on storage class
            elif resource_type == "aws_s3_bucket":
                storage_class = metadata.get("storage_class", "")
                if storage_class == "GLACIER":
                    return "aws_s3_glacier"
                elif storage_class == "DEEP_ARCHIVE":
                    return "aws_s3_deep_archive"
                elif storage_class == "INTELLIGENT_TIERING":
                    return "aws_s3_intelligent_tiering"
                    
            # Lambda variants based on runtime
            elif resource_type == "aws_lambda_function":
                runtime = metadata.get("runtime", "")
                if runtime.startswith("python"):
                    return "aws_lambda_python"
                elif runtime.startswith("node"):
                    return "aws_lambda_nodejs" 
                elif runtime.startswith("java"):
                    return "aws_lambda_java"
                elif runtime.startswith("dotnet"):
                    return "aws_lambda_dotnet"
                elif runtime.startswith("go"):
                    return "aws_lambda_go"
                    
            return None
            
        except Exception as e:
            logger.warning(f"Error determining variant for {resource_name}: {e}")
            return None
    
    def get_resource_icon_path(self, resource_type: str, variant: Optional[str] = None) -> str:
        """
        Get the icon path for an AWS resource type.
        
        Args:
            resource_type: Type of AWS resource (e.g., 'aws_ec2_instance')
            variant: Optional variant of the resource
            
        Returns:
            Path to the resource icon
        """
        base_path = Path("resource_images/aws")
        
        # Use variant icon if available
        if variant:
            variant_path = base_path / self._get_icon_category(variant) / f"{variant.replace('aws_', '')}.png"
            if variant_path.exists():
                return str(variant_path)
        
        # Fall back to base resource type icon
        category = self._get_icon_category(resource_type)
        icon_name = resource_type.replace("aws_", "") + ".png"
        icon_path = base_path / category / icon_name
        
        if icon_path.exists():
            return str(icon_path)
        
        # Final fallback to generic icon
        return str(base_path / "general" / "general.png")
    
    def _get_icon_category(self, resource_type: str) -> str:
        """Get the icon category directory for a resource type."""
        # Map AWS resource types to icon categories
        category_mapping = {
            # Compute
            "aws_instance": "compute",
            "aws_ec2": "compute", 
            "aws_lambda": "compute",
            "aws_ecs": "compute",
            "aws_eks": "compute",
            "aws_batch": "compute",
            
            # Networking
            "aws_vpc": "network",
            "aws_subnet": "network",
            "aws_route": "network",
            "aws_nat": "network",
            "aws_internet": "network",
            "aws_elb": "network",
            "aws_lb": "network",
            "aws_cloudfront": "network",
            "aws_api_gateway": "network",
            
            # Storage  
            "aws_s3": "storage",
            "aws_ebs": "storage",
            "aws_efs": "storage",
            "aws_fsx": "storage",
            
            # Database
            "aws_rds": "database", 
            "aws_dynamodb": "database",
            "aws_redshift": "database",
            "aws_elasticache": "database",
            
            # Security
            "aws_iam": "security",
            "aws_kms": "security",
            "aws_secrets": "security",
            "aws_waf": "security",
            "aws_security": "security",
            
            # Analytics
            "aws_kinesis": "analytics",
            "aws_athena": "analytics",
            "aws_glue": "analytics",
            "aws_emr": "analytics",
            
            # Management
            "aws_cloudwatch": "management",
            "aws_cloudtrail": "management",
            "aws_config": "management",
            "aws_systems": "management",
        }
        
        # Find matching category
        for prefix, category in category_mapping.items():
            if resource_type.startswith(prefix):
                return category
        
        return "general"  # Default category
    
    def should_consolidate(self, resource_name: str) -> Optional[str]:
        """
        Check if an AWS resource should be consolidated.
        
        Args:
            resource_name: Name of the resource to check
            
        Returns:
            Consolidated name if resource should be consolidated, None otherwise
        """
        # Check against AWS consolidated nodes configuration
        for pattern, consolidated_name in self.consolidated_nodes.items():
            if pattern in resource_name:
                return consolidated_name
        
        return None
    
    def get_forced_destinations(self) -> Set[str]:
        """Return set of AWS resource types that should be forced as destinations."""
        return set(cloud_config.AWS_FORCED_DEST)
    
    def get_forced_origins(self) -> Set[str]:
        """Return set of AWS resource types that should be forced as origins."""
        return set(cloud_config.AWS_FORCED_ORIGIN)
    
    def get_resource_category(self, resource_type: str) -> str:
        """
        Get the category of an AWS resource type.
        
        Args:
            resource_type: Type of AWS resource
            
        Returns:
            Category name (compute, network, storage, etc.)
        """
        # AWS-specific categorization with more detail
        aws_categories = {
            # Compute services
            "compute": [
                "aws_instance", "aws_launch_template", "aws_launch_configuration",
                "aws_autoscaling_group", "aws_lambda_function", "aws_ecs_cluster",
                "aws_ecs_service", "aws_ecs_task_definition", "aws_eks_cluster",
                "aws_batch_compute_environment", "aws_batch_job_queue"
            ],
            
            # Networking services  
            "network": [
                "aws_vpc", "aws_subnet", "aws_route_table", "aws_route",
                "aws_internet_gateway", "aws_nat_gateway", "aws_vpn_gateway",
                "aws_customer_gateway", "aws_vpn_connection", "aws_vpc_peering_connection",
                "aws_lb", "aws_elb", "aws_lb_target_group", "aws_cloudfront_distribution",
                "aws_api_gateway", "aws_route53_zone", "aws_route53_record"
            ],
            
            # Storage services
            "storage": [
                "aws_s3_bucket", "aws_ebs_volume", "aws_efs_file_system",
                "aws_fsx_file_system", "aws_glacier_vault", "aws_backup_vault"
            ],
            
            # Database services
            "database": [
                "aws_db_instance", "aws_db_cluster", "aws_rds_cluster",
                "aws_dynamodb_table", "aws_redshift_cluster", "aws_elasticache_cluster",
                "aws_neptune_cluster", "aws_docdb_cluster"
            ],
            
            # Security services
            "security": [
                "aws_iam_role", "aws_iam_policy", "aws_iam_user", "aws_iam_group",
                "aws_security_group", "aws_kms_key", "aws_secretsmanager_secret",
                "aws_waf_web_acl", "aws_shield_protection", "aws_guardduty_detector"
            ],
            
            # Analytics services
            "analytics": [
                "aws_kinesis_stream", "aws_kinesis_firehose_delivery_stream",
                "aws_kinesis_analytics_application", "aws_athena_database",
                "aws_glue_catalog_database", "aws_glue_job", "aws_emr_cluster",
                "aws_elasticsearch_domain", "aws_quicksight_analysis"
            ],
            
            # Management services
            "management": [
                "aws_cloudwatch_log_group", "aws_cloudwatch_metric_alarm",
                "aws_cloudtrail", "aws_config_configuration_recorder",
                "aws_systems_manager_parameter", "aws_sns_topic", "aws_sqs_queue"
            ]
        }
        
        # Find category for resource type
        for category, resource_types in aws_categories.items():
            for rt in resource_types:
                if resource_type.startswith(rt):
                    return category
        
        # Fall back to parent class implementation
        return super().get_resource_category(resource_type)
    
    def get_service_limits(self) -> Dict[str, Dict[str, Any]]:
        """
        Get AWS service limits and quotas.
        
        Returns:
            Dictionary of service limits by resource type
        """
        return {
            "aws_instance": {
                "default_limit": 20,
                "max_limit": 1000,
                "limit_type": "running_instances"
            },
            "aws_vpc": {
                "default_limit": 5,
                "max_limit": 100,
                "limit_type": "vpcs_per_region"
            },
            "aws_s3_bucket": {
                "default_limit": 100,
                "max_limit": 1000,
                "limit_type": "buckets_per_account"
            },
            # Add more service limits as needed
        }
    
    def validate_resource_configuration(self, resource_type: str, config: Dict[str, Any]) -> List[str]:
        """
        Validate AWS resource configuration for common issues.
        
        Args:
            resource_type: Type of AWS resource
            config: Resource configuration dictionary
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # EC2 instance validation
        if resource_type == "aws_instance":
            if not config.get("instance_type"):
                warnings.append("Instance type not specified")
            
            ami = config.get("ami")
            if not ami:
                warnings.append("AMI not specified")
            elif not ami.startswith("ami-"):
                warnings.append("Invalid AMI format")
        
        # S3 bucket validation
        elif resource_type == "aws_s3_bucket":
            bucket_name = config.get("bucket")
            if bucket_name:
                if len(bucket_name) < 3 or len(bucket_name) > 63:
                    warnings.append("S3 bucket name must be between 3 and 63 characters")
                if not bucket_name.islower():
                    warnings.append("S3 bucket name should be lowercase")
        
        # VPC validation
        elif resource_type == "aws_vpc":
            cidr = config.get("cidr_block")
            if cidr and not self._is_valid_cidr(cidr):
                warnings.append("Invalid CIDR block format")
        
        return warnings
    
    def _is_valid_cidr(self, cidr: str) -> bool:
        """Validate CIDR block format."""
        try:
            import ipaddress
            ipaddress.IPv4Network(cidr, strict=False)
            return True
        except ValueError:
            return False
