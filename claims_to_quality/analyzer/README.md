# Claims to Quality Analyzer
This is the main library for the MIPS analyzer service within the C2Q pipeline.

## About
The main function of this module is to calcuate all 74 claims-based quality measures for all providers and submit the results to the QPP submissions API, whose source code is located [at this Github repository](https://github.com/CMSgov/qpp-submissions-api)).

## Structure
The top-level files for calculating the quality measures and submitting the results are [`process.py`](processing/process.py) and [`submit.py`](processing/submit.py). 

The distinct measure types can be found under [calculation](calculation/).

The [models](models/) directory contains data structures for storing measure and claim information. 
The [datasource](datasource/) directory contains tools to load these data structures, either from the IDR in the case of claims data or from the single source JSON in the case of measures data.