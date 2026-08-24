"""
Test for #108: the centralized VPC flow-logs bucket (network/03) must be
retained on teardown.

The bucket is versioned and holds audit data. CloudFormation cannot delete a
non-empty versioned bucket, which drove the StackSet instance INOPERABLE. Rather
than auto-empty (which would destroy audit logs), the bucket carries
DeletionPolicy: Retain so teardown succeeds cleanly and the data is preserved.
"""

from pathlib import Path

import yaml

import titanium_generator

TEMPLATE = (
    Path(titanium_generator.__file__).parent
    / "mcp_tools" / "templates" / "network"
    / "03-vpc-stackset-logarchive-flowlogs-bucket.yaml"
)


class _CfnLoader(yaml.SafeLoader):
    pass


_CfnLoader.add_multi_constructor("!", lambda loader, suffix, node: None)


def _bucket():
    doc = yaml.load(TEMPLATE.read_text(), Loader=_CfnLoader)
    return doc["Resources"]["VPCFlowLogsBucket"]


def test_bucket_is_retained_on_delete():
    bucket = _bucket()
    assert bucket.get("DeletionPolicy") == "Retain"
    assert bucket.get("UpdateReplacePolicy") == "Retain"


def test_bucket_not_auto_emptied():
    # Guard against reintroducing an auto-empty cleanup Lambda: audit data must
    # never be destroyed on teardown.
    text = TEMPLATE.read_text()
    assert "list_object_versions" not in text
    assert "delete_objects" not in text
