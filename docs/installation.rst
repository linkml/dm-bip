.. dm-bip installation information

Installation
============

Requirements:
-------------
- Python >= 3.11, <= 3.13
- `uv <https://docs.astral.sh/uv/>`_
- `Cruft <https://cruft.github.io/cruft/>`_

To install and set up the project:

.. code-block:: bash

    git clone https://github.com/linkml/dm-bip.git
    cd dm-bip

Using uv (default):

.. code-block:: bash

    uv sync

Using Virtual Environment explicitly:

.. code-block:: bash

    pyenv local 3.12
    uv sync
