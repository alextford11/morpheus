.DEFAULT_GOAL := all

.PHONY: install
install:
	pip install -U setuptools pip
	pip install -r requirements.txt

.PHONY: isort
isort:
	isort -rc -w 120 morpheus
	isort -rc -w 120 tests

.PHONY: lint
lint:
	flake8 morpheus/ tests/
	pytest morpheus -p no:sugar -q
	python setup.py check -rms

.PHONY: test
test:
	pytest --cov=morpheus

.PHONY: testcov
testcov:
	pytest --cov=morpheus && (echo "building coverage html"; coverage html)

.PHONY: all
all: testcov lint

.PHONY: build
build:
	docker build morpheus -t morpheus

.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
