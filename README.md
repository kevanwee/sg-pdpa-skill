# sg-pdpa-skill

An agent skill for assessing an activity, product feature, process or document against
Singapore's Personal Data Protection Act 2012 and the PDPC's Advisory Guidelines on Key
Concepts, obligation by obligation. Works with Codex and Claude Code. The helper is
standard-library Python 3.11+.

## Why

PDPA reviews fail quietly: an obligation is never considered, or a finding rests on a
remembered version of a provision that has since been amended. This skill works from a checklist
of the Act's obligations, and its check refuses any finding that relies on a section whose text
was not retrieved for that assessment.

## What the check refuses

| Refused | Because |
|---|---|
| A finding citing a section or schedule whose text was not retrieved in this run | The law must be read, not remembered |
| A provision text changed after it was recorded | The evidence changed under the finding |
| A checklist item left unaddressed | Coverage is part of the result |
| A gap or risk without a recommendation | A finding should say what to do |
| A quote that does not appear in the subject | Findings rest on what the subject actually says |
| An assessment with no recorded version of the Act | Version matters: the Act was amended in 2025 and 2026 |

A passing check shows coverage and that findings rest on retrieved text. It does not show that
the assessments are legally correct.

## Sources

The checklist follows the table of contents of the Act as shown on Singapore Statutes Online
as current at 20 October 2026, and page references to the PDPC Advisory Guidelines on Key
Concepts revised 29 April 2026. The skill indexes these sources; it does not reproduce them.
See [sources and versions](skills/singapore-pdpa-assessment/references/sources.md), including
two open points: what the 2025 and 2026 amending Acts changed, and the status of the Part 6B
that section 4 refers to.

Provision text is retrieved per assessment, using
[sg-legalresearch-skill](https://github.com/kevanwee/sg-legalresearch-skill)'s statutory
evidence procedure or a copy the user supplies.

## Use

See [SKILL.md](skills/singapore-pdpa-assessment/SKILL.md). Install by copying
`skills/singapore-pdpa-assessment` into `.claude/skills/` or `.agents/skills/`, or with the
[legal engineering toolkit](https://github.com/kevanwee/legal-engineering-manifesto) launcher,
which binds it to the `review@1` contract.

## Status

The checklist, sources index and check are tested with synthetic fixtures. The obligation map
and assessment method have not yet been reviewed by a data protection lawyer, and the effect of
the 2025 and 2026 amendments has not been examined.

## Test

```
python -m unittest discover -s tests -v
```

## Licence

MIT. See [LICENSE](LICENSE). The PDPA and PDPC guidelines are not reproduced and are not
licensed by this project.
