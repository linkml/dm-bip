.. dm-bip installation information

Installation
============

Requirements:
-------------
- Python >= 3.12 (Note: Downgraded to 3.12 due to linkml-runtime issue in 3.13, patch forthcoming)
- [uv](https://docs.astral.sh/uv/)
- [Cruft](https://cruft.github.io/cruft/)

To install and set up the project:

.. code-block:: bash

    git clone https://github.com/amc-corey-cox/dm-bip.git
    cd dm-bip

Using uv (default):

.. code-block:: bash

    uv sync

Using Virtual Environment explicitly:

.. code-block:: bash

    pyenv local 3.12
    uv sync
