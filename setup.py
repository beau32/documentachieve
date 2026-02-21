#!/usr/bin/env python
"""
Setup script for Cloud Document Archive CLI.

Install with:
    pip install -e .

Then use:
    archive-cli --help
"""

from setuptools import setup, find_packages

setup(
    name="cloud-document-archive",
    version="2.0.0",
    description="Cloud-based document archive with encryption, user management, and audit trails",
    author="Your Organization",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "python-dotenv>=1.0.0",
        "cryptography>=41.0.0",
        "pyjwt>=2.8.0",
        "click>=8.0.0",
        "tabulate>=0.9.0",
        "boto3>=1.34.0",
        "azure-storage-blob>=12.19.0",
        "google-cloud-storage>=2.14.0",
        "pyiceberg>=0.7.0",
        "aiokafka>=0.10.0",
        "sentence-transformers>=2.2.0",
    ],
    entry_points={
        "console_scripts": [
            "archive-cli=app.cli:cli",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
)
