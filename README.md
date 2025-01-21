# dm-bip

| [Documentation](https://amc-corey-cox.github.io/dm_bip) |

Data Model-Based Ingestion Pipeline using LinkML tools
**TODO: Add more detailed information about the project**

# Setting Up a New Project -- Delete this section when completed

Upon creating a new project from the `cookiecutter-monarch-ingest` template, there are a few steps you should take to finish setting up the project. First, change into the newly created project.

```bash
cd dm-bip
```

#### Setup Python Environment and Install Poetry
To finish setting up the project first we'll need to set up a Python development environment. You can either use your system `poetry` or install it within a repository virtual environment.

##### Use System Poetry
To use you're system `poetry`, install `poetry` if you haven't already.
```
pip install poetry
```

##### Install Poetry in a Virtual Environment
To use poetry within a virtual environmen and install `poetry` to the environment use your system Python or install `pyenv` and select your python version with `pyenv local 3.13`. Then create a virtual environment and install poetry to it.
```
python -m venv .venv
. .venv/bin/activate
pip install poetry
```

#### GitHub Repository

1. Create a new repository on GitHub.
1. Enable GitHub Actions to read and write to the repository (required to deploy the project to GitHub Pages).
   - in GitHub, go to Settings -> Action -> General -> Workflow permissions and choose read and write permissions
1. Initialize the local repository and push the code to GitHub. For example:

   ```bash
   cd dm-bip
   git init
   git remote add origin https://github.com/<username>/<repository>.git
   git add -A && git commit -m "Initial commit"
   git push -u origin main
   ```

#### Documentation

1. Update this `README.md` file with any additional information about the project.
1. Add any appropriate documentation to the `docs` directory.

> **Note:** After the GitHub Actions for deploying documentation runs, the documentation will be automatically deployed to GitHub Pages.  
> However, you will need to go to the repository settings and set the GitHub Pages source to the `gh-pages` branch, using the `/docs` directory.

Once you have completed these steps, you can remove the [Setting Up a New Project](#setting-up-a-new-project) section from this `README.md` file.

## Requirements

- Python >= 3.13
- [Poetry](https://python-poetry.org/docs/#installation)

## Repository Structure

* [examples/](examples/) - example data
* [project/](project/) - project files (do not edit these)
* [src/](src/) - source files (edit these)
  * [dm_bip](src/dm_bip)
    * [schema](src/dm_bip/schema) -- LinkML schema
      (edit this)
    * [datamodel](src/dm_bip/datamodel) -- generated
      Python datamodel
* [tests/](tests/) - Python tests

## Developer Documentation

<details>
Use the `make` command to generate project artefacts:

* `make all`: make everything
* `make deploy`: deploys site
</details>

# Acknowledgements

This [cookiecutter](https://cookiecutter.readthedocs.io/en/stable/README.html) project was developed from the [monarch-project-template](https://github.com/monarch-initiative/monarch-project-template) template and will be kept up-to-date using [cruft](https://cruft.github.io/cruft/).
