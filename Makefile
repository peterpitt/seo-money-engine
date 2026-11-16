SITE ?= sites/coffee-demo

.PHONY: install test cov check build serve

install:
	pip install -e ".[dev]"

test:
	python -m pytest

cov:
	python -m pytest --cov=seoengine --cov-report=term-missing

check:
	seoengine check $(SITE)

build:
	seoengine build $(SITE)

serve: build
	python -m http.server 8000 -d $(SITE)/public
