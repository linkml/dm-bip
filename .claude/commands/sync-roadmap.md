# Sync Roadmap Command

Synchronize the DEVELOPMENT.md GANTT chart and Project Outline with GitHub issues.

## Steps

### 1. Fetch Current GitHub Issue State

Query GitHub for all relevant issues:

```bash
# Get all open tracking issues (labeled "Tracking")
gh issue list --repo linkml/dm-bip --state open --label "Tracking" --json number,title,state

# Get all issues (open and closed) with tracking category labels
# Excludes issues closed as NOT_PLANNED (duplicates, obsolete)
gh issue list --repo linkml/dm-bip --state all --limit 300 --json number,title,state,stateReason,labels,assignees | jq '[.[] | select(.labels | length > 0) | select(.stateReason != "NOT_PLANNED") | select(.labels[].name | test("Release Control|Pipeline Improvement|Quality Control|DMC Integration|BDC Application|Trans-Spec Authoring|Audit Logs|Data Delivery"))]'
```

### 2. Triage Unlabeled Issues

Check for open issues with no labels that would be invisible to the sync:

```bash
gh issue list --repo linkml/dm-bip --state open --limit 300 \
  --json number,title,labels \
  --jq '[.[] | select(.labels | length == 0)] | sort_by(.number) | .[] | "#\(.number)  \(.title)"'
```

For each unlabeled issue:
1. Read the issue body (`gh issue view NUMBER`)
2. Suggest a tracking label based on content:
   - Stream/format/schema/mapping work → Pipeline Improvement
   - BDC deployment, Docker, Seven Bridges, S3 → BDC Application
   - DMC coordination, NHLBI-BDC-DMC-HV → DMC Integration
   - Test coverage, linting, CI → Quality Control
   - Versioning, releases, packaging → Release Control
   - Data delivery, output QC → Data Delivery
   - Not ready for current roadmap → future
3. Present suggestions to the user for approval before applying labels
4. Apply approved labels, then re-run the step 1 query so they're included in the sync

### 3. Parse Current DEVELOPMENT.md

Read DEVELOPMENT.md and identify:
- All issues currently in the GANTT chart (by issue number in parentheses)
- Their current status (done, active, or pending)
- Their current date ranges
- All issues in the Project Outline
- Their completion status ([x] or [ ])

### 4. Identify Changes Needed

Compare GitHub state to DEVELOPMENT.md and categorize:

**New issues to add:**
- Issues in GitHub with tracking labels not in GANTT/Outline (already filtered: NOT_PLANNED issues excluded in Step 1)
- Determine which section based on label:
  - "Release Control" → section 1
  - "Data Delivery" → section 2
  - "Quality Control" → section 3
  - "Pipeline Improvement" → section 4
  - "Audit Logs" → section 5
  - "DMC Integration" → section 6
  - "BDC Application" → section 7
  - "Trans-Spec Authoring" → section 8

**Status changes:**
- Issues marked CLOSED in GitHub but not `done` in GANTT
- Issues marked CLOSED in GitHub but not `[x]` in Outline

**Missing infrastructure:**
- Issues without IDs in GANTT (need `i###` added)
- Issues without click directives

### 5. Date Handling Rules

**Allowed automatic adjustments:**
- Move start date EARLIER (sooner) - allowed
- Move end date LATER (further out) - allowed

**Prohibited adjustments (require user approval):**
- Move start date LATER - ask user with justification
- Move end date EARLIER - ask user with justification

**For new issues:**
- Place after all existing issues under the same tracker issue
- Use 8 week duration as default
- Start date should begin after the last existing issue in that section ends

### 6. Apply Changes

**CRITICAL: Never modify section header lines!**
- Section headers have significant trailing spaces (e.g., `section 1 `)
- Only edit task lines, tracking issue lines, and click directives
- Match existing indentation exactly (4 spaces)

**GANTT updates:**
- Add new tasks with ID: `:i###, start-date, end-date`
- Mark closed issues: `:done, i###, start-date, end-date`
- Add click directives at bottom: `click i### href "https://github.com/linkml/dm-bip/issues/###"`

**Outline updates:**
- Add new issues under correct section heading
- Use `- [ ]` for open, `- [x]` for closed
- Include assignee names (first names) if available
- Assignee mapping:
  - amc-corey-cox → Corey
  - ptgolden → Patrick
  - rjruizes → Roman
  - twhetzel → Trish
  - vbakalov → Vessie
  - gnawhnehpets → Stephen
  - madanucd → Madan

### 7. Report Changes

After applying changes, summarize:
- Issues added (with sections)
- Issues marked complete
- Date adjustments made
- Any issues requiring manual attention

### 8. Offer Rendered Preview (after PR is open)

Once the sync PR has been pushed, offer to render the updated `DEVELOPMENT.md` to PDF so the user can visually scan the Mermaid GANTT for layout/overflow issues before review. Don't render proactively — just offer; the user may prefer to look in the GitHub UI directly.

If the user agrees, render the GitHub blob view (which executes the Mermaid JS) via Chrome headless:

```bash
google-chrome --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --virtual-time-budget=15000 \
  --print-to-pdf=/tmp/development-pr<N>.pdf --print-to-pdf-no-header \
  "https://github.com/linkml/dm-bip/blob/<branch>/DEVELOPMENT.md"
```

Then `Read` the PDF and look for: bar text overflow, missing/misplaced rows, broken section headers, GANTT label collisions in compact mode.

## Usage Notes

- Run this command periodically to keep roadmap in sync
- Review suggested date changes before confirming prohibited adjustments
- New issues without clear labels may need manual section assignment
- Items without GitHub issue numbers (placeholders) are not affected
