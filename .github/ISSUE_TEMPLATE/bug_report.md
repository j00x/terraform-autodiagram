---
name: Bug report
about: Create a report to help us improve TerraVision
title: '[BUG] '
labels: 'bug'
assignees: ''
---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Run command '...'
2. With Terraform files containing '...'
3. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened instead.

**Error Messages**
If applicable, paste the complete error message and stack trace:

```
Paste error message here
```

**Environment (please complete the following information):**
- OS: [e.g. Windows 10, macOS 12.1, Ubuntu 20.04]
- Python version: [e.g. 3.9.7]
- Terraform version: [e.g. 1.3.0]
- TerraVision version: [e.g. 0.6.0]
- Graphviz version: [e.g. 2.50.0]

**Sample Terraform Configuration**
If possible, provide a minimal Terraform configuration that reproduces the issue:

```hcl
# Paste minimal Terraform code here
resource "aws_instance" "example" {
  ami           = "ami-0abcdef1234567890"
  instance_type = "t2.micro"
}
```

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Additional context**
- Size of Terraform project (number of resources)
- Any custom annotations or configuration
- Cloud provider(s) being used
- Any other context about the problem

**Possible Solution**
If you have ideas about what might be causing the issue or how to fix it, please share them here.
