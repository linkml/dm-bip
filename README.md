# Data Model-Based Ingestion Pipeline - dm-bip

| [Documentation](https://linkml.io/dm-bip/) |

Data Model-Based Ingestion Pipeline using LinkML tools

## Overview
The purpose of this repository is to coordinate the efforts of multiple projects in creating a Data Model-Based Ingestion Pipeline (dm-bip) for their respective purposes. Currently, the two projects involved in this effort are the BioData Catalyst (BDC) Data Management Core (BDC-DMC) and the INCLUDE project. If you have another ingest pipeline you would like to consider for inclusion in this joint ingestion pipeline please make an issue or reach out to the respective programs of the authors of this repository.

The main effort of this project is to use existing [LinkML](https://linkml.io/linkml/) tools to the extent possible and fill in gaps between these tools with simple scripts. Whenever possible, the goal should be to move created middle-ware tools within this repository either upstream to the data submitters or into the LinkML tools in use.

# Requirements
- Python >= 3.12 (Note: Downgraded to 3.12 due to linkml-runtime issue in 3.13, patch forthcoming)
- [Poetry](https://python-poetry.org/docs/#installation)
- [Cruft] (https://cruft.github.io/cruft/)

# Repository Structure
 - Github wokflows:
   - For code quality checks (`qc.yml`)
   - Documentation deployment (`deploy-docs.yml`)
   - PyPI deployment (`pypi-publish.yml`)
 - `docs` directory with `Sphinx` configuration files and an `index.rst`file.
 - `src` directory structure with the `project_name` directory within it.
   - Within the `project_name` directory, there are 2 python files:
     - `main_file.py`
     - `cli.py` for [`click`](https://click.palletsprojects.com) commands.
 - `tests` directory with a very basic test.
 - `poetry` compatible `pyproject.toml` file containing minimal package requirements.
 - `tox.ini` file containing configuration for:
   -  `coverage-clean`
   -  `lint`
   -  `codespell`
   -  `docstr-coverage`
   -  `pytest`
- `LICENSE` file based on the choice made during setup. 
- `README.md` file containing `project_description` value entered during setup.

# Getting Started
To get started with development in the Data Model-Based Ingetion Pipeline (dm-bip) first we will need to clone the repository. If you don't already have `git` installed, refer to installation instructions appropriate for your environment [here](https://github.com/git-guides/install-git). With `git` installed you can clone the repository.
```
git clone https://github.com/linkml/dm-bip.git
```

Then, change to the newly created project directory.
```bash
cd dm-bip
```

## Setup Python Environment and Install Poetry
First, we'll need to set up a Python development environment. You can either use your system `poetry` or install it within a repository virtual environment.

### Use System Poetry
To use you're system `poetry`, install `poetry` if you haven't already.
```
pip install poetry
```

### Install Poetry in a Virtual Environment
To use poetry within a virtual environment and install `poetry` to the environment, use your system Python or install `pyenv` and select your python version with `pyenv local 3.12`. If you have just installed `pyenv`, make sure to install your intended Python version e.g. `pyenv install 3.12`. Then create a virtual environment and install poetry to it. You will also want to add `cruft` to the virtual environment to keep updated with this template.
```
pyenv local 3.12
python -m venv .venv
. .venv/bin/activate
pip install poetry
pip install cruft
```

### Install Dependencies
Now that we have the basic repository set up and the background dependencies, we can set up the dependencies for the rest of the project. First, we'll use poetry to install project dependencies.
```
poetry install
```

If you are managing `poetry` and `cruft` in the local virtual environment rather than using your own system wide poetry you may want to use the `env` group. If you are doing development within the repository you also want to use the `dev` group with your poetry install.
```
poetry install --with env --with dev
```

### Add `poetry-dynamic-versioning` as a plugin
Our usage of poetry requires the dynamic versionining plugin.
```
poetry self add "poetry-dynamic-versioning[plugin]"
```
**Note**: If you are using a Linux system and the above doesn't work giving you the following error `Invalid PEP 440 version: ...`, you could alternatively run:
```
poetry add poetry-dynamic-versioning
```

#### Verify the setup is working
Once we have everything set up, we should run `tox` and  to make sure that the setup is correct and functioning.
```
poetry run tox
```

This should run all the bullets mentioned above under the `tox` configuration and ideally you should see the following at the end of the run:
```
  coverage-clean: OK (0.20=setup[0.05]+cmd[0.15] seconds)
  lint-fix: OK (0.40=setup[0.01]+cmd[0.30,0.09] seconds)
  codespell-write: OK (0.20=setup[0.02]+cmd[0.18] seconds)
  docstr-coverage: OK (0.29=setup[0.01]+cmd[0.28] seconds)
  py: OK (1.29=setup[0.01]+cmd[1.28] seconds)
  congratulations :) (2.55 seconds)
```

And as the last line says: `congratulations :)`!! Your project is ready to evolve!

> If you have an error running `tox` your python dependencies may be out of sync and you may be able to fix it by running `poetry lock` and then running `tox` again.

# Final test to see everything is wired properly
When you have finished downloading and installing the repo, we can run the project by it's name to ensure everything is setup up properly.
```
poetry run dm-bip run
```
Should return "Hello, World"

To run commands within the poetry environment either preface the command with `poetry run`, i.e. `poetry run /path-to/my-command --options` or open the poetry shell with `poetry shell`. You should also be able to activate the virtual environment directly, `.venv/bin/activate` and run the command within the virtual environment like `dm-bip run`.

# Development
Now the repository is cloned, installed, and we have verified everything is working. We are ready for development. Please create issues at the main repository and work on development by creating branches within the main repo or within your own fork and pushing those commits to the main branch via PRs on GitHub.

## Testing
Before you submit your PR it is a good idea to do basic testing. Admittedly, the testing suite is rather sparse at the moment but please write tests for your submitted code and make sure they and other tests work before asking for a PR to be reviewed. We have set up automated testing on GitHub but it is also nice to test on your own system. You can do so with `make`.
```
make test
```
Or you can test directly with `pytest` which can be nice for only running specific tests.
```
poetry run pytest
```

## Linting
It is also a good idea to run linting locally before submitting PRs. You can lint with `make`.
```
make lint
```
Alternatively, you can run the linting direclty with `ruff`.
```
poetry run ruff --check --diff --exclude tests/input tests/output
```

# Updating the project after initial setup
There are a few things that may need further setup and maintenance after the initial setup of the repository, such as keeping the repository in sync with our upstream project template and setting up or using PyPi for distribution as well as automating that process. Instructions for all of these can be found below.

## Future updates to the project's boilerplate code
In order to be up-to-date with the template, first check if there is a mismatch between the project's boilerplate code and the template by running:
```
cruft check
```

This indicates if there is a difference between the current project's boilerplate code and the latest version of the project template. If the project is up-to-date with the template:
```
SUCCESS: Good work! Project's cruft is up to date and as clean as possible :).
```

Otherwise, it will indicate that the project's boilerplate code is not up-to-date by the following:
```
FAILURE: Project's cruft is out of date! Run `cruft update` to clean this mess up.
```

For viewing the difference, run `cruft diff`. This shows the difference between the project's boilerplate code and the template's latest version.

After running `cruft update`, the project's boilerplate code will be updated to the latest version of the template.

## This section is for further setup of the project
This section is for further setup of the project as a whole using the `monarch-project-template` and can be ignored for regular development. We should revisit this section as the project evolves and finalize the setup when appropriate.

### Setting up PyPI release

For the first time, you'll need to just run the following commands:
```
poetry build
poetry publish -u YOUR_PYPI_USERNAME -p YOUR_PYPI_PASSWORD
```
This will release a 0.0.0 version of your project on PyPI.

#### Automating this via Github Release
Use "[Trusted Publishers](https://docs.pypi.org/trusted-publishers/)" by PyPI

# Acknowledgements
This [cookiecutter](https://cookiecutter.readthedocs.io/en/stable/README.html) project was developed from the [monarch-project-template](https://github.com/monarch-initiative/monarch-project-template) template and will be kept up-to-date using [cruft](https://cruft.github.io/cruft/).
