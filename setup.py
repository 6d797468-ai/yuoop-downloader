#!/usr/bin/env python3
"""
Setuptools compatibility shim.

Project metadata lives in pyproject.toml. Keep this file minimal so legacy
packaging commands and PEP 517 builds do not run the interactive bootstrap.
"""

from setuptools import setup


if __name__ == "__main__":
    setup()
