lint:
	flake8 bin claims_to_quality runners tests
	pep257 claims_to_quality

# Run test suite locally.
test: FORCE
	ENV=TEST pytest -s tests

# Run coverage.
coverage:
	ENV=TEST pytest --cov=claims_to_quality --cov-config .coveragerc --cov-fail-under=90 --cov-report term-missing

# Run local tests.
local-test:
	docker-compose -f docker-compose.yml -f docker-compose.override.local.yml run --entrypoint "make test" analyzer

# Run local linter.
local-lint:
	docker-compose -f docker-compose.yml -f docker-compose.override.local.yml run --entrypoint "make lint" analyzer

# Run local test coverage.
local-coverage:
	docker-compose -f docker-compose.yml -f docker-compose.override.local.yml run --entrypoint "make coverage" analyzer

# Run local linter and tests.
local-all:
	$(MAKE) local-lint
	$(MAKE) local-test
	$(MAKE) local-coverage

local-analyzer-shell:
	docker-compose -f docker-compose.yml -f docker-compose.override.local.yml run --rm analyzer bash

# [Dummy dependency to force a make command to always run.]
FORCE:
