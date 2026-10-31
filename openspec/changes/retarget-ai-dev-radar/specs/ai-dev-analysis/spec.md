# Spec Delta

## Purpose

Defines the English and Russian analysis of an arXiv paper so a reader can judge whether it helps organize software development with AI or build an AI-powered product feature.

## ADDED Requirements

### Requirement: Prompt assembly
For each paper the analysis request MUST contain the shared instructions, the lens for that paper's search topic, and both the process and feature track sections. The saved analysis MUST contain only one track body.

#### Scenario: Group lens is included
- **WHEN** a paper's topic is `chart_generation`
- **THEN** the request contains the shared instructions, the `chart_generation` lens, and both track sections

#### Scenario: Topic has no lens
- **WHEN** a paper's topic has no lens text
- **THEN** the request still contains the shared instructions and both track sections

#### Scenario: One body is saved
- **WHEN** an English analysis file is saved
- **THEN** it contains either the process body or the feature body, and not both

### Requirement: Track classification
The English analysis MUST state exactly one track, `process` or `feature`, in a `Track` metadata line. The track MUST follow the paper's primary contribution, not the search topic: `process` when it changes how software is built with AI, `feature` when it delivers a capability end users of a product receive.

#### Scenario: Coding agent paper
- **WHEN** the paper's contribution is an agent loop that resolves repository issues
- **THEN** the track is `process`

#### Scenario: Chart generation paper found by a process phrase
- **WHEN** the paper was found by a coding-agent phrase but its contribution is generating charts from natural language for end users
- **THEN** the track is `feature`

### Requirement: Track-specific score
The English analysis MUST contain `## Recommendation: N/10`, where N is an integer from 1 to 10, with no explanation on that line. Process papers MUST be scored equally on process relevance, actionability, evidence, and transfer. Feature papers MUST be scored equally on feature relevance, novelty, result quality, and product integrability.

#### Scenario: Strong process paper
- **WHEN** a process paper changes how a team runs an AI-assisted development loop, states a practice that can be adopted, and supports it with evidence that applies outside the authors' own scaffold
- **THEN** the recommendation is 9 or 10

#### Scenario: Strong feature paper
- **WHEN** a feature paper targets chart, text-motion, screen-video, or GUI-agent capability, is novel, reports clearly better results, and produces structured or editable output at product-viable latency
- **THEN** the recommendation is 9 or 10

#### Scenario: Off-topic paper
- **WHEN** a paper is neither about building software with AI nor about a target product feature
- **THEN** the recommendation is 1 or 2

#### Scenario: Score line has no commentary
- **WHEN** an English analysis file is saved
- **THEN** the recommendation heading contains only the integer and `/10`

### Requirement: Machine-read sections stay stable
The English analysis MUST include a `Code` metadata line, a `## Tags` section whose values are one comma-separated, hyphenated line directly after the heading, and a `## Summary` section of one paragraph.

#### Scenario: Downstream readers
- **WHEN** an English analysis file is saved
- **THEN** a reader can extract the score, the code URL, the tags, and the summary paragraph from those fields

### Requirement: Shared header and tail
Every English analysis MUST include, in order, metadata with `Track`, the recommendation, tags, a fit line, at most one figure, the summary, and a takeaway. It MUST end with limitations and what is required to run the approach.

#### Scenario: Any track
- **WHEN** an English analysis file is saved
- **THEN** it contains the shared header sections before the track body and the two tail sections after it

### Requirement: Process body
A process analysis MUST give the workflow stage as its fit value, one of discover, specify, implement, review, verify, or context. Its body MUST cover the method as a workflow loop, evaluation, what changed in practice, adjacent systems, and the human in the loop.

#### Scenario: Process analysis
- **WHEN** the track is `process`
- **THEN** the fit line is one value from that stage set
- **AND** the body contains the five process sections

### Requirement: Feature body
A feature analysis MUST give the feature area as its fit value, one of charts, text-motion, screen-video, or gui-agent. Its body MUST cover the user-facing capability, the pipeline, output format and integration, evaluation, competitors, and latency and cost.

#### Scenario: Feature analysis
- **WHEN** the track is `feature`
- **THEN** the fit line is one value from that area set
- **AND** the body contains the six feature sections

### Requirement: Takeaway names a concrete action
The takeaway MUST say what to adopt or try in this team's workflow or features, and what to skip, without restating the summary.

#### Scenario: Weak paper
- **WHEN** a paper offers nothing reusable
- **THEN** the takeaway says to skip it and why

### Requirement: Track figure
When figure metadata is available, the analysis MUST include at most one image. Process papers MUST use a workflow or system overview. Feature papers MUST use a pipeline overview, or a representative output example when no pipeline figure exists. Otherwise the image MUST be omitted.

#### Scenario: Process paper with overview figure
- **WHEN** the track is `process` and a caption describes a workflow or system overview
- **THEN** the analysis includes that figure's URL and no other figure

#### Scenario: No suitable figure
- **WHEN** figure metadata is missing or no caption fits the track
- **THEN** the analysis contains no image

### Requirement: Confluence-safe formulas
The analysis MUST write formulas as plain text or Unicode. It MUST NOT use LaTeX math delimiters.

#### Scenario: Paper states a formula
- **WHEN** the analysis includes a formula from the paper
- **THEN** the formula contains no LaTeX math delimiters

### Requirement: Russian translation preserves identifiers
The Russian analysis MUST keep the English heading structure. Tag values, the recommendation line, the track value, the fit value, URLs, and method, dataset, and metric names MUST stay as in the English file.

#### Scenario: Translation
- **WHEN** the English analysis is translated to Russian
- **THEN** the recommendation line, track, fit value, and tag values are unchanged
- **AND** prose headings and sentences are in Russian
