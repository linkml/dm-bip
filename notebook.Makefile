RUN := poetry run

# Configurable parameters via environment variables
KERNEL_NAME ?= dm-bip
NB_FILE ?= notebooks/LinkML-Map_tutorial.ipynb

.PHONY: add-jupyter-kernel
add-jupyter-kernel: $(PYTHON)
	$(RUN) python -m ipykernel install --user --name=dm-bip --display-name "Python (dm-bip)"

ONESHELL:
.PHONY: jupyter-notebook
jupyter-notebook:
	if jupyter kernelspec list 2>/dev/null | grep -q "$KERNEL_NAME"; then \
		echo "Kernel '$KERNEL_NAME' already installed."; \
		INSTALLED_BEFORE=yes; \
	else \
		echo "Installing kernel '$KERNEL_NAME'..."; \
		$(MAKE) add-jupyter-kernel; \
	fi; \
	echo "Launching notebook..."; \
	$(RUN) jupyter notebook $NB_FILE; \
	if [ "$$INSTALLED_BEFORE" != "no" ]; then \
		echo "Removing temporary kernel '$KERNEL_NAME'..."; \
		$(MAKE) remove-jupyter-kernel; \
	fi


.PHONY: remove-jupyter-kernel
remove-jupyter-kernel:
	jupyter kernelspec uninstall dm-bip -f

.PHONY: lint-notebooks
lint-notebooks:
	@OUTPUTS=$$(find . -name '*.ipynb' ! -path './.venv/*' -exec grep -l '"output_type":' {} \;); \
	if [ -n "$$OUTPUTS" ]; then \
		echo "Notebooks contain outputs. Run 'make fix-notebook-lint'."; \
		exit 1; \
	fi

.PHONY: fix-notebook-lint
fix-notebook-lint:
	@echo "Stripping outputs from notebooks..."
	@find . -name '*.ipynb' ! -path "./.venv/*" ! -path "./.ipynb_checkpoints/*" -exec \
		$(RUN) jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace --to notebook {} \;
