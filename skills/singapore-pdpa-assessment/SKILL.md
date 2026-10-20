---
name: singapore-pdpa-assessment
description: Assess a proposed activity, product feature, process or document against Singapore's Personal Data Protection Act 2012 and the PDPC's advisory guidelines, obligation by obligation, with every finding tied to provision text actually retrieved. Use for PDPA compliance reviews, data protection impact questions and privacy checks on Singapore personal data.
---

# Singapore PDPA assessment

A PDPA review fails quietly in two ways: an obligation is never considered, or a finding rests
on a remembered version of a provision that has since been amended. This skill works from a
checklist of the Act's obligations and refuses any finding that relies on a section whose text
was not retrieved for this assessment.

## Set up

1. **The subject.** Get the activity, feature, process or document to assess, with enough
   facts to apply the Act: what personal data, about whom, collected how, used and disclosed
   for what, held where and for how long, and who processes it. Ask for missing facts that
   change an obligation's outcome; record the rest as assumptions.
2. **The law-as-at date.** Usually today, unless the question concerns past conduct.
3. **A private run** outside source control:
   `python <this skill>/scripts/assessment.py init <run> --subject "..." --subject-reference "..."
   --law-as-at YYYY-MM-DD [--items all|id,id]`. The checklist is in
   `references/obligations.json`; select only items that cannot apply with a recorded reason.
4. **Read [sources and versions](references/sources.md)** before retrieving anything.

## Retrieve the law, then assess

1. **Record the standards applied.** `add-standard <run> --name "Personal Data Protection Act 2012"
   --kind legislation --version "<version in force on the law-as-at date>" --how "<route>"`, and
   the PDPC guidelines with their revision date as `--kind guidance`.
2. **Retrieve each provision you rely on** for the law-as-at date, using the
   `singapore-legal-research` skill's statutory evidence procedure and access rules, or a copy
   the user supplies. Save the provision text and record it:
   `add-provision <run> --section 26 --file s26.txt --version "<version>" --how "<route>"`.
   Record schedules the same way (`--section "First Schedule"`). Check whether the 2025 and 2026
   amending Acts touched the provision before relying on it.
3. **Assess each checklist item.** Apply the provision text to the facts, using the guidelines
   for the Commission's interpretation. Record one or more findings:
   `finding <run> --item transfer --assessment gap --severity high --standard-ref "s 26(1)"
   --explanation "..." --recommendation "..." [--location "..."] [--quote "exact subject text"]`.
   - `meets`: the subject satisfies the obligation on the facts given;
   - `gap`: it does not; give a recommendation;
   - `risk`: it may not, depending on facts or interpretation; give a recommendation;
   - `unclear`: the facts do not allow an assessment; say what is needed;
   - `not-applicable`: explain why, for example no Singapore telephone numbers are messaged.
   Severity reflects consequence to individuals and the organisation, not effort to fix.
4. **Record limits** in the run's `gaps`, such as facts not supplied, a provision whose version
   could not be confirmed, or a guideline revision that predates an amendment.

## Check and deliver

Run `check <run>`. It fails when a checklist item is unaddressed, a gap or risk has no
recommendation, a quote does not appear in the subject, the Act's version is not recorded, a
provision text changed after it was recorded, or a finding cites a section or schedule whose
text was not retrieved. Retrieve the text; never remove the citation to make the check pass.

`export <run>` prints the `review@1` result for a workflow. In conversation, lead with the
gaps and risks by severity, each with its provision and recommendation, then the unclear items
and the facts needed, then the limitations.

A passing check shows coverage and that findings rest on retrieved text. It does not show the
assessments are legally correct; a responsible lawyer reviews them before they are relied upon.

## Boundaries

This skill assesses; it does not decide whether to proceed, notify the Commission or affected
individuals, or change a product. Never send a breach notification or contact the PDPC.
Do Not Call obligations have separate PDPC guidance, and sector-specific rules may also apply.
