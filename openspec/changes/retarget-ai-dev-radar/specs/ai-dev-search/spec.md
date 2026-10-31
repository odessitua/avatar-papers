# Spec Delta

## Purpose

Defines which arXiv papers this radar collects: AI-assisted software development and AI-powered product features, in a fresh corpus that does not reuse the avatar-paper table.

## ADDED Requirements

### Requirement: Process topic family
The default search MUST include four development-process groups: coding agents, specification review and verification, repository context, and human-AI programming workflow.

#### Scenario: Process groups are queried
- **WHEN** the operator runs a search with the default configuration
- **THEN** the query includes the coding-agent, specification-review-verification, repository-context, and human-AI-workflow groups

### Requirement: Feature topic family
The default search MUST include four product-feature groups: chart and visualization generation, text and motion graphics, screen and demo video, and GUI agents.

#### Scenario: Feature groups are queried
- **WHEN** the operator runs a search with the default configuration
- **THEN** the query includes the chart-generation, text-motion, screen-video, and GUI-agent groups

### Requirement: No avatar topics
Default queries MUST NOT include talking-head, lip-sync, portrait animation, face reenactment, or 3D face reconstruction phrases.

#### Scenario: Avatar phrases are absent
- **WHEN** the operator runs a search with the default configuration
- **THEN** no query contains talking-head, lip-sync, portrait-animation, face-reenactment, or face-reconstruction phrases

### Requirement: Categories cover both families
The default search MUST limit results to `cs.SE`, `cs.AI`, `cs.CL`, `cs.HC`, `cs.GR`, `cs.CV`, and `cs.MM`.

#### Scenario: Category filter
- **WHEN** the operator runs a search with the default configuration
- **THEN** only papers in at least one of those categories are eligible

### Requirement: One topic per paper
When a paper matches several groups, it MUST be stored once, with the topic of the first matching group in configured order. Process groups MUST come before feature groups, and within each family the broadest group MUST come last.

#### Scenario: Paper matches two groups
- **WHEN** one paper matches both the coding-agent group and the GUI-agent group
- **THEN** the paper table has one row for it with topic `coding_agents`

### Requirement: Fresh corpus window
The default search window MUST start on 2025-01-01. Matches MUST be stored in this worktree's paper table. The search MUST NOT import rows from the avatar-papers corpus.

#### Scenario: Default date bound
- **WHEN** the operator runs a search without overriding the date range
- **THEN** papers submitted before 2025-01-01 are excluded

#### Scenario: Separate paper table
- **WHEN** a search adds papers
- **THEN** they are written to this worktree's paper table
- **AND** rows that exist only in the avatar-papers corpus are not copied in

### Requirement: arXiv items only
The collector MUST add only items that have an arXiv id. A blog post, product doc, or other URL without an arXiv id MUST NOT be added to the paper table.

#### Scenario: Non-arXiv source
- **WHEN** the only available source is a blog post or product document without an arXiv id
- **THEN** no row is added to the paper table
