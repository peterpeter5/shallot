SHELL := /bin/bash
DIST := $(shell find ./dist -name *.whl)

clean:
	rm -r .testvenv build dist shallot.egg-info

testvenv:
	python -m venv .testvenv

build: **.py
	python setup.py build bdist_wheel

install: testvenv
	source .testvenv/bin/activate; \
	pip install ./dist/shallot*.whl;

integrationtest-package: build testvenv
	source .testvenv/bin/activate; \
	pip install $(DIST)[test]; \
	pytest ./integration_test ./test


integration_test-github:
	pytest --cov=shallot --cov-report html --cov-report term ./integration_test ./test

	$(MAKE) -C docs coverage
	$(MAKE) -C docs linkcheck

format-check:
	black --line-length=120 shallot/
	flake8 shallot/*

test: format-check
	pytest --cov=shallot --cov-report html --cov-report term test/ 

