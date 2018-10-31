# MIPS - Claims-to-Quality Analyzer - Open-Source Update Mechanism
To update the public version of claims-to-quality, follow the instructions below.

## Parent code
This repository only contains the open-source code of Claims-to-Quality. For security purposes, it does not expose access methods to government databases and other parts with any risk to create vulnerabilities.

For authorized users, the private repo lives at - [CMSgov/claims-to-quality-analyzer](https://github.com/CMSgov/claims-to-quality-analyzer/).

## Private to Public
We decided to rebase the complete history before releasing to the public. For this purpose, we created an `open-source` branch in the private repository and a new repository.

Once an update has been made to the open-source branch of the private repository, an authorized user will review the commit history.

After validation, the authorized user will be able to create a feature branch on the public repo and propose a PR with the updates.
