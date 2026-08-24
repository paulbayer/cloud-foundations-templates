"""
Shared naming helpers.

These transforms are load-bearing across the generator: the organization
processor publishes OU IDs to SSM under a slug, and the deployment-guide
generator reads them back by the same slug. Keeping a single implementation
here guarantees the two sides stay byte-identical.
"""

import re


def ssm_slug(name: str) -> str:
    """
    Convert a name into an SSM-parameter-safe path segment.

    AWS Organizations allows spaces and punctuation in OU names, but SSM
    parameter names do not, so the name cannot be lowercased and used directly.
    Downstream templates resolve OU IDs by this slug, so the transformation has
    to stay stable.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return slug or "ou"
