# TASK_<ID>_<slug>

## Identity

- State: `PROPOSED`
- Base revision: `<exact git SHA>`
- Feature cell: `<features/<feature> or repository-wide>`
- Owner role: `<registry role>`
- Reviewer role(s): `<registry role(s)>`

## Objective

State one bounded result that can be independently reviewed.

## Allowed write paths

- `<path or path prefix>`

## Forbidden write paths

- `<path or path prefix>`

## Inputs and dependencies

- `<required checkpoint, issue, source revision, prior task, or artifact>`

## Acceptance evidence

- [ ] exact base was verified before implementation
- [ ] focused tests or validation defined for this slice pass
- [ ] relevant compatibility boundary was checked
- [ ] generated or derived evidence is reproducible where applicable
- [ ] no lifecycle or trust promotion occurred outside the task objective
- [ ] reviewer can identify the exact implementation revision

## Findings outside scope

Record discoveries here without expanding the task.

## Handoff target

- Next role: `<role>`
- Expected handoff: `<review, integration, research, compatibility, or checkpoint>`
