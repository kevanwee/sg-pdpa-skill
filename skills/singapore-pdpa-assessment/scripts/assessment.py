"""PDPA assessment records: every obligation considered, every finding tied to provision text actually retrieved.

Standard library only. Commands:
    init RUN --subject TEXT --subject-reference WHERE --law-as-at YYYY-MM-DD [--items all|id,id]
    add-standard RUN --name NAME --kind legislation|guidance|policy|playbook --version TEXT --how TEXT
    add-provision RUN --section 13 [--section 14 ...] --file TEXT_FILE --version TEXT --how TEXT
    finding RUN --item ID --assessment meets|gap|risk|unclear|not-applicable --severity high|medium|low|info
            --standard-ref "s 13(1)" --explanation TEXT [--recommendation TEXT] [--location TEXT] [--quote TEXT]
    check RUN
    export RUN

Sections cited in a standard reference ("s 13", "ss 21 and 22", "s 26D(1)", "First Schedule") must have
their retrieved text recorded with add-provision before a finding relying on them passes the check.
Exit codes: 0 ok, 1 check failed, 2 usage or input error.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ASSESSMENTS = ("meets", "gap", "risk", "unclear", "not-applicable")
SEVERITIES = ("high", "medium", "low", "info")
KINDS = ("legislation", "guidance", "policy", "playbook")
SECTION = re.compile(r"\b(?:ss?|sections?)\.?\s+((?:\d+[A-Z]*(?:\(\w+\))*)(?:\s*(?:,|and|to|-|–)\s*\d+[A-Z]*(?:\(\w+\))*)*)", re.I)
NUMBER = re.compile(r"\d+[A-Z]*")
SCHEDULE = re.compile(r"\b(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh)\s+Schedule\b", re.I)
STANDARD_LIMITS = [
    "A passing check shows every selected obligation was considered and every finding relies on provision text "
    "retrieved in this assessment; it does not show the assessments are legally correct.",
    "PDPC guidelines indicate the Commission's interpretation and may predate later amendments to the Act.",
]


class UsageError(Exception):
    pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collapse(text):
    return re.sub(r"\s+", " ", text).strip()


def load(run):
    path = Path(run) / "run.json"
    if not path.is_file():
        raise UsageError(f"No run.json in {run}; run init first")
    return json.loads(path.read_text(encoding="utf-8"))


def save(run, data):
    (Path(run) / "run.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def checklist():
    return json.loads((HERE / "references" / "obligations.json").read_text(encoding="utf-8"))["items"]


def cited_sections(reference):
    """Section numbers and schedules named in a standard reference, normalised for matching."""
    found = set()
    for match in SECTION.finditer(reference):
        found.update(n.upper() for n in NUMBER.findall(re.sub(r"\(\w+\)", "", match.group(1))))
    found.update(f"{m.group(1).title()} Schedule" for m in SCHEDULE.finditer(reference))
    return found


def cmd_init(args):
    run = Path(args.run)
    if (run / "run.json").exists():
        raise UsageError("run.json already exists; use a fresh run folder")
    date.fromisoformat(args.law_as_at)
    items = checklist()
    known = {i["id"] for i in items}
    selected = sorted(known) if args.items == "all" else [s.strip() for s in args.items.split(",") if s.strip()]
    unknown = set(selected) - known
    if unknown or not selected:
        raise UsageError(f"Unknown checklist items {sorted(unknown)}; choose from {sorted(known)}")
    run.mkdir(parents=True, exist_ok=True)
    (run / "subject.txt").write_text(args.subject, encoding="utf-8")
    data = {"schema_version": 1, "run_id": uuid.uuid4().hex,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "subject_reference": args.subject_reference, "subject_sha256": sha256(run / "subject.txt"),
            "law_as_at": args.law_as_at, "items": [i for i in selected],
            "standards": [], "provisions": [], "findings": [], "gaps": [], "review": ""}
    save(run, data)
    return {"status": "initialised", "run_id": data["run_id"], "items": selected}


def cmd_add_standard(args):
    data = load(args.run)
    data["standards"].append({"name": args.name, "kind": args.kind, "version": args.version, "how_obtained": args.how})
    save(args.run, data)
    return {"status": "added", "standards": len(data["standards"])}


def cmd_add_provision(args):
    run, data = Path(args.run), load(args.run)
    sections = []
    for section in args.section:
        schedule = SCHEDULE.fullmatch(section.strip())
        if schedule:
            sections.append(f"{schedule.group(1).title()} Schedule")
        elif NUMBER.fullmatch(section.strip().upper()):
            sections.append(section.strip().upper())
        else:
            raise UsageError(f"Section must look like 13, 26D or 'First Schedule'; got {section!r}")
    number = len(data["provisions"]) + 1
    folder = run / "provisions"
    folder.mkdir(exist_ok=True)
    kept = folder / f"P{number}.txt"
    shutil.copyfile(args.file, kept)
    if not kept.read_text(encoding="utf-8").strip():
        kept.unlink()
        raise UsageError("Provision text is empty")
    record = {"id": f"P{number}", "sections": sections, "file": kept.relative_to(run).as_posix(),
              "sha256": sha256(kept), "version": args.version, "how_obtained": args.how}
    data["provisions"].append(record)
    save(run, data)
    return {"status": "added", "provision": record}


def cmd_finding(args):
    data = load(args.run)
    if args.item not in data["items"]:
        raise UsageError(f"{args.item} is not a selected checklist item: {data['items']}")
    finding = {"id": f"F{len(data['findings']) + 1}", "item": args.item, "standard_ref": args.standard_ref,
               "assessment": args.assessment, "severity": args.severity, "explanation": args.explanation}
    for key in ("recommendation", "location", "quote"):
        if getattr(args, key):
            finding[key] = getattr(args, key)
    data["findings"].append(finding)
    save(args.run, data)
    return {"status": "recorded", "finding": finding}


def run_check(run, data):
    errors, warnings = [], []
    run = Path(run)
    if sha256(run / "subject.txt") != data["subject_sha256"]:
        errors.append("subject text changed after the assessment started")
    subject = collapse((run / "subject.txt").read_text(encoding="utf-8")).lower()
    retrieved = set()
    for provision in data["provisions"]:
        path = run / provision["file"]
        if not path.is_file() or sha256(path) != provision["sha256"]:
            errors.append(f"{provision['id']}: provision text missing or changed since it was recorded")
        else:
            retrieved.update(provision["sections"])
    if not any(s["kind"] == "legislation" and "personal data protection act" in s["name"].lower() and s["version"].strip()
               for s in data["standards"]):
        errors.append("record the Personal Data Protection Act 2012 as a legislation standard with the version applied")
    if not any(s["kind"] == "guidance" for s in data["standards"]):
        warnings.append("no PDPC guidance recorded as a standard; say why if none was used")
    addressed = {f["item"] for f in data["findings"]}
    for item in data["items"]:
        if item not in addressed:
            errors.append(f"{item}: not addressed; record a finding or mark it not-applicable with reasons")
    for finding in data["findings"]:
        label = f"{finding['id']} ({finding['item']})"
        if finding["assessment"] in ("gap", "risk") and not finding.get("recommendation"):
            errors.append(f"{label}: a {finding['assessment']} needs a recommendation")
        if finding.get("quote") and collapse(finding["quote"]).lower() not in subject:
            errors.append(f"{label}: quoted text does not appear in the subject")
        if finding["assessment"] == "not-applicable":
            continue
        cited = cited_sections(finding["standard_ref"])
        if not cited:
            errors.append(f"{label}: cite the provision relied on, e.g. 's 13(1)'")
        for section in sorted(cited - retrieved):
            errors.append(f"{label}: relies on {section if 'Schedule' in section else 's ' + section} without its retrieved text; "
                          "record it with add-provision")
    if not data["review"].strip():
        warnings.append("review is empty: record who reviewed the assessment and what was rechecked")
    return {"status": "fail" if errors else "pass", "errors": errors, "warnings": warnings,
            "checked": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def cmd_check(args):
    data = load(args.run)
    result = run_check(args.run, data)
    (Path(args.run) / "check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def cmd_export(args):
    data = load(args.run)
    result = run_check(args.run, data)
    addressed = {f["item"] for f in data["findings"]}
    not_addressed = [item for item in data["items"] if item not in addressed]
    limitations = [g for g in data["gaps"] if str(g).strip()] + STANDARD_LIMITS
    if result["status"] != "pass":
        limitations.insert(0, "Assessment check failed: " + "; ".join(result["errors"][:5]))
    standards = [{"name": s["name"], "version": s["version"], "how_obtained": s["how_obtained"]} for s in data["standards"]]
    if not standards:
        standards = [{"name": "Personal Data Protection Act 2012", "version": "not recorded", "how_obtained": "not recorded"}]
    return {"standards_applied": standards, "findings": data["findings"],
            "coverage": {"items_total": len(data["items"]), "items_addressed": len(data["items"]) - len(not_addressed),
                         "not_addressed": not_addressed},
            "record": {"status": result["status"], "location": str(Path(args.run).resolve())},
            "limitations": limitations}


def parser():
    p = argparse.ArgumentParser(prog="assessment.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("init")
    s.add_argument("run")
    s.add_argument("--subject", required=True)
    s.add_argument("--subject-reference", required=True)
    s.add_argument("--law-as-at", required=True)
    s.add_argument("--items", default="all")
    s = sub.add_parser("add-standard")
    s.add_argument("run")
    s.add_argument("--name", required=True)
    s.add_argument("--kind", required=True, choices=KINDS)
    s.add_argument("--version", required=True)
    s.add_argument("--how", required=True)
    s = sub.add_parser("add-provision")
    s.add_argument("run")
    s.add_argument("--section", action="append", required=True)
    s.add_argument("--file", required=True)
    s.add_argument("--version", required=True)
    s.add_argument("--how", required=True)
    s = sub.add_parser("finding")
    s.add_argument("run")
    s.add_argument("--item", required=True)
    s.add_argument("--assessment", required=True, choices=ASSESSMENTS)
    s.add_argument("--severity", required=True, choices=SEVERITIES)
    s.add_argument("--standard-ref", required=True)
    s.add_argument("--explanation", required=True)
    for name in ("--recommendation", "--location", "--quote"):
        s.add_argument(name)
    for name in ("check", "export"):
        sub.add_parser(name).add_argument("run")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    handlers = {"init": cmd_init, "add-standard": cmd_add_standard, "add-provision": cmd_add_provision,
                "finding": cmd_finding, "check": cmd_check, "export": cmd_export}
    try:
        result = handlers[args.command](args)
    except (UsageError, OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if args.command == "check" and result["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
