"""
Regression test for #66: the SRA Metadata `Version` must be a quoted string.

Unquoted `Version: 1.1` parses as a YAML float, which the SRA metadata schema
rejects (cfn-lint E4002). Guard that it stays quoted.
"""

import re
from pathlib import Path

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "security"
    / "04-guardduty-stackset-audit-role.yaml"
)


def test_sra_version_is_quoted_string():
    text = TEMPLATE.read_text()
    # The SRA Version line must quote the value (string), not leave it a bare float.
    assert re.search(r'^\s*Version:\s*"[\d.]+"\s*$', text, re.MULTILINE), (
        "SRA Metadata Version must be a quoted string (e.g. Version: \"1.1\") to "
        "satisfy the schema / avoid cfn-lint E4002"
    )
    assert not re.search(r'^\s*Version:\s*\d+\.\d+\s*$', text, re.MULTILINE)
