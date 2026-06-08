# Automated Harmonization Orchestration — Design

**Status:** Draft · **Last updated:** 2026-06-08 · **Tracking issue:** [#267](https://github.com/linkml/dm-bip/issues/267)

> **Where this document lives.** This is the single design of record for the *end-to-end* automated harmonization pathway, not just the dm-bip slice. It lives in dm-bip for now because that is where the active engineering is. Over time it should migrate to the **Data Submission Tool (DST)** repo, as dm-bip settles into being a *tool the orchestrator consumes* rather than a place orchestration is reasoned about.

---

## 1. Purpose

Today the dm-bip harmonization pipeline runs **user-triggered** on BioData Catalyst (BDC) / Seven Bridges (SB): a person runs `dm-bip seven-bridges submit`, which creates and runs an SB task against data staged into an SB project.

The target is **automatic**: once a data submission has landed in its S3 store and the submission's conditions are met, the harmonization pipeline runs **without a human in the loop**, with the whole flow organized by the DST and actuated by JIRA.

This document describes that pathway whole, names what each system is responsible for, and states the concrete deliverable dm-bip owns.

---

## 2. Design philosophy

The DST is the **orchestrator by virtue of being the organizing principle**, not by being the code that does the organizing. It is intentionally a thin layer:

- **No duplicated effort.** The DST does not re-implement work that more central systems already own. It coordinates and *surfaces*.
- **Single sources of truth, per domain.** **JIRA** is the source of truth for the *submission lifecycle*; **Freshdesk** is the source of truth for the *support domain*. The DST reads from these and presents a unified, understandable view to users.
- **"Orchestration" includes the setup in other resources.** The DST's remit covers the configuration and coordination that lives in JIRA, Freshdesk, SB, and AWS to make the flow work — even though that machinery does not run *inside* the DST codebase.

The consequence for dm-bip: **dm-bip is a consumed tool.** Its job is to be cleanly invokable by the orchestrator and to do the harmonization work well. It should not accrete orchestration logic of its own. The deliverable we own is *"the DST/JIRA can fire off the workflow automatically"* — and we own that outcome even though most of the machinery (the JIRA rule, the SB volume, the service identity) does not live in this repo.

---

## 3. Actors and responsibilities

| Actor | Role | Source of truth for |
|---|---|---|
| **DST** (Django app, `NHLBI-BDC-DMC-DST`) | Self-service intake + lifecycle dashboard; organizing principle | Nothing of its own — it *mirrors* JIRA/Freshdesk |
| **JIRA** | Submission lifecycle state machine; the **actuator** of the trigger | Submission lifecycle, run parameters (custom fields) |
| **Freshdesk** | Support/ticketing | Support domain |
| **NIH RAS / NIH SSO** | Human **login** (OIDC) to BDC/SB/DST | User identity at login time only |
| **Seven Bridges (Velsera)** | Runs the harmonization app; exposes the REST API that starts tasks | Task/app execution |
| **S3 submission bucket** | Where submitted data lands; DMC-created per submission | The raw submitted data |
| **dm-bip** | The harmonization pipeline app (this repo) | The harmonization transform itself |

A correction to an earlier assumption worth stating plainly: **RAS is not a workflow credential.** It is a login-focused authenticator. The automated pipeline never performs a RAS login; RAS only governs *human* access to the surrounding systems. Workflow credentials are SB tokens (see §6).

---

## 4. End-to-end flow

```mermaid
sequenceDiagram
    participant Sub as Data submitter
    participant DST as DST (dashboard)
    participant JIRA as JIRA (lifecycle + actuator)
    participant S3 as S3 submission bucket
    participant SB as Seven Bridges API
    participant DMB as dm-bip app (on SB)
    participant FD as Freshdesk

    Sub->>DST: Create submission (intake form)
    DST->>JIRA: Create/track ticket (lifecycle mirror)
    Note over JIRA,S3: DMC creates bucket; submitter granted write via their AWS IAM ARN
    Sub->>S3: Upload data
    JIRA->>JIRA: Status transitions as conditions are met
    Note over JIRA: On transition into "ready for pipeline"
    JIRA->>SB: Automation rule "Send web request"<br/>POST /v2/tasks?action=run (X-SBG-Auth-Token)
    SB->>DMB: Create + run task with inputs from JIRA fields
    DMB->>S3: Read raw data (via SB volume → RawSource)
    DMB->>DMB: prepare → schema → validate → map (BDCHM)
    DMB->>S3: Write harmonized output
    DMB->>FD: Notify done/failed (structured ticket — §9.2)
    FD-->>DST: Surfaced to coordinator
    Note over FD,JIRA: Coordinator advances the JIRA issue
    JIRA-->>DST: Status updates
    DST-->>Sub: Surfaces progress / completion
```

The pivotal substitution is simple: **the JIRA automation rule replaces the human who runs `seven-bridges submit` today.** The task body it POSTs is the same shape dm-bip already constructs.

---

## 5. The parameter contract (JIRA fields → SB task inputs)

The JIRA ticket already carries every parameter a harmonization run needs, as structured custom fields (see `tracker/jira_agent.py` in the DST). This mapping is the **interface contract** between the orchestrator and dm-bip:

| JIRA field | ID | → SB task input | Notes |
|---|---|---|---|
| Bucket URL | `customfield_15207` | `RawSource` (via SB volume) | The S3 location of the submitted data |
| Study Name | `customfield_15203` | `Schema` | Cohort/study identifier |
| Consent Code | (intake `consent_code`) | consent suffix | Consent group |
| Accession Number | `customfield_15206` | run identity | dbGaP `phs` accession |
| Version Update | `customfield_15205` | run identity | Submission version |
| Gen3 Project Name | `customfield_15208/9` | (downstream) | For Gen3 indexing |

Keeping this table accurate as fields evolve is part of owning the deliverable, even though the fields are defined in the DST.

---

## 6. Authentication & credentials

- **Human access** to BDC/SB/DST is via **NIH RAS/SSO** (OIDC). Not used by the workflow.
- **Workflow credential** is a Seven Bridges **auth token** (`X-SBG-Auth-Token`). The automated `POST` runs *as the identity that owns the token*.
  - **v1:** a developer creates a token for a dedicated **service user**. Stored as a **hidden header** in the JIRA automation rule.
  - **Later:** a true SB **service account**, if/when Velsera supports one (undocumented today — see §10).
- **S3 access** for reading the bucket is the DMC's own AWS concern, attached to SB as a **volume** using static IAM keys — **decoupled from RAS**. The submitter's `aws_iam` ARN governs *their write* to the bucket, not the pipeline's read.

**Operational note:** SB does not document a token expiry/rotation policy. Treat the token as long-lived-until-regenerated; rotation requires updating the stored value in the JIRA rule.

---

## 7. Data access

The submission bucket is **created and owned by the DMC** (the DST `Ticket` lifecycle includes a "bucket created" stage; the submitter is granted write via their IAM ARN). Therefore the pipeline's *read* path is ours to provision.

- **v1 (realistic):** Attach the submission bucket as a **Seven Bridges S3 volume**. A volume presents S3 objects as stage-able platform files — i.e. the same `Directory`/file shape dm-bip already consumes as `RawSource`. **This means little-to-no new data-fetch code in dm-bip.** Do **not** bake static AWS keys into the container (the discarded early sketch) — the volume is the sanctioned, audited mechanism.
- **Aspirational:** A **DRS-indexed** store (GA4GH DRS API, `X-SBG-Auth-Token`-scoped). The data-source seam (§8) should be designed to allow DRS later, but v1 does not depend on it. This system has competing interests; the DRS target may never be reached, and the design must not block on it.

---

## 8. dm-bip's deliverable (what we own here)

The end-state is mostly assembly of documented primitives that live *outside* this repo. dm-bip's concrete, ownable slice:

1. **Pluggable data-source seam.** Today there is exactly one seam where data arrives on local disk (`bdc-workflow.sh` validates a local `--source` dir; `prepare_input.py` globs it). Generalize *behind that seam* so the source can be: a mounted directory (today) · an SB volume path (v1) · DRS object IDs (later). Everything downstream is unchanged.
2. **Accept orchestrator-supplied parameters.** Ensure the app inputs accept the parameters the JIRA payload sends (bucket → `RawSource`, study → `Schema`, consent, accession, version).
3. **Output write-back.** Write harmonized BDCHM output back to the designated bucket/location.
4. **Idempotency guard.** A re-fired trigger (JIRA "Send web request" can double-fire) must not launch duplicate harmonizations. Guard on a stable run identity (see §9).
5. **A clean "start a run" surface.** The existing `seven-bridges` verb-group already builds the task body for a human. Keep that path the single, parameterized entrypoint an external actuator (JIRA, or later the DST) calls — do not fork orchestration logic into the pipeline.

**Stage 0** (no external dependencies, safe to start now) = items **1** and **2**.

---

## 9. Open design decisions

These are the genuine choices, not yet made:

1. **Volume vs. DRS** for the bucket read path. *Recommendation:* SB volume for v1; design the seam to allow DRS later. Accept that DRS may never arrive.
2. **Close-the-loop mechanism — RESOLVED (see §9a).** ~~push the pipeline → JIRA, vs. poll SB task status~~. Decided: the pipeline emits a structured **notification to Freshdesk** at end-of-run; the DST surfaces it and a coordinator advances the JIRA issue. Rationale and the remaining sub-decision are in §9a.
3. **Run identity / idempotency key.** *Recommendation:* the **JIRA issue key** as the correlation ID for the run, with **accession + version** as the semantic identity for dedupe. (Open: confirm whether a submission/ticket ID is the more natural unique key.)
4. **Service identity.** Dedicated SB service *user* + token for v1; true service account later (pending Velsera).

---

## 9a. Close-the-loop design (resolved)

**Decision:** the harmonization run emits a **structured notification to Freshdesk** on completion — success *or* failure. Freshdesk auto-creates a ticket (a documented first-class feature: sender → requester, subject → subject, body → description; creation-time automations can tag/route). The DST already integrates Freshdesk (`tracker/freshdesk_agent.py`) and surfaces it; a coordinator advances the JIRA lifecycle issue, correlating via the **JIRA issue key** carried in the notification.

**Why this over the alternatives:**
- **No new auth surface in the pipeline** beyond a send path — lighter than granting the pipeline JIRA write credentials (a "push to JIRA" design) or standing up a poller.
- **Leans on existing single-sources-of-truth** — Freshdesk owns the support domain and the DST already reads it. No duplicated orchestration; consistent with the DST philosophy (§2).
- **Covers both outcomes and carries the correlation key**, so the coordinator can bridge it to the lifecycle issue.
- **Keeps a human gate** in the controlled-access path before the JIRA issue advances — acceptable, arguably desirable, for v1.

**Why the pipeline sends — not SB's native email:** SB task-completion emails go only to the *account holder's* address (no documented arbitrary/shared recipient), carry undocumented content (essentially a task-page link), and only the *failure* email is guaranteed. So we control the content ourselves.

**Open sub-decision — send mechanism:** **Freshdesk REST API** (`POST /api/v2/tickets`, structured fields, needs an API key) *(recommended)* vs. **SMTP to a Freshdesk intake mailbox** (simplest, but needs an outbound mail path from the container). Resolve at Stage 2.

**Backstop (optional):** for a hard container crash (OOM/kill) before the pipeline can notify, route the SB service user's account email to the same Freshdesk intake as a catch-all — the one case where SB's native failure email earns its keep.

**Minor domain nuance:** a "harmonization done" notice is a *lifecycle* event entering the *support* system. Pragmatic and intentional for v1; if full automation is later wanted, the Freshdesk ticket (or a poller) could drive the JIRA transition directly.

---

## 10. Implementation staging

| Stage | Work | Owner | Blocked on |
|---|---|---|---|
| **0** | Pluggable data-source seam (`resolve_source.py` helper + tests, mirroring #324) + accept orchestrator params + log-only notify hook | dm-bip | nothing — start now |
| **1** | SB S3 volume over bucket; JIRA automation rule (transition → `POST /v2/tasks?action=run`, field mapping); service user + token | You (JIRA side) + BDC/Velsera | decision §9.1, §9.4 |
| **2** | Freshdesk notification (`notify.py` → API per §9a); output write-back; idempotency guard | dm-bip + Freshdesk | §9a send mechanism, §9.3 key |
| **3** | True service account; DRS-indexed source | BDC/Velsera | external |

---

## 11. Open questions for BDC / NHLBI / Velsera

1. **Service account:** does SB/BDC support a non-user service account, or is a dedicated service *user* the only option? What is the token expiry/rotation policy on the BDC instance?
2. **Data path sanction:** is an SB **volume** over the submission bucket the sanctioned path for automated controlled-access processing, or is DRS required?
3. **DRS timeline:** is a DRS-indexed submission store realistically on the roadmap, or should we assume volume-over-S3 indefinitely?
4. **Trigger surface:** confirmed there is no inbound SB webhook/event surface beyond the REST API (so JIRA must be the active caller). Confirm no undocumented RHEO/automation trigger exists.

---

## 12. References

- dm-bip pipeline data seam: `scripts/workflow/bdc-workflow.sh`, `src/dm_bip/cleaners/prepare_input.py`, `src/dm_bip/seven_bridges/`
- DST: `RTIInternational/NHLBI-BDC-DMC-DST` — `api/tracker/jira_agent.py` (field map), `api/tracker/models.py` (`Ticket` lifecycle), `api/nihsso/` (RAS/SSO login)
- SB API — create task: <https://docs.sevenbridges.com/reference/create-a-new-task> (supports `?action=run`)
- SB API — run task: <https://docs.sevenbridges.com/reference/perform-an-action-on-a-specific-task>
- BDC API overview/auth: <https://sb-biodatacatalyst.readme.io/docs/the-api>
- SB S3 volumes (IAM keys): <https://sb-biodatacatalyst.readme.io/docs/amazon-web-services-simple-storage-service-aws-s3-volumes>
- BDC DRS API: <https://sb-biodatacatalyst.readme.io/reference/drs-api>
- JIRA Automation — Send web request: <https://support.atlassian.com/cloud-automation/docs/jira-automation-actions/>
- NIH RAS service offerings: <https://auth.nih.gov/docs/RAS/serviceofferings.html>
