# Development Overview
This document contains the project development outline and assignments as well as associated timeline and project roadmap. This is intended to be used as a tool for organizing our project development and understanding our needs to meet out timeline.

# Project Roadmap
This Gantt chart represents a starting point for understanding the timeline for our development and serves a roadmap for our development stages. This a high-level chart showing the different parts of the project and how development time can ovelap. Currently, this is non-finalized and is intended only as a starting point for discussing the relative timelines of tasks.

```mermaid
---
displayMode: compact
---
gantt
    title Data Model-Based Ingestion Pipeline Roadmap
    dateFormat  YYYY-MM-DD

    section Release Control
    Tracking Issue #186                     :milestone, 2025-12-10, 0d

    section 1 
    Move to uv as Python manager (#178)                 :done, 2025-11-01, 2025-12-01
    Reporting for JIRA (#182)                           :done, 2025-11-15, 2025-12-10
    Create a new development Roadmap (#172)             :active, 2025-12-10, 2026-01-15
    Re-align Tracking Tickets and Tasks (#173)          :2025-12-15, 2026-01-31
    Update Dependencies and Release Strategy (#180)     :2026-01-01, 2026-02-15
    First dm-bip release (#193)                         :2026-01-15, 2026-02-28
    Automate Release creation process (#194)            :2026-02-01, 2026-03-15
    Improve Documentation (#50)                         :2026-01-01, 2026-03-31
    Add Markdown plugin for Sphinx (#41)                :2026-02-15, 2026-03-31

    section Pilot Data Delivery 
    Tracking Issue #185                     :milestone, 2025-12-10, 0d

    section 2 
    Independent Re-ingestion of Dataset (#171)          :active, 2025-12-10, 2026-02-28

    section Quality Control 
    Tracking Issue #187                     :milestone, 2026-01-01, 0d

    section 3 
    Fix Measurement Observation Sets (#174)             :2026-01-01, 2026-02-15
    Create QC Documentation (#195)                      :2026-01-15, 2026-03-15
    Create QC metrics (#196)                            :2026-02-01, 2026-04-15

    section Pipeline Improvement
    Tracking Issue #188                     :milestone, 2026-01-15, 0d

    section 4 
    Full Ingestions Pipeline v2.0 (#168)                :done, 2025-10-01, 2025-12-01
    Create a Dockerfile for containerization (#176)     :done, 2025-11-01, 2025-12-15
    Add Docker to Dependencies (#179)                   :done, 2025-11-15, 2025-12-20
    Add tooling for SchemaAutomator/Schemasheets (#80)  :2026-01-15, 2026-03-01
    Generalize map_data.py with INCLUDE mapping (#166)  :2026-02-01, 2026-03-15
    Add data mapping to automation (#167)               :2026-02-15, 2026-04-01
    Enable offset calculations in LinkML-Map (#169)     :2026-03-01, 2026-04-15
    Add Containerization to Makefile (#177)             :2026-04-01, 2026-05-15
    Create tests for mapping script (#210)              :2026-04-15, 2026-06-01
    Enum derivations (#211)                             :2026-05-01, 2026-06-15

    section Audit Logs
    Tracking Issue #189                     :milestone, 2026-02-01, 0d

    section 5 
    Define audit log requirements                       :2026-02-01, 2026-03-15
    Implement human-readable logging                    :2026-03-01, 2026-05-01

    section DMC Integration
    Tracking Issue #191                     :milestone, 2026-03-01, 0d

    section 6 
    Add Containerization with Docker (#90)              :2026-03-01, 2026-04-15
    make a data dictionary template (#103)              :2026-03-15, 2026-05-01
    Improve Data Cleanup and add to Makefile (#170)     :2026-04-01, 2026-05-15
    Incorporate Stata YAML authoring tool (#175)        :2026-04-15, 2026-06-01
    Create GitHub workflow to container registry (#201) :2026-05-01, 2026-06-15
    Add variable digest files to pipeline (#204)        :2026-05-15, 2026-07-01
    Update Docker with uv (#208)                        :2026-06-01, 2026-07-15

    section Schema/Spec Explorer
    Tracking Issue #190                     :milestone, 2026-03-15, 0d

    section 7 
    Evaluate dynamic schema explorer                    :2026-03-15, 2026-05-01
    Integrate explorer with pipeline                    :2026-04-15, 2026-06-15

    section BDC User On-Demand
    Tracking Issue #192                     :milestone, 2026-04-01, 0d

    section 8 
    Post Pilot Toy Dataset Improvement (#117)           :2026-04-01, 2026-05-15
    Update README.md to current usage (#144)            :2026-04-15, 2026-05-31
    Packages without wheels for Python 3.13 (#151)      :2026-05-01, 2026-06-15
    Seven Bridges integration planning                  :2026-05-15, 2026-07-15
    User harmonization workflow                         :2026-06-15, 2026-08-15

    section AI Curation
    Tracking Issue #197                     :milestone, 2026-05-01, 0d

    section 9 
    Independent run of AI curation API (#198)           :2026-05-01, 2026-06-15
    Create script to run AI API (#199)                  :2026-06-01, 2026-07-15
    Integrate AI curation into pipeline                 :2026-07-01, 2026-09-15

    axisFormat %B
    tickInterval 1month
```

# Project Outline
This outline captures the main features shown in the project roadmap above, organized by tracking issue. Each section corresponds to a GANTT chart section and its associated GitHub tracking issue. Sub-issues are listed under each tracking category.

## 1. Release Control (Tracking: #186)
Procedures for controlling releases of tool-chains, repositories, and data sets.
- [x] Move to uv as Python manager (#178) - Roman
- [x] Reporting for JIRA (#182) - Corey
- [ ] Create a new development Roadmap (#172) - Corey
- [ ] Re-align Tracking Tickets and Development Tasks (#173) - Corey
- [ ] Update Dependencies and Create Release Strategy (#180)
- [ ] First dm-bip release (#193) - Corey
- [ ] Automate Release creation process (#194) - Corey
- [ ] Improve Documentation (#50) - Corey
- [ ] Add Markdown plugin for Sphinx (#41) - Patrick

## 2. Pilot Data Delivery (Tracking: #185)
Preparation, ingestion, and QC of the original pilot data set.
- [ ] Independent Re-ingestion of Dataset (#171) - Roman, Corey

## 3. Quality Control (Tracking: #187)
Procedures and workflows for quality control.
- [ ] Fix Measurement Observation Sets (#174)
- [ ] Create QC Documentation (#195)
- [ ] Create QC metrics (#196)

## 4. Pipeline Improvement (Tracking: #188)
Improving automation, testing, workflows, and integration.
- [x] Full Ingestions Pipeline v2.0 (#168)
- [x] Create a Dockerfile for containerization (#176)
- [x] Add Docker to Dependencies (#179) - Vessie, Corey
- [ ] Add tooling for SchemaAutomator/Schemasheets (#80) - Trish
- [ ] Generalize map_data.py with INCLUDE mapping (#166) - Trish, Corey
- [ ] Add data mapping to automation (#167)
- [ ] Enable offset calculations in LinkML-Map (#169) - Madan
- [ ] Add Containerization to Makefile (#177)
- [ ] Create tests for mapping script (#210) - Corey
- [ ] Enum derivations (#211) - Roman, Corey

## 5. Audit Logs (Tracking: #189)
Logging, auditability, and human-readable data provenance.
- [ ] Define audit log requirements
- [ ] Implement human-readable logging

## 6. DMC Integration (Tracking: #191)
Integrating the Harmonization Pipeline into DMC pre-ingestion.
- [ ] Add Containerization with Docker (#90) - Patrick, Stephen
- [ ] Make a data dictionary template (#103) - Trish
- [ ] Improve Data Cleanup and add to Makefile (#170) - Roman, Corey
- [ ] Incorporate Stata YAML authoring tool (#175)
- [ ] Create GitHub workflow to container registry (#201) - Patrick
- [ ] Add variable digest files to pipeline (#204)
- [ ] Update Docker with uv (#208) - Vessie, Corey

## 7. Schema/Spec Explorer (Tracking: #190)
Dynamic Schema or Transformation Specification explorer tools.
- [ ] Evaluate dynamic schema explorer
- [ ] Integrate explorer with pipeline

## 8. BDC User On-Demand (Tracking: #192)
Bringing the Harmonization Pipeline to BDC for user on-demand harmonization.
- [ ] Post Pilot Toy Dataset Improvement (#117)
- [ ] Update README.md to current usage (#144) - Roman, Corey
- [ ] Packages without wheels for Python 3.13 (#151) - Patrick
- [ ] Seven Bridges integration planning
- [ ] User harmonization workflow

## 9. AI Curation (Tracking: #197)
AI curation pipeline for improving data curation and specification creation.
- [ ] Independent run of AI curation API (#198)
- [ ] Create script to run AI API (#199) - Corey
- [ ] Integrate AI curation into pipeline
