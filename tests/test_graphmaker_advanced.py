"""
Advanced test cases for graphmaker module.

Tests complex scenarios, edge cases, and error conditions that aren't covered
by the basic unit tests.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from modules import graphmaker
from modules.logging_config import setup_logging


class TestGraphmakerAdvanced:
    """Advanced test cases for graphmaker functionality."""
    
    @classmethod
    def setup_class(cls):
        """Set up test class with logging."""
        setup_logging("DEBUG")
        cls.logger = logging.getLogger(__name__)
    
    def test_reverse_relations_with_missing_keys(self):
        """Test reverse_relations handles missing keys gracefully."""
        # Test with missing graphdict key
        incomplete_tfdata = {"meta_data": {}}
        
        with pytest.raises(KeyError):
            graphmaker.reverse_relations(incomplete_tfdata)
    
    def test_check_relationship_with_complex_parameters(self):
        """Test relationship checking with complex nested parameters."""
        tfdata = {
            "node_list": ["aws_ec2_instance.web", "aws_vpc.main", "aws_subnet.private"],
            "hidden": [],
            "graphdict": {
                "aws_ec2_instance.web": [],
                "aws_vpc.main": [],
                "aws_subnet.private": []
            }
        }
        
        # Complex nested parameter structure
        complex_params = [
            {
                "vpc_id": "${aws_vpc.main.id}",
                "subnet_ids": ["${aws_subnet.private.id}", "${aws_subnet.public.id}"],
                "security_groups": {
                    "ingress": [
                        {"from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"]},
                        {"from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}
                    ]
                }
            }
        ]
        
        result = graphmaker.check_relationship("aws_ec2_instance.web", complex_params, tfdata)
        
        # Should find relationships to VPC and subnet
        assert len(result) >= 2  # At least one relationship pair
        assert "aws_vpc.main" in result or "aws_subnet.private" in result
    
    def test_consolidate_nodes_with_circular_references(self):
        """Test node consolidation with circular reference scenarios."""
        tfdata = {
            "graphdict": {
                "aws_security_group.web": ["aws_security_group.db"],
                "aws_security_group.db": ["aws_security_group.web"],
                "aws_instance.web": ["aws_security_group.web"]
            },
            "meta_data": {
                "aws_security_group.web": {"ingress": []},
                "aws_security_group.db": {"ingress": []},
                "aws_instance.web": {"instance_type": "t3.micro"}
            }
        }
        
        with patch('modules.helpers.consolidated_node_check', return_value=None):
            result = graphmaker.consolidate_nodes(tfdata)
            
        # Should handle circular references without infinite loops
        assert "aws_security_group.web" in result["graphdict"]
        assert "aws_security_group.db" in result["graphdict"]
    
    def test_handle_variants_with_malformed_data(self):
        """Test variant handling with malformed or unexpected data."""
        tfdata = {
            "graphdict": {
                "malformed.resource.name": ["aws_ec2_instance.web"],
                "aws_ec2_instance.web": []
            },
            "meta_data": {
                "malformed.resource.name": {},
                "aws_ec2_instance.web": {"instance_type": "t3.micro"}
            }
        }
        
        # Should handle malformed resource names gracefully
        result = graphmaker.handle_variants(tfdata)
        assert result is not None
        assert "graphdict" in result
    
    def test_create_multiple_resources_large_count(self):
        """Test multiple resource creation with large count values."""
        tfdata = {
            "graphdict": {
                "aws_instance.web": ["aws_subnet.private"],
                "aws_subnet.private": []
            },
            "meta_data": {
                "aws_instance.web": {"count": 10, "instance_type": "t3.micro"},
                "aws_subnet.private": {"cidr_block": "10.0.1.0/24"}
            },
            "node_list": ["aws_instance.web", "aws_subnet.private"],
            "hidden": []
        }
        
        with patch('modules.helpers.consolidated_node_check', return_value=None), \
             patch('modules.helpers.list_of_dictkeys_containing', return_value=[]), \
             patch('modules.helpers.list_of_parents', return_value=[]):
            
            result = graphmaker.create_multiple_resources(tfdata)
            
        # Should create numbered instances (limited by max_i = 3)
        numbered_instances = [k for k in result["graphdict"] if "~" in k]
        assert len(numbered_instances) > 0
    
    def test_dict_generator_with_deeply_nested_structure(self):
        """Test dict generator with deeply nested data structures."""
        deeply_nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": ["value1", "value2", {"nested": "deep"}]
                        }
                    }
                }
            },
            "array_of_objects": [
                {"key1": "value1", "nested": {"deep": "value"}},
                {"key2": "value2", "array": [1, 2, 3]}
            ]
        }
        
        results = list(graphmaker.dict_generator(deeply_nested))
        
        # Should traverse all nested levels
        assert len(results) > 10  # Many nested values
        
        # Check specific deep value
        deep_values = [r for r in results if "deep" in str(r)]
        assert len(deep_values) > 0
    
    def test_performance_with_large_graph(self):
        """Test performance with large graph structures."""
        # Create a large graph structure
        large_tfdata = {
            "graphdict": {},
            "meta_data": {},
            "node_list": [],
            "hidden": []
        }
        
        # Generate 100 resources with interconnections
        for i in range(100):
            resource_name = f"aws_instance.web_{i}"
            large_tfdata["graphdict"][resource_name] = []
            large_tfdata["meta_data"][resource_name] = {"instance_type": "t3.micro"}
            large_tfdata["node_list"].append(resource_name)
            
            # Add some connections
            if i > 0:
                large_tfdata["graphdict"][resource_name].append(f"aws_instance.web_{i-1}")
        
        # Test consolidation performance
        import time
        start_time = time.time()
        
        with patch('modules.helpers.consolidated_node_check', return_value=None):
            result = graphmaker.consolidate_nodes(large_tfdata)
        
        elapsed = time.time() - start_time
        
        # Should complete within reasonable time (< 5 seconds for 100 nodes)
        assert elapsed < 5.0
        assert len(result["graphdict"]) == 100
    
    def test_error_handling_in_add_relations(self):
        """Test error handling in add_relations function."""
        tfdata = {
            "graphdict": {"aws_instance.web": []},
            "node_list": ["aws_instance.web"],
            "meta_data": {"aws_instance.web": {"instance_type": "t3.micro"}},
            "original_metadata": {"aws_instance.web": {"instance_type": "t3.micro"}},
            "hidden": []
        }
        
        # Mock a function to raise an exception
        with patch('modules.graphmaker.dict_generator', side_effect=Exception("Test error")):
            with pytest.raises(Exception) as exc_info:
                graphmaker.add_relations(tfdata)
            
            assert "Test error" in str(exc_info.value)
    
    def test_memory_usage_with_repeated_operations(self):
        """Test memory usage doesn't grow excessively with repeated operations."""
        import gc
        import sys
        
        base_tfdata = {
            "graphdict": {
                "aws_instance.web": ["aws_vpc.main"],
                "aws_vpc.main": []
            },
            "meta_data": {
                "aws_instance.web": {"instance_type": "t3.micro"},
                "aws_vpc.main": {"cidr_block": "10.0.0.0/16"}
            }
        }
        
        # Measure initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform operations multiple times
        for _ in range(50):
            tfdata_copy = base_tfdata.copy()
            tfdata_copy["graphdict"] = base_tfdata["graphdict"].copy()
            tfdata_copy["meta_data"] = base_tfdata["meta_data"].copy()
            
            with patch('modules.helpers.consolidated_node_check', return_value=None):
                graphmaker.consolidate_nodes(tfdata_copy)
        
        # Measure final memory
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable (less than 2x initial)
        memory_growth_ratio = final_objects / initial_objects
        assert memory_growth_ratio < 2.0
    
    def test_concurrent_access_safety(self):
        """Test thread safety of graph operations."""
        import threading
        import time
        
        tfdata = {
            "graphdict": {
                "aws_instance.web": ["aws_vpc.main"],
                "aws_vpc.main": []
            },
            "meta_data": {
                "aws_instance.web": {"instance_type": "t3.micro"},
                "aws_vpc.main": {"cidr_block": "10.0.0.0/16"}
            }
        }
        
        results = []
        exceptions = []
        
        def worker():
            try:
                # Make a deep copy to avoid shared state issues
                import copy
                local_tfdata = copy.deepcopy(tfdata)
                
                with patch('modules.helpers.consolidated_node_check', return_value=None):
                    result = graphmaker.consolidate_nodes(local_tfdata)
                results.append(result)
            except Exception as e:
                exceptions.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should complete without exceptions
        assert len(exceptions) == 0
        assert len(results) == 10


class TestGraphmakerEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_input_handling(self):
        """Test handling of empty or minimal input data."""
        empty_tfdata = {
            "graphdict": {},
            "meta_data": {},
            "node_list": [],
            "hidden": []
        }
        
        # Should handle empty data gracefully
        result = graphmaker.consolidate_nodes(empty_tfdata)
        assert result["graphdict"] == {}
        
        result = graphmaker.handle_variants(empty_tfdata)
        assert result["graphdict"] == {}
    
    def test_malformed_resource_names(self):
        """Test handling of malformed or unusual resource names."""
        malformed_tfdata = {
            "graphdict": {
                "": ["aws_instance.web"],  # Empty name
                "aws.instance..double.dots": [],  # Double dots
                "resource-with-dashes": [],  # Dashes
                "resource_with_unicode_🚀": [],  # Unicode
                "very.long.resource.name.with.many.dots.and.segments": []
            },
            "meta_data": {
                "": {},
                "aws.instance..double.dots": {},
                "resource-with-dashes": {},
                "resource_with_unicode_🚀": {},
                "very.long.resource.name.with.many.dots.and.segments": {}
            }
        }
        
        # Should handle malformed names without crashing
        result = graphmaker.consolidate_nodes(malformed_tfdata)
        assert result is not None
        assert "graphdict" in result
    
    def test_circular_dependency_detection(self):
        """Test detection and handling of circular dependencies."""
        circular_tfdata = {
            "graphdict": {
                "resource_a": ["resource_b"],
                "resource_b": ["resource_c"],
                "resource_c": ["resource_a"]  # Creates cycle
            },
            "meta_data": {
                "resource_a": {},
                "resource_b": {},
                "resource_c": {}
            }
        }
        
        # Should handle circular dependencies without infinite loops
        with patch('modules.helpers.consolidated_node_check', return_value=None):
            result = graphmaker.consolidate_nodes(circular_tfdata)
            
        assert result is not None
        # All resources should still be present
        assert len(result["graphdict"]) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
