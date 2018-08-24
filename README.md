# MIPS - Claims-to-Quality Analyzer - Open-Source
This is the open-source version of the C2Q Analyzer repository.

To learn more about the architecture of the project, please have a look [here](/docs/ARCHITECTURE.md).
To learn how we keep them in sync, follow the instructions [here](/docs/UPDATE.md).

## About
`claims-to-quality-analyzer` is intended to calculate claims-based quality measures for providers. The analyzer works as follows:

	- Read provider data and filter on quality codes
	- For each of 74 claims-based quality measures and for each provider, filter to relevant claims.
	- Calculate measures and aggregate for each provider.
	- Resulting measurements are submitted to the QPP Submissions API.

## Project Structure
* `audit`: contains scripts relating to verification of measure processing.
* `bin`: contains scripts employed during setup of the C2Q system.
* `claims_to_quality`: contains the bulk of the source code. Broken down into the following three components:
    * `analyzer`: calculating the quality measures
    * `lib`: shared resources
* `data`: contains data sources used for analysis and exploration.
* `tests`: contains automated unit tests.

## Instructions
We use [Docker](https://www.docker.com/) for easier collaboration and deployment. If you don't already have Docker installed, install it [here](https://docs.docker.com/engine/installation).

## Local Development

### Tests and Linter
Several entries exist in the [makefile](/Makefile) for running tests. Use `make local-test` to run the full test suite and linters locally.

You can simply start the app following the instructions below.

### Analyzer
`make local-analyzer`

#### Note
To detach from a running container which you are attached to:
`ctrl + p, ctrl + q - hold ctrl in between.`

#### Poirot Secrets Testing
A secrets pattern file `hubzone-poirot-patterns.txt` is included with the app to assist with running [Poirot](https://github.com/emanuelfeld/poirot) to scan commit history for secrets.

##### Install
It is important to run Poirot locally and not through docker-compose, to make sure that you are looking at all the files in the repo.

##### Run
 It is recommended to run this on the current branch only:
```
  poirot --patterns c2q-poirot-patterns.txt --revlist="develop^..HEAD"
```
Poirot will return an error status if it finds any secrets in the commit history between `HEAD` and develop.  You can correct these by: removing the secrets and squashing commits or by using something like BFG.

##### Note
Note that Poirot is hardcoded to run in case-insensitive mode and uses two different regex engines (`git log --grep` and a 3rd-party Python regex library https://pypi.python.org/pypi/regex/ ). Refer to Lines 121 and 195 in `<python_path>/site-packages/poirot/poirot.py`. The result is that the 'ssn' matcher will flag on: 'ssn', 'SSN', or 'ssN', etc., which also 'className', producing false positive errors in the full rev history.  Initially we included the `(?c)` flag in the SSN matchers: `.*(ssn)(?c).*[:=]\s*[0-9-]{9,11}` however this is not compatible with all regex engines and causes an error in some cases.  During the `--revlist="all"` full history Poirot runs, this pattern failed silently with the `git --grep` engine and therefore did not actually run.  During the `--staged` Poirot runs, this pattern fails with a stack trace with the `pypi/regex` engine. The `(?c)` pattern has been removed entirely and so the `ssn` patterns can still flag on false positives like 'className'.

## Contributing
This repository is open for contributions, although it is not its primary intent. Please read [CONTRIBUTING](CONTRIBUTING.md) to learn more on how to contribute.

We strive for a welcoming and inclusive environment for the Claims-to-Quality project.

Please follow this guidelines in all interactions:

1. Be Respectful: use welcoming and inclusive language.
2. Assume best intentions: seek to understand other's opinions.

## Security Issues
Please do not submit an issue on GitHub for a security vulnerability. Please contact the development team through the Certify Help Desk at [c2q@tistatech.com](mailto:c2q@tistatech.com).

Be sure to include all the pertinent information.

<sub>The agency reserves the right to change this policy at any time.</sub>
