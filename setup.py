#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup configuration for zulip-bots package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="async-zulip-bot-sdk",
    version="0.2.0",
    author="Stewitch",
    author_email="sunksugar24@gmail.com",
    description="Async, type-safe Zulip bot development framework in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    install_requires=[
        "distro>=1.9.0",
        "httpx>=0.28.1",
        "loguru>=0.7.3",
        "pydantic>=2.12.5",
        "ruamel-yaml>=0.19.1",
    ],
)
