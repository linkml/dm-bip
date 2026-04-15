.. dm-bip installation information

Installation
============

Requirements:
-------------
- Python >= 3.11, <= 3.13
- `uv <https://docs.astral.sh/uv/>`_
- `make <https://www.gnu.org/software/make/>`_ (usually pre-installed on Mac/Linux)

To install and set up the project:

.. code-block:: bash

    git clone https://github.com/linkml/dm-bip.git
    cd dm-bip
    uv sync

``uv sync`` handles the Python version, virtual environment, and all dependencies.
