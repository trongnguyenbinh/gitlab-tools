#!/usr/bin/env python3
"""
Setup script for GitLab Tools.
"""

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

with open(here / "README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open(here / "requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="gitlab-tools",
    version="1.0.0",
    author="GitLab Tools",
    author_email="",
    description="A suite of tools for managing GitLab repositories - clone and publish repositories with group hierarchy support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    package_dir={"":"src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: System :: Archiving :: Backup",
    ],
    python_requires=">=3.13",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "gitlab-clone=gitlab_tools.cli_cloner:main",
            "gitlab-publish=gitlab_tools.cli_publisher:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
