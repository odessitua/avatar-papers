# Spec Delta

## Purpose

Defines the Confluence page tree for this radar so it can sit in the same space as the avatar Papers tree without sharing or overwriting those pages.

## ADDED Requirements

### Requirement: Sibling root page
Publishing MUST create or reuse a page titled `Papers AI Development` under the configured parent page. Publishing MUST NOT update the avatar `Papers` page or its children.

#### Scenario: First publish
- **WHEN** publish runs and no `Papers AI Development` page exists under the configured parent
- **THEN** a page titled `Papers AI Development` is created under that parent

#### Scenario: Avatar tree stays unchanged
- **WHEN** publish runs
- **THEN** the avatar `Papers` page body and the pages under it are not updated

### Requirement: Unique child titles
The Russian index, prompt page, keywords page, year pages, and week pages MUST use titles that differ from the avatar radar's titles for the same roles. A year page title MUST NOT be a bare year. A week page title MUST NOT be only the calendar span.

#### Scenario: Year page
- **WHEN** publish creates the page for 2026
- **THEN** its title is `2026 · AI Dev`
- **AND** the Russian year page title is `2026 · AI Dev (RU)`

#### Scenario: Week page
- **WHEN** publish creates the page for 16 Feb 2026 through 22 Feb 2026
- **THEN** its title is `AI Dev: Feb 16 - Feb 22, 2026`
- **AND** the Russian week page title is `AI Dev: Feb 16 - Feb 22, 2026 (RU)`

#### Scenario: Reference pages
- **WHEN** publish ensures the prompt and keywords pages
- **THEN** their titles are `Analysis Prompt · AI Dev` and `Search Keywords · AI Dev`
- **AND** the Russian index title is `RU · AI Dev`

### Requirement: Topic cell names the group
The year-table Topic cell MUST show the family mark and the group mark, and MUST NOT show the group key or the words `process` and `feature`. A legend above the table MUST be a grouped list. It MUST explain the family mark and name each group mark under that family. Process uses ⚙️. Feature uses 🎯.

#### Scenario: Process group
- **WHEN** a year-table row has topic `coding_agents`
- **THEN** its Topic cell contains ⚙️ and 🤖
- **AND** the cell does not contain `coding_agents`

#### Scenario: Feature group
- **WHEN** a year-table row has topic `chart_generation`
- **THEN** its Topic cell contains 🎯 and 📊
- **AND** the cell does not contain `chart_generation`

### Requirement: Index points at this tree
The `Papers AI Development` index MUST link to this radar's year pages, prompt page, and keywords page.

#### Scenario: Index update
- **WHEN** publish updates the index
- **THEN** each year link targets this radar's year page
- **AND** the prompt and keywords links target this radar's reference pages

### Requirement: Weekly report names this radar
The weekly Slack report header MUST name this radar and the week range. Each included paper MUST still show its arXiv title link, score, tags, and summary. The score threshold for inclusion MUST stay unchanged.

#### Scenario: Slack weekly report
- **WHEN** a weekly Slack report is sent
- **THEN** the header identifies the AI-dev radar and the week range
- **AND** each paper entry includes the arXiv link, score, tags, and summary
