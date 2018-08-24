# MIPS - Claims-to-Quality Analyzer - Open-Source - Architecture
This is a quick overview of how the C2Q Analyzer works.

## About
`claims-to-quality-analyzer` is intended to calculate claims-based quality measures for providers. The analyzer works as follows:
    * Read provider data and compute the 74 claims-based quality measures for each provider.
    * Resulting measurements are submitted to the QPP Submissions API.

## Project Structure
* `audit`: contains scripts relating to verification of measure processing.
* `bin`: contains scripts employed during setup of the C2Q system.
* `claims_to_quality`: contains the bulk of the source code. Broken down into the following three components:
    * `analyzer`: calculating the quality measures
    * `lib`: shared resources
* `data`: contains data sources used for analysis and exploration.
* `tests`: contains automated unit tests.

## Single Source
TODO - Explain the process around the Single Source document and how we use it.

## Measure Definitions
### Measure Classes
The 74 measure definitions can be split into 5 main measure classes and a few measure specific classes:

- DateWindowEOCMeasure
- IntersectingDiagnosisMeasure
- MultipleEncounterMeasure
- PatientProcessMeasure
- PatientIntermediateMeasure
- ProcedureMeasure
- VisitMeasure

- CTScanMeasure
- Measure46
- Measure407


### Measure Mapping
We then use a measure mapping - `claims-to-quality/analyzer/measure_mapping.py` to use the correct class for each measure.


## Measure Processing
The overall measure processing looks like this. For each measure:

- Filtering claims to those containing quality codes.
- If required, infer the performance period for the submission and filter claims by date.
- Calculate measure:
	- Find relevant claims based on eligibility criteria
	- Filter claims by date if needed
	- Extract eligible instances, grouping claims together based on characteristics like beneficiary ID or beneficiary ID + date of service.
	- Score eligible instances using "most advantageous claims"
- Return eligible population and performance information
- (Send to the submission API)
