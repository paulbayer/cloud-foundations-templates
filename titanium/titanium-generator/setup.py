"""
Setup configuration for Titanium Template Modifier.
"""

from setuptools import setup, find_packages

setup(
    name="titanium-generator",
    version="0.1.0",
    description="Titanium Template Modifier - CloudFormation template parameter injection system",
    author="Titanium Team",
    author_email="titanium@example.com",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pyyaml>=6.0",
        "click>=8.0", 
        "jsonschema>=4.0",
        "dataclasses-json>=0.6.0",
        "typing-extensions>=4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "flake8>=5.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
