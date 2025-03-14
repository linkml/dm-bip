.. dm-bip installation information

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