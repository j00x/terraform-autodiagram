# Contributing to TerraVision

Thank you for your interest in contributing to TerraVision! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Adding New Cloud Providers](#adding-new-cloud-providers)

## Code of Conduct

This project adheres to a code of conduct that we expect all contributors to follow. Please be respectful, inclusive, and constructive in all interactions.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.8 or higher
- Git
- Terraform CLI
- Graphviz
- Basic understanding of Terraform and cloud infrastructure

### Development Environment Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/terraform-autodiagram.git
   cd terraform-autodiagram
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .  # Install in development mode
   ```

3. **Install additional development dependencies:**
   ```bash
   pip install pytest pytest-cov black flake8 mypy
   ```

4. **Verify installation:**
   ```bash
   python terravision --help
   ```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes**
- **New features**
- **Cloud provider support** (GCP, Azure, etc.)
- **Documentation improvements**
- **Performance optimizations**
- **Test coverage improvements**
- **UI/UX enhancements**

### Before You Start

1. Check existing [issues](https://github.com/patrickchugh/terravision/issues) and [pull requests](https://github.com/patrickchugh/terravision/pulls)
2. Create or comment on an issue to discuss your proposed changes
3. For large changes, consider creating a design document

## Coding Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting:
  ```bash
  black modules/ tests/ *.py
  ```
- Use type hints where appropriate
- Maximum line length: 88 characters (Black default)

### Code Quality Tools

Run these tools before submitting:

```bash
# Format code
black modules/ tests/ *.py

# Check style
flake8 modules/ tests/ *.py

# Type checking
mypy modules/

# Run tests
pytest tests/ -v --cov=modules
```

### Code Organization

- **Modules**: Core functionality in `modules/` directory
- **Tests**: All tests in `tests/` directory
- **Cloud Providers**: Provider implementations in `modules/cloud_providers/`
- **Resource Classes**: Resource definitions in `resource_classes/`

### Logging

- Use the logging framework in `modules/logging_config.py`
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Include context in log messages

Example:
```python
import logging
logger = logging.getLogger(__name__)

def process_resource(resource_name: str):
    logger.debug(f"Processing resource: {resource_name}")
    try:
        # Process resource
        logger.info(f"Successfully processed {resource_name}")
    except Exception as e:
        logger.error(f"Failed to process {resource_name}: {e}")
        raise
```

## Testing Guidelines

### Test Structure

- Unit tests for individual functions and classes
- Integration tests for end-to-end workflows
- Performance tests for large-scale scenarios

### Writing Tests

```python
import pytest
from modules import graphmaker

class TestGraphMaker:
    def test_consolidate_nodes(self):
        """Test node consolidation functionality."""
        tfdata = {
            "graphdict": {"resource_a": ["resource_b"]},
            "meta_data": {"resource_a": {"type": "test"}}
        }
        
        result = graphmaker.consolidate_nodes(tfdata)
        assert "resource_a" in result["graphdict"]
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=modules --cov-report=html

# Run specific test file
pytest tests/test_graphmaker.py -v

# Run tests matching pattern
pytest tests/ -k "test_consolidate" -v
```

### Test Coverage

- Aim for >80% test coverage
- Include edge cases and error conditions
- Test with various cloud provider configurations

## Documentation

### Code Documentation

- Use comprehensive docstrings for all public functions and classes
- Follow Google docstring style:

```python
def process_terraform_graph(tfdata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Terraform graph data to create visualization.
    
    Args:
        tfdata: Dictionary containing Terraform graph and metadata
        
    Returns:
        Processed data ready for diagram generation
        
    Raises:
        ValueError: If required keys are missing from tfdata
        ProcessingError: If graph processing fails
    """
```

### README Updates

- Update README.md for new features
- Include usage examples
- Update installation instructions if needed

## Pull Request Process

### Before Submitting

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add support for GCP resources"
   ```

3. **Run quality checks:**
   ```bash
   black modules/ tests/ *.py
   flake8 modules/ tests/ *.py
   pytest tests/ --cov=modules
   ```

4. **Update documentation:**
   - Add docstrings to new functions
   - Update README if needed
   - Add examples for new features

### Commit Message Format

Use conventional commit format:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/modifications
- `refactor:` for code refactoring
- `perf:` for performance improvements

Examples:
```
feat: add GCP cloud provider support
fix: resolve circular dependency in graph processing
docs: update installation instructions for Windows
test: add comprehensive tests for AWS provider
```

### Pull Request Template

When submitting a PR, include:

1. **Description:** Clear description of changes
2. **Motivation:** Why is this change needed?
3. **Testing:** How was it tested?
4. **Screenshots:** For UI changes
5. **Breaking Changes:** Any breaking changes?

## Issue Reporting

### Bug Reports

When reporting bugs, include:

- **Environment:** OS, Python version, Terraform version
- **Steps to Reproduce:** Detailed steps
- **Expected Behavior:** What should happen
- **Actual Behavior:** What actually happens
- **Error Messages:** Full error messages/stack traces
- **Sample Code:** Minimal reproducible example

### Feature Requests

For feature requests, provide:

- **Use Case:** Why is this feature needed?
- **Proposed Solution:** How should it work?
- **Alternatives:** Any alternative approaches considered?
- **Additional Context:** Screenshots, examples, etc.

## Adding New Cloud Providers

### Provider Implementation

1. **Create provider class:**
   ```python
   # modules/cloud_providers/gcp_provider.py
   from . import BaseCloudProvider
   
   class GCPProvider(BaseCloudProvider):
       @property
       def provider_name(self) -> str:
           return "gcp"
       
       # Implement all abstract methods...
   ```

2. **Register provider:**
   ```python
   # In your initialization code
   from modules.cloud_providers import register_provider
   from modules.cloud_providers.gcp_provider import GCPProvider
   
   register_provider(GCPProvider())
   ```

3. **Add resource definitions:**
   ```python
   # resource_classes/gcp/__init__.py
   # Add GCP resource class definitions
   ```

4. **Add tests:**
   ```python
   # tests/test_gcp_provider.py
   # Comprehensive tests for GCP provider
   ```

### Resource Icons

- Add provider-specific icons to `resource_images/gcp/`
- Follow the existing directory structure
- Use PNG format, consistent sizing
- Include icons for major service categories

### Configuration

- Add provider-specific configuration to cloud config
- Define resource relationships and special handling
- Add provider to documentation

## Performance Considerations

### Large Projects

When working on performance improvements:

- Profile code using the performance utilities in `modules/performance_cache.py`
- Use caching for expensive operations
- Consider memory usage for large Terraform projects
- Test with realistic large-scale scenarios

### Optimization Guidelines

- Use lazy loading where appropriate
- Implement efficient algorithms for graph processing
- Cache results of expensive computations
- Profile before and after optimizations

## Release Process

### Version Numbering

- Follow [Semantic Versioning](https://semver.org/)
- Format: MAJOR.MINOR.PATCH
- Document changes in CHANGELOG.md

### Release Checklist

- [ ] Update version number
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release notes

## Questions and Support

- **Discussions:** Use GitHub Discussions for questions
- **Issues:** Create issues for bugs and feature requests
- **Email:** Contact maintainers for sensitive issues

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- Special recognition for major features

Thank you for contributing to TerraVision! 🚀
