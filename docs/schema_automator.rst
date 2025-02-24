Schema Automator
=================


Overview
---------
`Schema Automator <https://linkml.io/schema-automator/index.html>`_ is a toolkit within the `LinkML ecosystem <https://linkml.io/linkml/ecosystem.html>`_ that assists with generating LinkML schemas from structured and semi-structured sources.


Installation
-------------
The ``pyproject.toml`` file includes Schema Automator as a dependency. If you have already followed the "Getting Started" instructions in this project's README, you can run: ``poetry update`` to ensure your environment includes Schema Automator.


Usage
------
To test Schema Automator as a stand-alone tool on a file in the "toy_data" directory, run:  

.. code-block:: bash

   schemauto generalize-tsv toy_data/initial/study.tsv -n StudyInfo -o study_toy_data_schema.yaml



Help
-----
To see a full list of commands for Schema Automator, run:  

.. code-block:: bash

    schemauto --help


To see a full list of arguments for the ``generalize-tsv`` command, run:  

.. code-block:: bash

    schemauto generalize-tsv --help


Issues for Schema Automator can be submited via the `GitHub issue tracker <https://github.com/linkml/schema-automator>`_.