.. dm-bip documentation master file

Welcome to the Data Model-Based Ingestion Pipeline (dm-bip) documentation!
==========================================================================

This project coordinates efforts to create a Data Model-Based Ingestion Pipeline using [LinkML](https://linkml.io/linkml/) tools. Currently, it is a collaboration between the BioData Catalyst and INCLUDE teams, with the goal of developing a flexible, reusable pipeline framework adaptable to other projects. Contributions from other groups are welcome!

Overview
========
The primary objective of dm-bip is to leverage existing LinkML tools and supplement them with lightweight scripts where necessary. Whenever feasible, middleware tools developed here should be integrated upstream with data submitters or incorporated into LinkML tools.

Installation
============

Requirements:
-------------
- Python >= 3.12 (Note: Downgraded to 3.12 due to linkml-runtime issue in 3.13, patch forthcoming)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Cruft](https://cruft.github.io/cruft/)

To install and set up the project:

.. code-block:: bash

    git clone https://github.com/amc-corey-cox/dm-bip.git
    cd dm-bip

Using System Poetry:

.. code-block:: bash

    pip install poetry
    poetry install

Using Virtual Environment:

.. code-block:: bash

    pyenv local 3.12
    python -m venv .venv
    . .venv/bin/activate
    pip install poetry
    pip install cruft
    poetry install --with env

Usage
=====
To verify everything is working, run:

.. code-block:: bash

    poetry run tox

To test the project:

.. code-block:: bash

    poetry run dm-bip run

This should return "Hello, World".

Repository Structure
====================
- `docs/` - Sphinx documentation
- `src/` - Contains the main source code
- `tests/` - Basic unit tests
- `.github/workflows/` - GitHub Actions for CI/CD
- `pyproject.toml` - Poetry configuration file
- `tox.ini` - Configuration for linting, testing, and code quality checks


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

  index
