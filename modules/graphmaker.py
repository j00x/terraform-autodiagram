"""
Graph maker module for TerraVision.

This module handles the creation and manipulation of Terraform resource graphs,
including relationship detection, node consolidation, and resource multiplicity handling.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import click
import modules.cloud_config as cloud_config
import modules.helpers as helpers
import modules.resource_handlers as resource_handlers

# Configure logging
logger = logging.getLogger(__name__)

# Cloud provider configuration constants
REVERSE_ARROW_LIST = cloud_config.AWS_REVERSE_ARROW_LIST
IMPLIED_CONNECTIONS = cloud_config.AWS_IMPLIED_CONNECTIONS
GROUP_NODES = cloud_config.AWS_GROUP_NODES
CONSOLIDATED_NODES = cloud_config.AWS_CONSOLIDATED_NODES
NODE_VARIANTS = cloud_config.AWS_NODE_VARIANTS
SPECIAL_RESOURCES = cloud_config.AWS_SPECIAL_RESOURCES
SHARED_SERVICES = cloud_config.AWS_SHARED_SERVICES
AUTO_ANNOTATIONS = cloud_config.AWS_AUTO_ANNOTATIONS
EDGE_NODES = cloud_config.AWS_EDGE_NODES
FORCED_DEST = cloud_config.AWS_FORCED_DEST
FORCED_ORIGIN = cloud_config.AWS_FORCED_ORIGIN


def reverse_relations(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reverse relationship directions for certain resources based on configuration.
    
    Some resources in Terraform graphs need their connection directions reversed
    to better represent the actual data flow or dependency relationships.
    
    Args:
        tfdata: Dictionary containing graph data and metadata
        
    Returns:
        Modified tfdata with reversed relationships
        
    Raises:
        KeyError: If required keys are missing from tfdata
    """
    try:
        logger.debug("Starting relationship reversal process")
        
        for n, connections in dict(tfdata["graphdict"]).items():
            node = helpers.get_no_module_name(n)
            reverse_dest = len([s for s in FORCED_DEST if node.startswith(s)]) > 0
            
            for c in list(connections):
                if reverse_dest:
                    _reverse_destination_connection(tfdata, n, c)
                
                if _should_reverse_origin_connection(node, c):
                    _reverse_origin_connection(tfdata, node, c)
        
        logger.debug("Completed relationship reversal process")
        return tfdata
        
    except KeyError as e:
        logger.error(f"Missing required key in tfdata: {e}")
        raise
    except Exception as e:
        logger.error(f"Error during relationship reversal: {e}")
        raise


def _reverse_destination_connection(tfdata: Dict[str, Any], source: str, dest: str) -> None:
    """Helper function to reverse destination connections."""
    if not tfdata["graphdict"].get(dest):
        tfdata["graphdict"][dest] = list()
    tfdata["graphdict"][dest].append(source)
    tfdata["graphdict"][source].remove(dest)


def _should_reverse_origin_connection(node: str, connection: str) -> bool:
    """Check if an origin connection should be reversed."""
    return len([
        s for s in FORCED_ORIGIN
        if helpers.get_no_module_name(connection).startswith(s)
        and not node.split(".")[0] in str(AUTO_ANNOTATIONS)
    ]) > 0


def _reverse_origin_connection(tfdata: Dict[str, Any], node: str, connection: str) -> None:
    """Helper function to reverse origin connections."""
    tfdata["graphdict"][connection].append(node)
    tfdata["graphdict"][node].remove(connection)


def check_relationship(
    resource_associated_with: str, plist: List[Any], tfdata: Dict[str, Any]
) -> List[str]:
    """
    Check whether a particular resource mentions another known resource (relationship).
    
    This function analyzes resource parameters to identify relationships between
    Terraform resources that may not be explicitly defined in the graph.
    
    Args:
        resource_associated_with: The resource being analyzed
        plist: List of parameters from the resource configuration
        tfdata: Dictionary containing graph data and metadata
        
    Returns:
        List containing pairs of related nodes where index i and i+1 are related
        
    Raises:
        KeyError: If required keys are missing from tfdata
    """
    try:
        logger.debug(f"Checking relationships for resource: {resource_associated_with}")
        
        nodes = tfdata["node_list"]
        hidden = tfdata["hidden"]
        connection_pairs = []
        
        for param in plist:
            # Find nodes referenced in this parameter
            matching_nodes = _find_matching_nodes(param, nodes)
            
            # Add implied connections based on keywords
            matching_nodes.extend(_find_implied_connections(param, nodes))
            
            if matching_nodes:
                connection_pairs.extend(
                    _process_matched_resources(
                        resource_associated_with, matching_nodes, param, tfdata, hidden
                    )
                )
        
        logger.debug(f"Found {len(connection_pairs)//2} relationships for {resource_associated_with}")
        return connection_pairs
        
    except Exception as e:
        logger.error(f"Error checking relationships for {resource_associated_with}: {e}")
        raise


def _find_matching_nodes(param: Any, nodes: List[str]) -> List[str]:
    """Find nodes that match references in the parameter."""
    matching = list({s for s in nodes if s.split("~")[0] in str(param)})
    matching.extend(list({s for s in nodes if helpers.get_no_module_name(s) in str(param)}))
    return list(set(matching))  # Remove duplicates


def _find_implied_connections(param: Any, nodes: List[str]) -> List[str]:
    """Find connections implied by keywords in the parameter."""
    found_connections = list({s for s in IMPLIED_CONNECTIONS.keys() if s in str(param)})
    implied_nodes = []
    
    for connection in found_connections:
        for node in nodes:
            if (helpers.get_no_module_name(node).startswith(IMPLIED_CONNECTIONS[connection])
                and node not in implied_nodes):
                implied_nodes.append(node)
    
    return implied_nodes


def _process_matched_resources(
    resource_associated_with: str, 
    matching_nodes: List[str], 
    param: Any, 
    tfdata: Dict[str, Any], 
    hidden: List[str]
) -> List[str]:
    """Process matched resources to determine connection pairs."""
    connection_pairs = []
    
    for matched_resource in matching_nodes:
        if matched_resource not in hidden and resource_associated_with not in hidden:
            reverse = _should_reverse_connection(resource_associated_with, param)
            
            # Validate numbered node relationships
            if not _validate_numbered_nodes(matched_resource, resource_associated_with):
                continue
            
            # Add connection pair based on direction
            if reverse:
                if _is_new_connection(resource_associated_with, matched_resource, tfdata):
                    connection_pairs.extend([matched_resource, resource_associated_with])
            else:
                if _is_new_connection(matched_resource, resource_associated_with, tfdata):
                    connection_pairs.extend([resource_associated_with, matched_resource])
    
    return connection_pairs


def _should_reverse_connection(resource_name: str, param: Any) -> bool:
    """Determine if connection should be reversed based on configuration."""
    reverse_origin_match = [s for s in REVERSE_ARROW_LIST if s in str(param)]
    if not reverse_origin_match:
        return False
    
    reverse_dest_match = [s for s in REVERSE_ARROW_LIST if s in resource_name]
    if reverse_dest_match:
        return (REVERSE_ARROW_LIST.index(reverse_dest_match[0]) 
                >= REVERSE_ARROW_LIST.index(reverse_origin_match[0]))
    
    return True


def _validate_numbered_nodes(matched_resource: str, resource_associated_with: str) -> bool:
    """Validate that numbered nodes are associated with connections of the same number."""
    if "~" in matched_resource and "~" in resource_associated_with:
        matched_resource_no = matched_resource.split("~")[1]
        resource_associated_with_no = resource_associated_with.split("~")[1]
        return matched_resource_no == resource_associated_with_no
    return True


def _is_new_connection(source: str, dest: str, tfdata: Dict[str, Any]) -> bool:
    """Check if this would be a new connection."""
    return (dest not in tfdata["graphdict"].get(source, []) 
            and source not in tfdata["graphdict"].get(dest, []))


def add_relations(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make final graph structure to be used for drawing by adding relationships.
    
    This function processes all nodes to identify and add relationships between
    resources based on their configuration parameters.
    
    Args:
        tfdata: Dictionary containing graph data and metadata
        
    Returns:
        Modified tfdata with enhanced relationships
        
    Raises:
        KeyError: If required keys are missing from tfdata
    """
    try:
        logger.info("Starting relationship addition process")
        
        # Start with an existing connections list for all nodes/resources we know about
        graphdict = dict(tfdata["graphdict"])
        created_resources = len(tfdata["node_list"])
        
        click.echo(
            click.style(
                f"\nChecking for additional links between {created_resources} resources..",
                fg="white",
                bold=True,
            )
        )
        
        # Determine relationship between resources and append to graphdict when found
        for node in tfdata["node_list"]:
            if _should_skip_node(node, tfdata):
                continue
                
            nodename = _get_node_name(node, tfdata)
            param_generator = _get_param_generator(node, nodename, tfdata)
            
            for param_item_list in param_generator:
                matching_result = check_relationship(node, param_item_list, tfdata)
                
                if matching_result and len(matching_result) >= 2:
                    _add_matching_connections(matching_result, graphdict)
        
        # Clean up hidden resources
        _cleanup_hidden_resources(tfdata, graphdict)
        
        tfdata["graphdict"] = graphdict
        logger.info("Completed relationship addition process")
        return tfdata
        
    except Exception as e:
        logger.error(f"Error during relationship addition: {e}")
        raise


def _should_skip_node(node: str, tfdata: Dict[str, Any]) -> bool:
    """Determine if a node should be skipped during relationship processing."""
    nodename = node.split("~")[0] if node not in tfdata["meta_data"].keys() else node
    if "[" in nodename:
        nodename = nodename.split("[")[0]
    
    return (
        helpers.get_no_module_name(nodename).startswith("random") or
        helpers.get_no_module_name(node).startswith("aws_security_group") or
        helpers.get_no_module_name(node).startswith("null")
    )


def _get_node_name(node: str, tfdata: Dict[str, Any]) -> str:
    """Get the appropriate node name for metadata lookup."""
    if node not in tfdata["meta_data"].keys():
        nodename = node.split("~")[0]
        if "[" in nodename:
            nodename = nodename.split("[")[0]
    else:
        nodename = node
    return nodename


def _get_param_generator(node: str, nodename: str, tfdata: Dict[str, Any]):
    """Get parameter generator for the node."""
    if nodename not in tfdata["meta_data"].keys():
        tfdata["meta_data"][node] = tfdata["original_metadata"][node]
        return dict_generator(tfdata["original_metadata"][node])
    else:
        return dict_generator(tfdata["meta_data"][nodename])


def _add_matching_connections(matching_result: List[str], graphdict: Dict[str, List[str]]) -> None:
    """Add connections from matching results to the graph dictionary."""
    for i in range(0, len(matching_result), 2):
        origin = matching_result[i]
        dest = matching_result[i + 1]
        c_list = list(graphdict[origin])
        
        if (not dest in c_list and 
            not helpers.get_no_module_name(origin).startswith("aws_security_group")):
            click.echo(f"   {origin} --> {dest}")
            c_list.append(dest)
            
            # Handle numbered node cleanup
            if ("~" in origin and "~" in dest and dest.split("~")[0] in c_list):
                c_list.remove(dest.split("~")[0])
        
        graphdict[origin] = c_list


def _cleanup_hidden_resources(tfdata: Dict[str, Any], graphdict: Dict[str, List[str]]) -> None:
    """Remove hidden resources from the graph."""
    # Hide nodes where specified
    for hidden_resource in tfdata["hidden"]:
        if hidden_resource in graphdict:
            del graphdict[hidden_resource]
    
    # Remove hidden resources from connection lists
    for resource in graphdict:
        for hidden_resource in tfdata["hidden"]:
            if hidden_resource in graphdict[resource]:
                graphdict[resource].remove(hidden_resource)


def consolidate_nodes(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Consolidate multiple related nodes into single logical nodes.
    
    This function groups related resources together based on configuration
    to create a cleaner, more logical diagram structure.
    
    Args:
        tfdata: Dictionary containing graph data and metadata
        
    Returns:
        Modified tfdata with consolidated nodes
    """
    try:
        logger.info("Starting node consolidation process")
        
        for resource in dict(tfdata["graphdict"]):
            if "null_resource" in resource:
                del tfdata["graphdict"][resource]
                continue
            
            # Get resource metadata
            res, resdata = _get_resource_data(resource, tfdata)
            
            # Check if this resource should be consolidated
            consolidated_name = helpers.consolidated_node_check(resource)
            if consolidated_name:
                _consolidate_resource(resource, consolidated_name, resdata, tfdata)
                connected_resource = consolidated_name
            else:
                connected_resource = resource
            
            # Update connections to use consolidated names
            _update_consolidated_connections(connected_resource, tfdata)
        
        logger.info("Completed node consolidation process")
        return tfdata
        
    except Exception as e:
        logger.error(f"Error during node consolidation: {e}")
        raise


def _get_resource_data(resource: str, tfdata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Get resource name and data for consolidation processing."""
    if resource not in tfdata["meta_data"].keys():
        res = resource.split("~")[0]
    else:
        res = resource
        
    if "[" in res:
        res = res.split("[")[0]
    
    if tfdata["meta_data"].get(res):
        resdata = tfdata["meta_data"].get(res)
    else:
        resdata = tfdata["meta_data"][resource]
    
    return res, resdata


def _consolidate_resource(
    resource: str, 
    consolidated_name: str, 
    resdata: Dict[str, Any], 
    tfdata: Dict[str, Any]
) -> None:
    """Consolidate a single resource into a consolidated node."""
    if not tfdata["meta_data"].get(consolidated_name):
        tfdata["graphdict"][consolidated_name] = list()
        tfdata["meta_data"][consolidated_name] = dict()
    
    # Merge metadata (don't override count values with 0)
    tfdata["meta_data"][consolidated_name] = dict(
        tfdata["meta_data"][consolidated_name] | resdata
    )
    
    # Merge connections
    tfdata["graphdict"][consolidated_name] = list(
        set(tfdata["graphdict"][consolidated_name]) | 
        set(tfdata["graphdict"][resource])
    )
    
    del tfdata["graphdict"][resource]


def _update_consolidated_connections(connected_resource: str, tfdata: Dict[str, Any]) -> None:
    """Update connections to use consolidated resource names."""
    for index, connection in enumerate(tfdata["graphdict"][connected_resource]):
        consolidated_connection = helpers.consolidated_node_check(connection)
        
        if consolidated_connection and consolidated_connection != connection:
            if (_can_replace_connection(consolidated_connection, connected_resource, tfdata)):
                tfdata["graphdict"][connected_resource][index] = consolidated_connection
            elif _should_remove_connection(consolidated_connection, connected_resource, tfdata):
                tfdata["graphdict"][connected_resource].insert(index, "null")
                tfdata["graphdict"][connected_resource].remove(connection)
    
    # Clean up null entries
    if "null" in tfdata["graphdict"][connected_resource]:
        tfdata["graphdict"][connected_resource] = list(
            filter(lambda a: a != "null", tfdata["graphdict"][connected_resource])
        )


def _can_replace_connection(consolidated_connection: str, connected_resource: str, tfdata: Dict[str, Any]) -> bool:
    """Check if a connection can be replaced with its consolidated version."""
    return (consolidated_connection not in tfdata["graphdict"][connected_resource] and
            connected_resource not in consolidated_connection)


def _should_remove_connection(consolidated_connection: str, connected_resource: str, tfdata: Dict[str, Any]) -> bool:
    """Check if a connection should be removed due to consolidation."""
    return (connected_resource in consolidated_connection or
            consolidated_connection in tfdata["graphdict"][connected_resource])


def handle_variants(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle resource variants by renaming nodes based on their specific configurations.
    
    AWS resources often have variants (like different instance types) that should
    be represented with specific icons or names in the diagram.
    
    Args:
        tfdata: Dictionary containing graph data and metadata
        
    Returns:
        Modified tfdata with variant handling applied
    """
    try:
        logger.info("Starting variant handling process")
        
        # Loop through all top level nodes and rename if variants exist
        for node in dict(tfdata["graphdict"]):
            renamed_node = _process_node_variant(node, tfdata)
            
            # Go through each connection and rename variants
            _process_connection_variants(renamed_node, node, tfdata)
        
        logger.info("Completed variant handling process")
        return tfdata
        
    except Exception as e:
        logger.error(f"Error during variant handling: {e}")
        raise


def _process_node_variant(node: str, tfdata: Dict[str, Any]) -> str:
    """Process variant for a single node."""
    node_title = helpers.get_no_module_name(node).split(".")[1]
    node_name = node.split("~")[0] if (node[-1].isdigit() and node[-2] == "~") else node
    
    if helpers.get_no_module_name(node_name).startswith("aws"):
        renamed_node = helpers.check_variant(node, tfdata["meta_data"].get(node_name))
    else:
        renamed_node = False
    
    if (renamed_node and 
        helpers.get_no_module_name(node).split(".")[0] not in SPECIAL_RESOURCES.keys()):
        renamed_node = renamed_node + "." + node_title
        tfdata["graphdict"][renamed_node] = list(tfdata["graphdict"][node])
        del tfdata["graphdict"][node]
        return renamed_node
    
    return node


def _process_connection_variants(renamed_node: str, original_node: str, tfdata: Dict[str, Any]) -> None:
    """Process variants for all connections of a node."""
    for resource in list(tfdata["graphdict"][renamed_node]):
        resource_name = resource.split("~")[0] if "~" in resource else resource
        
        if helpers.get_no_module_name(resource_name).startswith("aws"):
            variant_suffix = helpers.check_variant(resource, tfdata["meta_data"].get(resource_name))
            variant_label = resource.split(".")[1]
        else:
            variant_suffix = None
        
        if _should_apply_variant(variant_suffix, resource, renamed_node, original_node, tfdata):
            _apply_connection_variant(resource, variant_suffix, variant_label, renamed_node, tfdata)


def _should_apply_variant(
    variant_suffix: Optional[str], 
    resource: str, 
    renamed_node: str, 
    original_node: str, 
    tfdata: Dict[str, Any]
) -> bool:
    """Check if variant should be applied to a connection."""
    if not variant_suffix:
        return False
    
    return (helpers.get_no_module_name(resource).split(".")[0] not in SPECIAL_RESOURCES.keys() and
            not renamed_node.startswith("aws_group.shared") and
            (resource not in tfdata["graphdict"].get("aws_group.shared_services", []) or "~" in original_node) and
            resource.split(".")[0] != original_node.split(".")[0])


def _apply_connection_variant(
    resource: str, 
    variant_suffix: str, 
    variant_label: str, 
    renamed_node: str, 
    tfdata: Dict[str, Any]
) -> None:
    """Apply variant to a specific connection."""
    new_list = list(tfdata["graphdict"][renamed_node])
    new_list.remove(resource)
    new_variant_name = variant_suffix + "." + variant_label
    new_list.append(new_variant_name)
    tfdata["graphdict"][renamed_node] = new_list
    tfdata["meta_data"][new_variant_name] = tfdata["meta_data"][resource]


def handle_special_resources(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle resources which require pre/post-processing before/after being added to graphdict.
    
    Some resources have special handling requirements that can't be covered by the
    standard processing pipeline.
    
    Args:
        tfdata: Dictionary containing graph data and metadata
        
    Returns:
        Modified tfdata with special resource handling applied
    """
    try:
        logger.info("Starting special resource handling")
        
        resource_types = list(
            {helpers.get_no_module_name(k).split(".")[0] for k in tfdata["node_list"]}
        )
        
        for resource_prefix, handler in SPECIAL_RESOURCES.items():
            matching_substring = [s for s in resource_types if resource_prefix in s]
            if resource_prefix in resource_types or matching_substring:
                logger.debug(f"Applying special handler {handler} for {resource_prefix}")
                tfdata = getattr(resource_handlers, handler)(tfdata)
        
        logger.info("Completed special resource handling")
        return tfdata
        
    except Exception as e:
        logger.error(f"Error during special resource handling: {e}")
        raise


def dict_generator(indict: Any, pre: Optional[List[str]] = None) -> Any:
    """
    Generator function to crawl entire dict and load all dict and list values.
    
    This recursive generator walks through nested dictionaries and lists to
    extract all parameter paths and values for relationship analysis.
    
    Args:
        indict: Input dictionary or value to process
        pre: Prefix path accumulated during recursion
        
    Yields:
        Parameter paths and values from the nested structure
    """
    pre = pre[:] if pre else []
    
    if isinstance(indict, dict):
        for key, value in indict.items():
            if isinstance(value, dict):
                for d in dict_generator(value, pre + [key]):
                    yield d
            elif isinstance(value, (list, tuple)):
                for v in value:
                    for d in dict_generator(v, pre + [key]):
                        yield d
            else:
                yield pre + [key, value]
    else:
        yield pre + [indict]


def create_multiple_resources(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle resources with count, for_each, or other multiplicity attributes.
    
    This function creates multiple numbered instances of resources that are
    configured to have multiple copies (e.g., count > 1, for_each loops).
    
    Args:
        tfdata: Dictionary containing graph data and metadata
        
    Returns:
        Modified tfdata with multiple resource instances
    """
    try:
        logger.info("Starting multiple resource creation")
        
        # Get a list of all potential resources with a count type attribute
        multi_resources = _identify_multi_resources(tfdata)
        
        # Create multiple nodes for count resources as necessary
        tfdata = _handle_count_resources(multi_resources, tfdata)
        
        # Replace links to single nodes with multi nodes if they exist
        tfdata = _handle_singular_references(tfdata)
        
        # Clean up original resource names
        tfdata = _cleanup_original_resources(multi_resources, tfdata)
        
        # Handle creation of multiple security groups where needed
        tfdata = _extend_sg_groups(tfdata)
        
        logger.info("Completed multiple resource creation")
        return tfdata
        
    except Exception as e:
        logger.error(f"Error during multiple resource creation: {e}")
        raise


def _identify_multi_resources(tfdata: Dict[str, Any]) -> List[str]:
    """Identify resources that should have multiple instances."""
    return [
        n for n in tfdata["graphdict"]
        if ("~" not in n and
            tfdata["meta_data"].get(n) and
            (tfdata["meta_data"][n].get("count") or
             tfdata["meta_data"][n].get("desired_count") or
             tfdata["meta_data"][n].get("max_capacity") or
             tfdata["meta_data"][n].get("for_each")) and
            not helpers.consolidated_node_check(n))
    ]


def _handle_count_resources(multi_resources: List[str], tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """Handle resources with count attributes by creating multiple instances."""
    for resource in multi_resources:
        # TODO: Properly determine max_i based on AZs and subnets
        max_i = 3
        
        for i in range(max_i):
            # Get connections replaced with numbered suffixes
            resource_i = _add_number_suffix(i + 1, resource, tfdata)
            not_shared_service = resource.split(".")[0] not in SHARED_SERVICES
            
            if not_shared_service:
                # Create a top level node with number suffix and connect to numbered connections
                tfdata["graphdict"][resource + "~" + str(i + 1)] = resource_i
                tfdata["meta_data"][resource + "~" + str(i + 1)] = tfdata["meta_data"][resource]
                tfdata = _add_multiples_to_parents(i, resource, multi_resources, tfdata)
                
                # Check if numbered connection node exists as a top level node in graphdict
                tfdata = _create_numbered_connection_nodes(resource_i, i, multi_resources, tfdata)
    
    return tfdata


def _add_number_suffix(i: int, check_multiple_resource: str, tfdata: Dict[str, Any]) -> List[str]:
    """Add number suffix to connections where appropriate."""
    if not helpers.list_of_dictkeys_containing(tfdata["graphdict"], check_multiple_resource):
        return []
    
    new_list = list(tfdata["graphdict"][check_multiple_resource])
    
    for resource in list(tfdata["graphdict"][check_multiple_resource]):
        matching_resource_list = helpers.list_of_dictkeys_containing(tfdata["graphdict"], resource)
        
        for res in matching_resource_list:
            if _should_add_numbered_suffix(res, i, resource, check_multiple_resource, tfdata, new_list):
                new_list.append(res)
                if resource in new_list:
                    new_list.remove(resource)
    
    return new_list


def _should_add_numbered_suffix(
    res: str, 
    i: int, 
    resource: str, 
    check_multiple_resource: str, 
    tfdata: Dict[str, Any], 
    new_list: List[str]
) -> bool:
    """Check if a numbered suffix should be added to a resource."""
    return ("~" in res and
            res.split("~")[1] == str(i) and  # matching seq number suffix
            res not in new_list and
            (_needs_multiple(helpers.get_no_module_name(res), check_multiple_resource, tfdata) or
             res in tfdata["graphdict"].keys()) and
            res not in tfdata["graphdict"][check_multiple_resource])


def _needs_multiple(resource: str, parent: str, tfdata: Dict[str, Any]) -> bool:
    """Determine if a resource needs multiple instances."""
    target_resource = (helpers.consolidated_node_check(resource)
                      if helpers.consolidated_node_check(resource) and tfdata["meta_data"].get(resource)
                      else resource)
    
    any_parent_has_count = helpers.any_parent_has_count(tfdata, resource)
    target_is_group = target_resource.split(".")[0] in GROUP_NODES
    target_has_count = (tfdata["meta_data"].get(target_resource, {}).get("count") and
                       int(tfdata["meta_data"][target_resource].get("count", 0)) >= 1)
    not_already_multiple = "~" not in target_resource
    no_special_handler = (resource.split(".")[0] not in SPECIAL_RESOURCES.keys() or
                         resource.split(".")[0] in GROUP_NODES)
    not_shared_service = resource.split(".")[0] not in SHARED_SERVICES
    
    if helpers.get_no_module_name(resource).split(".")[0] == "aws_security_group":
        security_group_with_count = (tfdata["original_metadata"].get(parent, {}).get("count") and
                                   int(tfdata["original_metadata"][parent].get("count", 0)) > 1)
    else:
        security_group_with_count = False
    
    has_variant = helpers.check_variant(resource, tfdata["meta_data"].get(resource, {}))
    not_unique_resource = "aws_route_table." not in resource
    
    return (((target_is_group and target_has_count) or
             security_group_with_count or
             (any_parent_has_count and (has_variant or target_has_count)) or
             (target_has_count and any_parent_has_count)) and
            not_already_multiple and no_special_handler and not_shared_service and not_unique_resource)


def _add_multiples_to_parents(
    i: int, 
    resource: str, 
    multi_resources: List[str], 
    tfdata: Dict[str, Any]
) -> Dict[str, Any]:
    """Add numbered resource instances to their parent resources."""
    parents_list = helpers.list_of_parents(tfdata["graphdict"], resource)
    
    # Add numbered name to all original parents which may have been missed due to no count property
    for parent in parents_list:
        if parent not in multi_resources:
            suffixed_name = _get_suffixed_name(parent, resource, i)
            
            if _should_add_to_parent(parent, suffixed_name, resource, tfdata):
                _handle_security_group_special_case(parent, resource, suffixed_name, i, tfdata)
                _add_suffixed_resource_to_parent(parent, resource, suffixed_name, tfdata)
    
    return tfdata


def _get_suffixed_name(parent: str, resource: str, i: int) -> str:
    """Generate the appropriate suffixed name for a resource."""
    if "~" in parent:
        # We have a suffix so check it matches the i count
        existing_suffix = parent.split("~")[1]
        if existing_suffix == str(i + 1):
            return resource + "~" + str(i + 1)
        else:
            return resource + "~" + existing_suffix
    elif "~" not in resource:
        return resource + "~" + str(i + 1)
    else:
        return resource


def _should_add_to_parent(parent: str, suffixed_name: str, resource: str, tfdata: Dict[str, Any]) -> bool:
    """Check if a suffixed resource should be added to its parent."""
    return (parent.split("~")[0] in tfdata["meta_data"].keys() and
            tfdata["meta_data"][parent.split("~")[0]].get("count") and
            not parent.startswith("aws_group.shared") and
            suffixed_name not in tfdata["graphdict"][parent] and
            not ("cluster" in suffixed_name and "cluster" in parent) and
            "aws_route_table." not in resource)


def _handle_security_group_special_case(parent: str, resource: str, suffixed_name: str, i: int, tfdata: Dict[str, Any]) -> None:
    """Handle special case for security groups where parent has count > 1."""
    if _is_security_group_special_case(parent, resource, tfdata):
        if parent + "~" + str(i + 1) not in tfdata["graphdict"].keys() and "~" not in parent:
            tfdata["graphdict"][parent + "~" + str(i + 1)] = list(tfdata["graphdict"][parent])
        
        if tfdata["graphdict"].get(parent + "~" + str(i + 1)) and "~" not in parent:
            if suffixed_name not in tfdata["graphdict"][parent + "~" + str(i + 1)]:
                tfdata["graphdict"][parent + "~" + str(i + 1)].append(suffixed_name)
            if resource in tfdata["graphdict"][parent + "~" + str(i + 1)]:
                tfdata["graphdict"][parent + "~" + str(i + 1)].remove(resource)
            tfdata["meta_data"][parent + "~" + str(i + 1)] = tfdata["meta_data"][parent]


def _is_security_group_special_case(parent: str, resource: str, tfdata: Dict[str, Any]) -> bool:
    """Check if this is a security group special case."""
    return ((helpers.any_parent_has_count(tfdata, resource) and
             helpers.get_no_module_name(parent).split(".")[0] == "aws_security_group" and
             "~" not in parent) or
            (helpers.any_parent_has_count(tfdata, resource) and
             helpers.get_no_module_name(parent).split(".")[0] == "aws_security_group" and
             "~" in parent and
             helpers.check_list_for_dash(tfdata["graphdict"][parent])))


def _add_suffixed_resource_to_parent(parent: str, resource: str, suffixed_name: str, tfdata: Dict[str, Any]) -> None:
    """Add a suffixed resource to its parent if not security group special case."""
    if not _is_security_group_special_case(parent, resource, tfdata):
        if resource in tfdata["graphdict"][parent]:
            tfdata["graphdict"][parent].remove(resource)
        
        # Remove similar existing resources
        for sim in list(tfdata["graphdict"][parent]):
            if sim.split("~")[0] == suffixed_name.split("~")[0]:
                tfdata["graphdict"][parent].remove(sim)
        
        tfdata["graphdict"][parent].append(suffixed_name)


def _create_numbered_connection_nodes(resource_i: List[str], i: int, multi_resources: List[str], tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """Create numbered connection nodes as top level nodes in graphdict."""
    for numbered_node in resource_i:
        original_name = numbered_node.split("~")[0]
        
        if _should_create_numbered_node(numbered_node, original_name, multi_resources, tfdata):
            if i == 0:
                _handle_first_iteration(numbered_node, original_name, multi_resources, tfdata)
            else:
                _handle_subsequent_iterations(numbered_node, original_name, i, multi_resources, tfdata)
    
    return tfdata


def _should_create_numbered_node(numbered_node: str, original_name: str, multi_resources: List[str], tfdata: Dict[str, Any]) -> bool:
    """Check if a numbered node should be created."""
    return ("~" in numbered_node and
            helpers.list_of_dictkeys_containing(tfdata["graphdict"], original_name) and
            original_name not in multi_resources and
            not helpers.consolidated_node_check(original_name))


def _handle_first_iteration(numbered_node: str, original_name: str, multi_resources: List[str], tfdata: Dict[str, Any]) -> None:
    """Handle numbered node creation for first iteration."""
    if (original_name in tfdata["graphdict"].keys() and 
        original_name + "~1" not in tfdata["graphdict"].keys()):
        tfdata["graphdict"][numbered_node] = list(tfdata["graphdict"][original_name])
        tfdata = _add_multiples_to_parents(0, original_name, multi_resources, tfdata)
        del tfdata["graphdict"][original_name]


def _handle_subsequent_iterations(numbered_node: str, original_name: str, i: int, multi_resources: List[str], tfdata: Dict[str, Any]) -> None:
    """Handle numbered node creation for subsequent iterations."""
    if (original_name + "~" + str(i)) in tfdata["graphdict"] and numbered_node not in tfdata["graphdict"]:
        tfdata["graphdict"][numbered_node] = list(tfdata["graphdict"][original_name + "~" + str(i)])
    elif tfdata["graphdict"].get(original_name + "~" + str(i + 1)):
        tfdata["graphdict"][numbered_node] = list(tfdata["graphdict"][original_name + "~" + str(i + 1)])
    
    tfdata = _add_multiples_to_parents(i, original_name, multi_resources, tfdata)


def _handle_singular_references(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """Handle cases where a connection to only one of n numbered nodes exists."""
    for node, connections in dict(tfdata["graphdict"]).items():
        for c in list(connections):
            if "~" in node and "~" not in c:
                suffix = node.split("~")[1]
                suffixed_node = f"{c}~{suffix}"
                if suffixed_node in tfdata["graphdict"]:
                    tfdata["graphdict"][node].append(suffixed_node)
                    tfdata["graphdict"][node].remove(c)
            
            # If consolidated node, add all connections to node
            if "~" in c and helpers.consolidated_node_check(node):
                for i in range(1, int(c.split("~")[1]) + 4):
                    suffixed_node = f"{c.split('~')[0]}~{i}"
                    if (suffixed_node in tfdata["graphdict"] and
                        suffixed_node not in tfdata["graphdict"][node]):
                        tfdata["graphdict"][node].append(suffixed_node)
    
    return tfdata


def _cleanup_original_resources(multi_resources: List[str], tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """Clean up original resource names after creating multiples."""
    # Remove the original resource names
    for resource in multi_resources:
        if (helpers.list_of_dictkeys_containing(tfdata["graphdict"], resource) and
            resource.split(".")[0] not in SHARED_SERVICES):
            del tfdata["graphdict"][resource]
        
        parents_list = helpers.list_of_parents(tfdata["graphdict"], resource)
        for parent in parents_list:
            if (resource in tfdata["graphdict"][parent] and
                not parent.startswith("aws_group.shared") and
                "~" not in parent):
                tfdata["graphdict"][parent].remove(resource)
    
    # Delete any original security group nodes that have been replaced with numbered suffixes
    security_group_list = [
        k for k in tfdata["graphdict"]
        if helpers.get_no_module_name(k).startswith("aws_security_group") and "~" in k
    ]
    
    for security_group in security_group_list:
        check_original = security_group.split("~")[0]
        if check_original in tfdata["graphdict"].keys():
            del tfdata["graphdict"][check_original]
    
    return tfdata


def _extend_sg_groups(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """Handle creation of multiple security groups where needed."""
    list_of_sgs = [
        s for s in tfdata["graphdict"]
        if helpers.get_no_module_name(s).startswith("aws_security_group")
    ]
    
    for sg in list_of_sgs:
        expanded = False
        for connection in list(tfdata["graphdict"][sg]):
            if "~" in connection and "~" not in sg:
                expanded = True
                suffixed_sg = sg + "~" + connection.split("~")[1]
                tfdata["graphdict"][suffixed_sg] = [connection]
                tfdata["graphdict"][sg].remove(connection)
        
        if expanded:
            also_connected = helpers.list_of_parents(tfdata["graphdict"], sg)
            for node in also_connected:
                if "~" in node:
                    suffixed_sg = sg + "~" + node.split("~")[1]
                    tfdata["graphdict"][node].remove(sg)
                    tfdata["graphdict"][node].append(suffixed_sg)
                    
                    # Check if other multiples of the node also have the relationship
                    if "~1" in node:
                        _propagate_sg_relationships(node, sg, tfdata)
            
            del tfdata["graphdict"][sg]
    
    return tfdata


def _propagate_sg_relationships(node: str, sg: str, tfdata: Dict[str, Any]) -> None:
    """Propagate security group relationships to other numbered instances."""
    i = 2
    next_node = node.split("~")[0] + "~" + str(i)
    next_sg = sg + "~" + str(i)
    
    while (next_node in tfdata["graphdict"].keys() and next_sg in tfdata["graphdict"].keys()):
        if next_sg not in tfdata["graphdict"][next_node]:
            tfdata["graphdict"][next_node].append(next_sg)
        i += 1
        next_node = node.split("~")[0] + "~" + str(i)
        next_sg = sg + "~" + str(i)
