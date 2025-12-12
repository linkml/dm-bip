# Sync Roadmap Command

Synchronize the DEVELOPMENT.md GANTT chart and Project Outline with GitHub issues.

## Steps

### 1. Fetch Current GitHub Issue State

Query GitHub for all relevant issues:

```bash
# Get all open tracking issues (labeled "Tracking")
gh issue list --repo linkml/dm-bip --state open --label "Tracking" --json number,title,state

# Get all issues (open and closed) with tracking category labels
gh issue list --repo linkml/dm-bip --state all --limit 200 --json number,title,state,labels,assignees | jq '[.[] | select(.labels | length > 0) | select(.labels[].name | test("Release Control|Pipeline Improvement|Quality Control|DMC Integration|BDC Application|AI Integration|Audit Logs|Schema Explorer|Data Delivery"))]'
```

### 2. Parse Current DEVELOPMENT.md

Read DEVELOPMENT.md and identify:
- All issues currently in the GANTT chart (by issue number in parentheses)
- Their current status (done, active, or pending)
- Their current date ranges
- All issues in the Project Outline
- Their completion status ([x] or [ ])

### 3. Identify Changes Needed

Compare GitHub state to DEVELOPMENT.md and categorize:

**New issues to add:**
- Issues in GitHub with tracking labels not in GANTT/Outline
- Determine which section based on label:
  - "Release Control" → section 1
  - "Data Delivery" → section 2
  - "Quality Control" → section 3
  - "Pipeline Improvement" → section 4
  - "Audit Logs" → section 5
  - "DMC Integration" → section 6
  - "Schema Explorer" → section 7
  - "BDC Application" → section 8
  - "AI Integration" → section 9

**Status changes:**
- Issues marked CLOSED in GitHub but not `done` in GANTT
- Issues marked CLOSED in GitHub but not `[x]` in Outline

**Missing infrastructure:**
- Issues without IDs in GANTT (need `i###` added)
- Issues without click directives

### 4. Date Handling Rules

**Allowed automatic adjustments:**
- Move start date EARLIER (sooner) - allowed
- Move end date LATER (further out) - allowed

**Prohibited adjustments (require user approval):**
- Move start date LATER - ask user with justification
- Move end date EARLIER - ask user with justification

**For new issues:**
- Place at end of section's timeline
- Use ~6 week duration as default
- Suggest dates based on section's existing range

### 5. Apply Changes

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

### 6. Report Changes

After applying changes, summarize:
- Issues added (with sections)
- Issues marked complete
- Date adjustments made
- Any issues requiring manual attention

## Usage Notes

- Run this command periodically to keep roadmap in sync
- Review suggested date changes before confirming prohibited adjustments
- New issues without clear labels may need manual section assignment
- Items without GitHub issue numbers (placeholders) are not affected
