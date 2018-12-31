SHELL := /bin/bash
DIST := $(shell find ./dist -name *.whl)

clean:
	rm -r .testvenv build dist shallot.egg-info

testvenv:
	python -m venv .testvenv

build:
	python setup.py build bdist_wheel

install: testvenv
	source .testvenv/bin/activate; \
	pip install ./dist/shallot*.whl;

install-pytest:
	source .testvenv/bin/activate; \
	pip install pytest pytest-asyncio;

unittest-package: install-pytest testvenv
	source .testvenv/bin/activate; \
	pytest ./test;

integrationtest-package: testvenv
	source .testvenv/bin/activate; \
	pip install $(DIST)[test]; \
	pytest ./integration_test ./test
	

