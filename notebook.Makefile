RUN := poetry run


.PHONY: install-jupyter-kernel
install-jupyter-kernel: $(PYTHON)
	$(RUN) python -m ipykernel install --user --name=dm-bip --display-name "Python (dm-bip)"

.PHONY: jupyter-notebook
jupyter-notebook:
	@$(MAKE) _jupyter NB_FILE="$(word 2, $(MAKECMDGOALS))"

.PHONY: _jupyter
_jupyter:
	@KERNEL_NAME=dm-bip; \
	NB_FILE="$(NB_FILE)"; \
	if jupyter kernelspec list 2>/dev/null | grep -q "$$KERNEL_NAME"; then \
		echo "Kernel '$$KERNEL_NAME' already installed."; \
		INSTALLED_BEFORE=yes; \
	else \
		echo "Installing kernel '$$KERNEL_NAME'..."; \
		$(MAKE) install-jupyter-kernel; \
		INSTALLED_BEFORE=no; \
	fi; \
	echo "Launching notebook..."; \
	$(RUN) jupyter notebook $$NB_FILE; \
	if [ "$$INSTALLED_BEFORE" = "no" ]; then \
		echo "Removing temporary kernel '$$KERNEL_NAME'..."; \
		$(MAKE) remove-jupyter-kernel; \
	fi


.PHONY: remove-jupyter-kernel
remove-jupyter-kernel:
	jupyter kernelspec uninstall dm-bip -f
