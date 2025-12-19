.. dm-bip documentation index file

Data Model-Based Ingestion Pipeline (dm-bip)
==========================================================================

This project coordinates efforts to create a Data Model-Based Ingestion Pipeline using [LinkML](https://linkml.io/linkml/) tools. Currently, it is a collaboration between the BioData Catalyst and INCLUDE teams, with the goal of developing a flexible, reusable pipeline framework adaptable to other projects. Contributions from other groups are welcome!

Overview
========
The primary objective of dm-bip is to leverage existing LinkML tools and supplement them with lightweight scripts where necessary. Whenever feasible, middleware tools developed here should be integrated upstream with data submitters or incorporated into LinkML tools.

Usage
=====
See :doc:`installation` for installation instructions.

To verify everything is working, run:

.. code-block:: bash

    uv run tox

To test the project:

.. code-block:: bash

    uv run dm-bip run

This should return "Hello, World".

Repository Structure
====================
- `docs/` - Sphinx documentation
- `src/` - Contains the main source code
- `tests/` - Basic unit tests
- `.github/workflows/` - GitHub Actions for CI/CD
- `pyproject.toml` - Project configuration and dependencies (managed with uv)
- `tox.ini` - Configuration for linting, testing, and code quality checks

.. toctree::
   :maxdepth: 2
   :caption: Contents

   installation
   pipeline_user_docs
   schema_automator
   schemasheets
   scripts_format_converters


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

  index
