#!/usr/bin/env python3
"""
Setup script for 42-Norminette-Formatter
"""

from setuptools import setup, find_packages
import os
import re

# Read version from __init__.py
def get_version():
    with open(os.path.join('norminette_formatter', '__init__.py'), 'r') as f:
        content = f.read()
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", content, re.M)
        if version_match:
            return version_match.group(1)
        raise RuntimeError("Unable to find version string.")

# Read long description from README
def get_long_description():
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()

# Read requirements
def get_requirements():
    with open('requirements.txt', 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='42-norminette-formatter',
    version=get_version(),
    author='afreitas',
    author_email='afreitas@student.42.fr',
    description='A comprehensive norminette debugging and auto-correction tool for 42 School projects',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/Juskocode/42-Nominette-Formatter',
    project_urls={
        'Bug Reports': 'https://github.com/Juskocode/42-Nominette-Formatter/issues',
        'Source': 'https://github.com/Juskocode/42-Nominette-Formatter',
        'Documentation': 'https://github.com/Juskocode/42-Nominette-Formatter#readme',
    },
    packages=find_packages(exclude=['tests*']),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Education',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Environment :: Web Environment',
    ],
    keywords='norminette 42school code-quality linting formatting c-language',
    python_requires='>=3.8',
    install_requires=get_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'hypothesis>=6.70.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
            'isort>=5.12.0',
            'safety>=2.3.0',
            'bandit>=1.7.0',
        ],
        'web': [
            'Flask>=2.3.0',
            'Flask-CORS>=4.0.0',
        ],
        'all': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
            'hypothesis>=6.70.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
            'isort>=5.12.0',
            'safety>=2.3.0',
            'bandit>=1.7.0',
            'Flask>=2.3.0',
            'Flask-CORS>=4.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            '42-norminette-formatter=norminette_formatter.cli.commands:main',
            'norminette-formatter=norminette_formatter.cli.commands:main',
        ],
    },
    include_package_data=True,
    package_data={
        'norminette_formatter': [
            'dashboard/templates/*.html',
            'dashboard/static/css/*.css',
            'dashboard/static/js/*.js',
        ],
    },
    zip_safe=False,
    platforms=['any'],
    license='MIT',
    test_suite='tests',
    tests_require=[
        'pytest>=7.0.0',
        'pytest-cov>=4.0.0',
        'pytest-mock>=3.10.0',
        'hypothesis>=6.70.0',
    ],
)