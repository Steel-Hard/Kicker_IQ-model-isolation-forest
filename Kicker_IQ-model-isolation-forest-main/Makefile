.PHONY: help venv install import export notebook start clean

help:
	clear
	@echo "Makefile commands:"
	@echo "  venv      - Cria o ambiente virtual"
	@echo "  install   - Instala as dependências no ambiente virtual"
	@echo "  import    - Popula o banco de dados com os dados da planilha"
	@echo "  export    - Treina e exporta os modelos ONNX por atleta"
	@echo "  notebook  - Abre o Jupyter Notebook de desenvolvimento"
	@echo "  clean     - Remove o ambiente virtual e caches"

venv:
	python3 -m venv .venv

install:
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r requirements.txt

import:
	.venv/bin/python scripts/importData.py

export:
	.venv/bin/python src/export/export_onnx.py

notebook:
	.venv/bin/jupyter notebook src/isolation-forest_model.ipynb

clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
