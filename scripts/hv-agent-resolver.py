#!/usr/bin/env python3
"""Resolve HappyVertical agent definitions into local generated files.

The resolver composes these layers:

1. dotfiles baseline workflows
2. have-config organization standard
3. optional profile defaults, such as Hermes
4. Context Forge install-time snapshot
5. machine-local overrides

Commands and skills use winner-takes-all resolution by layer priority. Agent
documents are cumulative and assembled in layer order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LAYER_PRIORITIES = {
    "dotfiles": 10,
    "have-config": 20,
    "profile": 25,
    "contextforge": 30,
    "local": 40,
}

TARGETS = {
    "agents": "AGENTS.md",
    "codex": "AGENTS.md",
    "claude": "CLAUDE.md",
}


@dataclass(frozen=True)
class SourceLayer:
    name: str
    root: Path
    manifest: Path | None
    priority: int
    available: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class Candidate:
    kind: str
    agent: str
    name: str
    layer: str
    priority: int
    source: str
    path: Path | None = None
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.agent}:{self.kind}:{self.name}"

    def digest(self) -> str:
        if self.content is not None:
            return sha256_text(self.content)
        if self.path is None:
            return sha256_text("")
        return sha256_path(self.path)


@dataclass
class DocSnippet:
    snippet_id: str
    targets: list[str]
    layer: str
    priority: int
    source: str
    path: Path | None = None
    content: str | None = None

    def read(self) -> str:
        if self.content is not None:
            return self.content.rstrip() + "\n"
        if self.path is None:
            return ""
        return self.path.read_text(encoding="utf-8").rstrip() + "\n"

    def digest(self) -> str:
        if self.content is not None:
            return sha256_text(self.content)
        if self.path is None:
            return sha256_text("")
        return sha256_path(self.path)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()

    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(p for p in path.rglob("*") if p.is_file()):
            digest.update(str(child.relative_to(path)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(child.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    raw = Path(os.path.expandvars(os.path.expanduser(value)))
    if raw.is_absolute():
        return raw
    return root / raw


def source_label(layer: str, root: Path, path: Path | None, content: str | None) -> str:
    if path is None:
        return f"{layer}:inline:{sha256_text(content or '')[:12]}"
    try:
        rel = path.relative_to(root)
        return f"{layer}:{rel}"
    except ValueError:
        return f"{layer}:{path}"


def expand_agents(agent: str, kind: str) -> list[str]:
    if agent != "all":
        return [agent]
    if kind == "command":
        return ["claude", "codex"]
    return ["codex"]


def doc_target_matches(target: str, snippet_targets: list[str]) -> bool:
    if "all" in snippet_targets:
        return True
    if target == "agents":
        return "agents" in snippet_targets or "codex" in snippet_targets
    if target == "codex":
        return "codex" in snippet_targets or "agents" in snippet_targets
    return target in snippet_targets


def split_profiles(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def detect_profiles(home_dir: Path) -> tuple[list[str], list[str]]:
    explicit = split_profiles(os.environ.get("HV_AGENT_PROFILE") or os.environ.get("AGENT_PROFILE"))
    if explicit:
        return explicit, ["profile selected from HV_AGENT_PROFILE/AGENT_PROFILE"]

    hermes_markers = [
        os.environ.get("HERMES"),
        os.environ.get("HERMES_AGENT"),
        os.environ.get("HERMES_AGENT_ID"),
        os.environ.get("HERMES_HOME"),
    ]
    if any(marker for marker in hermes_markers):
        return ["hermes"], ["Hermes profile detected from HERMES environment"]

    hermes_home = Path(os.environ.get("HERMES_HOME", str(home_dir / ".hermes"))).expanduser()
    if (hermes_home / "profile.json").exists() or (hermes_home / ".profile-hermes").exists():
        return ["hermes"], [f"Hermes profile detected from {hermes_home}"]

    return [], ["no agent profile detected"]


def manifest_layer(name: str, root: Path, manifest_name: str, default_priority: int) -> SourceLayer:
    manifest = root / manifest_name
    if manifest.exists():
        data = load_json(manifest)
        notes: list[str] = []
        declared_priority = data.get("priority")
        if declared_priority is not None and int(declared_priority) != default_priority:
            notes.append(f"declared priority {declared_priority} ignored; using fixed {default_priority}")
        return SourceLayer(name, root, manifest, default_priority, True, notes)
    if name == "local" and root.exists():
        return SourceLayer(name, root, None, default_priority, True, [f"no {manifest}; using convention-based overrides"])
    return SourceLayer(name, root, None, default_priority, False, [f"missing {manifest}"])


def collect_manifest(layer: SourceLayer) -> tuple[list[Candidate], list[DocSnippet], list[dict[str, Any]], list[dict[str, Any]]]:
    if not layer.available or layer.manifest is None:
        return [], [], [], []

    data = load_json(layer.manifest)
    root = layer.root
    priority = layer.priority
    layer_name = layer.name

    candidates: list[Candidate] = []
    docs: list[DocSnippet] = []

    for item in data.get("skills", []):
        path = resolve_path(root, item.get("path"))
        content = item.get("content")
        name = item["name"]
        agent = item.get("agent", "codex")
        for expanded_agent in expand_agents(agent, "skill"):
            candidates.append(
                Candidate(
                    kind="skill",
                    agent=expanded_agent,
                    name=name,
                    layer=layer_name,
                    priority=priority,
                    path=path,
                    content=content,
                    source=source_label(layer_name, root, path, content),
                    metadata={k: v for k, v in item.items() if k not in {"path", "content"}},
                )
            )

    for item in data.get("commands", []):
        path = resolve_path(root, item.get("path"))
        content = item.get("content")
        name = item["name"]
        agent = item.get("agent", "all")
        for expanded_agent in expand_agents(agent, "command"):
            candidates.append(
                Candidate(
                    kind="command",
                    agent=expanded_agent,
                    name=name,
                    layer=layer_name,
                    priority=priority,
                    path=path,
                    content=content,
                    source=source_label(layer_name, root, path, content),
                    metadata={k: v for k, v in item.items() if k not in {"path", "content"}},
                )
            )

    for item in data.get("agent_docs", []):
        path = resolve_path(root, item.get("path"))
        content = item.get("content")
        docs.append(
            DocSnippet(
                snippet_id=item["id"],
                targets=list(item.get("targets", ["agents"])),
                layer=layer_name,
                priority=priority,
                path=path,
                content=content,
                source=source_label(layer_name, root, path, content),
            )
        )

    return candidates, docs, data.get("env_requirements", []), data.get("services", [])


def collect_local_conventions(root: Path, priority: int) -> tuple[list[Candidate], list[DocSnippet]]:
    candidates: list[Candidate] = []
    docs: list[DocSnippet] = []

    skill_roots = [
        ("codex", root / "skills"),
        ("codex", root / "skills" / "codex"),
        ("claude", root / "skills" / "claude"),
    ]
    for agent, skill_root in skill_roots:
        if not skill_root.is_dir():
            continue
        for skill_dir in sorted(p for p in skill_root.iterdir() if p.is_dir()):
            if (skill_dir / "SKILL.md").exists():
                candidates.append(
                    Candidate(
                        kind="skill",
                        agent=agent,
                        name=skill_dir.name,
                        layer="local",
                        priority=priority,
                        path=skill_dir,
                        source=source_label("local", root, skill_dir, None),
                    )
                )

    commands_root = root / "commands"
    for agent in ["claude", "codex"]:
        agent_root = commands_root / agent
        if not agent_root.is_dir():
            continue
        for command_file in sorted(agent_root.glob("*.md")):
            candidates.append(
                Candidate(
                    kind="command",
                    agent=agent,
                    name=command_file.stem,
                    layer="local",
                    priority=priority,
                    path=command_file,
                    source=source_label("local", root, command_file, None),
                )
            )

    doc_root = root / "agent-docs"
    doc_map = [
        ("local.agents", ["agents", "codex"], doc_root / "AGENTS.md"),
        ("local.claude", ["claude"], doc_root / "CLAUDE.md"),
    ]
    for snippet_id, targets, path in doc_map:
        if path.exists():
            docs.append(
                DocSnippet(
                    snippet_id=snippet_id,
                    targets=targets,
                    layer="local",
                    priority=priority,
                    path=path,
                    source=source_label("local", root, path, None),
                )
            )

    return candidates, docs


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def replace_tree(src: Path, dest: Path) -> None:
    if dest.exists() or dest.is_symlink():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    if src.is_dir():
        shutil.copytree(src, dest, symlinks=True)
    else:
        ensure_parent(dest)
        shutil.copy2(src, dest)


def write_candidate(candidate: Candidate, dest: Path) -> None:
    if candidate.content is not None:
        if dest.suffix:
            ensure_parent(dest)
            dest.write_text(candidate.content.rstrip() + "\n", encoding="utf-8")
        else:
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "SKILL.md").write_text(candidate.content.rstrip() + "\n", encoding="utf-8")
        return
    if candidate.path is None:
        return
    replace_tree(candidate.path, dest)


def is_managed_target(path: Path, generated_root: Path, repo_roots: list[Path]) -> bool:
    if not path.exists() and not path.is_symlink():
        return True
    if not path.is_symlink():
        return False
    target = Path(os.readlink(path))
    if not target.is_absolute():
        target = (path.parent / target).resolve()
    try:
        target.resolve().relative_to(generated_root.resolve())
        return True
    except ValueError:
        pass
    for root in repo_roots:
        try:
            target.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            continue
    parts = set(target.parts)
    if ".agents" in parts and "skills" in parts:
        return True
    if target.name == "AGENTS.md" and ".codex" in parts:
        return True
    if target.name == "CLAUDE.md" and ".claude" in parts:
        return True
    if "commands" in parts and (".claude" in parts or ".codex" in parts):
        return True
    return False


def link_target(
    src: Path,
    target: Path,
    generated_root: Path,
    repo_roots: list[Path],
    dry_run: bool,
    report: list[str],
    allow_unmanaged_dry_run: bool = False,
) -> None:
    if not is_managed_target(target, generated_root, repo_roots):
        if dry_run and allow_unmanaged_dry_run:
            report.append(f"- would link `{target}` -> `{src}` after adopting existing local file")
            return
        report.append(f"- blocked managed link `{target}`; existing file is not managed by hv")
        return
    if dry_run:
        report.append(f"- would link `{target}` -> `{src}`")
        return
    ensure_parent(target)
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.symlink_to(src)


def resolve_candidates(candidates: list[Candidate]) -> dict[str, list[Candidate]]:
    by_key: dict[str, list[Candidate]] = {}
    for candidate in candidates:
        by_key.setdefault(candidate.key, []).append(candidate)
    for items in by_key.values():
        items.sort(key=lambda c: (c.priority, c.layer, c.source))
    return by_key


def selected_candidate(items: list[Candidate]) -> Candidate:
    return sorted(items, key=lambda c: (c.priority, c.layer, c.source))[-1]


def candidate_record(candidate: Candidate) -> dict[str, Any]:
    return {
        "kind": candidate.kind,
        "agent": candidate.agent,
        "name": candidate.name,
        "layer": candidate.layer,
        "priority": candidate.priority,
        "source": candidate.source,
        "sha256": candidate.digest(),
        "metadata": candidate.metadata,
    }


def parse_enabled_capabilities(value: str | None, defaults: list[str]) -> set[str]:
    enabled = {item.strip() for item in defaults if item.strip()}
    if value:
        enabled.update(item.strip() for item in value.split(",") if item.strip())
    return enabled


def validate_env(requirements: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    defaults = [
        req["capability"]
        for req in requirements
        if req.get("default_enabled") is True and req.get("capability")
    ]
    enabled = parse_enabled_capabilities(os.environ.get("HV_ENABLED_CAPABILITIES"), defaults)
    if "all" in enabled:
        enabled.update(req.get("capability", "") for req in requirements)

    checked: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for req in requirements:
        capability = req.get("capability")
        vars_required = list(req.get("vars", []))
        if not capability or capability not in enabled:
            continue
        absent = [name for name in vars_required if not os.environ.get(name)]
        record = {
            "capability": capability,
            "vars": vars_required,
            "missing": absent,
            "source": req.get("source"),
        }
        checked.append(record)
        if absent:
            missing.append(record)
    return checked, missing


def assemble_doc(target: str, snippets: list[DocSnippet]) -> str:
    title = "Global Agent Instructions" if target in {"agents", "codex"} else "Global Claude Instructions"
    lines = [
        f"# {title}",
        "",
        "<!-- Generated by hv-agent-resolver. Edit source layers or ~/.config/hv/overrides instead. -->",
        "",
    ]
    for snippet in sorted(snippets, key=lambda s: (s.priority, s.layer, s.snippet_id)):
        if not doc_target_matches(target, snippet.targets):
            continue
        lines.extend(
            [
                f"<!-- hv-section:{snippet.snippet_id} source:{snippet.source} layer:{snippet.layer} -->",
                snippet.read().rstrip(),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def doc_conflicts(content: str) -> list[str]:
    must: set[str] = set()
    must_not: set[str] = set()
    for line in content.splitlines():
        cleaned = line.strip().lower().strip("-* ")
        if "must not " in cleaned:
            must_not.add(cleaned.split("must not ", 1)[1])
        elif "must " in cleaned:
            must.add(cleaned.split("must ", 1)[1])
    return sorted(must.intersection(must_not))


def write_report(
    path: Path,
    layers: list[SourceLayer],
    resolved: dict[str, list[Candidate]],
    doc_outputs: dict[str, str],
    env_checked: list[dict[str, Any]],
    env_missing: list[dict[str, Any]],
    services: list[dict[str, Any]],
    link_report: list[str],
    dry_run: bool,
) -> None:
    lines = [
        "# HappyVertical Agent Install Report",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Mode: {'dry-run' if dry_run else 'install'}",
        "",
        "## Source Layers",
        "",
    ]
    for layer in layers:
        status = "available" if layer.available else "missing"
        lines.append(f"- `{layer.name}` priority {layer.priority}: {status} at `{layer.root}`")
        for note in layer.notes:
            lines.append(f"  - {note}")

    lines.extend(["", "## Resolved Commands And Skills", ""])
    for key in sorted(resolved):
        items = resolved[key]
        winner = selected_candidate(items)
        lines.append(f"- `{key}` -> `{winner.source}` ({winner.layer})")
        for item in items:
            if item is winner:
                continue
            lines.append(f"  - overrides `{item.source}` ({item.layer})")

    lines.extend(["", "## Agent Docs", ""])
    for target, content in doc_outputs.items():
        conflicts = doc_conflicts(content)
        lines.append(f"- `{target}` generated ({len(content.splitlines())} lines)")
        for conflict in conflicts:
            lines.append(f"  - potential must/must-not conflict: `{conflict}`")

    lines.extend(["", "## Environment Requirements", ""])
    if not env_checked:
        lines.append("- No enabled capabilities required env validation.")
    for item in env_checked:
        if item["missing"]:
            lines.append(f"- `{item['capability']}` missing: {', '.join(item['missing'])}")
        else:
            lines.append(f"- `{item['capability']}` satisfied.")

    lines.extend(["", "## Services", ""])
    if not services:
        lines.append("- No service registry entries found.")
    for service in services:
        cli = service.get("cli", {})
        status = cli.get("status", "documented")
        lines.append(f"- `{service.get('id')}` {service.get('url', '')} CLI: {status}")

    if link_report:
        lines.extend(["", "## Managed Links", ""])
        lines.extend(link_report)

    ensure_parent(path)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_lock(
    path: Path,
    layers: list[SourceLayer],
    resolved: dict[str, list[Candidate]],
    docs: list[DocSnippet],
    env_checked: list[dict[str, Any]],
    services: list[dict[str, Any]],
) -> None:
    data = {
        "schema": "https://happyvertical.com/hv-agent-lock/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "layers": [
            {
                "name": layer.name,
                "root": str(layer.root),
                "manifest": str(layer.manifest) if layer.manifest else None,
                "priority": layer.priority,
                "available": layer.available,
            }
            for layer in layers
        ],
        "definitions": [],
        "docs": [
            {
                "id": doc.snippet_id,
                "targets": doc.targets,
                "layer": doc.layer,
                "priority": doc.priority,
                "source": doc.source,
                "sha256": doc.digest(),
            }
            for doc in sorted(docs, key=lambda d: (d.priority, d.layer, d.snippet_id))
        ],
        "env": env_checked,
        "services": services,
    }
    for key in sorted(resolved):
        items = resolved[key]
        winner = selected_candidate(items)
        data["definitions"].append(
            {
                "key": key,
                "winner": candidate_record(winner),
                "candidates": [candidate_record(item) for item in items],
            }
        )
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def materialize(
    resolved: dict[str, list[Candidate]],
    doc_outputs: dict[str, str],
    output_dir: Path,
    home_dir: Path,
    repo_roots: list[Path],
    dry_run: bool,
) -> list[str]:
    report: list[str] = []
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for child in ["skills", "commands"]:
            target = output_dir / child
            if target.exists():
                shutil.rmtree(target)

    for key in sorted(resolved):
        winner = selected_candidate(resolved[key])
        if winner.kind == "skill":
            dest = output_dir / "skills" / winner.name
            if not dry_run:
                write_candidate(winner, dest)
            link_target(dest, home_dir / ".agents" / "skills" / winner.name, output_dir, repo_roots, dry_run, report)
        elif winner.kind == "command":
            suffix = ".md" if winner.path is None or winner.path.is_file() else ""
            dest = output_dir / "commands" / winner.agent / f"{winner.name}{suffix}"
            if not dry_run:
                write_candidate(winner, dest)
            if winner.agent == "claude":
                link_target(dest, home_dir / ".claude" / "commands" / f"{winner.name}.md", output_dir, repo_roots, dry_run, report)
            elif winner.agent == "codex":
                link_target(dest, home_dir / ".codex" / "commands" / f"{winner.name}.md", output_dir, repo_roots, dry_run, report)

    for target, content in doc_outputs.items():
        filename = TARGETS[target]
        dest = output_dir / "docs" / target / filename
        if not dry_run:
            ensure_parent(dest)
            dest.write_text(content, encoding="utf-8")
        if target in {"agents", "codex"}:
            link_target(
                dest,
                home_dir / ".codex" / "AGENTS.md",
                output_dir,
                repo_roots,
                dry_run,
                report,
                allow_unmanaged_dry_run=True,
            )
        if target == "claude":
            link_target(
                dest,
                home_dir / ".claude" / "CLAUDE.md",
                output_dir,
                repo_roots,
                dry_run,
                report,
                allow_unmanaged_dry_run=True,
            )
    return report


def ensure_local_override_templates(local_dir: Path, dry_run: bool) -> list[str]:
    report: list[str] = []
    directories = [
        local_dir / "skills",
        local_dir / "skills" / "codex",
        local_dir / "skills" / "claude",
        local_dir / "commands" / "claude",
        local_dir / "commands" / "codex",
        local_dir / "agent-docs",
    ]
    readme = local_dir / "README.md"

    if dry_run:
        report.append(f"- would ensure local override directories under `{local_dir}`")
        return report

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    if not readme.exists():
        readme.write_text(
            "\n".join(
                [
                    "# HappyVertical Local Overrides",
                    "",
                    "Files in this directory are machine-local and are never overwritten by",
                    "the have-config installer.",
                    "",
                    "- `skills/<name>/SKILL.md` overrides Codex skills.",
                    "- `commands/claude/<name>.md` overrides Claude commands.",
                    "- `commands/codex/<name>.md` overrides Codex commands.",
                    "- `agent-docs/AGENTS.md` and `agent-docs/CLAUDE.md` are appended",
                    "  to generated global instructions.",
                    "",
                    "Local overrides win over Context Forge snapshots, profile defaults,",
                    "have-config, and dotfiles. Keep them intentional and review the install report after",
                    "each update.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    return report


def adopt_existing_agent_docs(
    home_dir: Path,
    local_dir: Path,
    generated_root: Path,
    repo_roots: list[Path],
    dry_run: bool,
) -> list[str]:
    report: list[str] = []
    doc_targets = [
        (home_dir / ".codex" / "AGENTS.md", local_dir / "agent-docs" / "AGENTS.md"),
        (home_dir / ".claude" / "CLAUDE.md", local_dir / "agent-docs" / "CLAUDE.md"),
    ]

    for target, override_path in doc_targets:
        if not target.exists() and not target.is_symlink():
            continue
        if is_managed_target(target, generated_root, repo_roots):
            continue
        if override_path.exists():
            report.append(
                f"- blocked adoption of `{target}`; local override already exists at `{override_path}`"
            )
            continue
        if dry_run:
            report.append(f"- would adopt existing `{target}` into `{override_path}`")
            continue
        ensure_parent(override_path)
        shutil.move(str(target), str(override_path))
        report.append(f"- adopted existing `{target}` into `{override_path}`")

    return report


def ensure_hermes_home(hermes_dir: Path, active_profiles: list[str], dry_run: bool) -> list[str]:
    report: list[str] = []
    if "hermes" not in active_profiles:
        return report

    if dry_run:
        report.append(f"- would ensure Hermes profile directories under `{hermes_dir}`")
        return report

    for directory in [hermes_dir, hermes_dir / "overrides", hermes_dir / "generated"]:
        directory.mkdir(parents=True, exist_ok=True)

    profile_path = hermes_dir / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile": "hermes",
                "managed_by": "have-config",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "local_overrides": str(hermes_dir / "overrides"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    home_default = Path("~").expanduser().resolve()
    detected_profiles, detection_notes = detect_profiles(home_default)
    active_profiles_default = ",".join(detected_profiles)
    hermes_active = "hermes" in detected_profiles
    hv_config_dir = os.environ.get("HV_CONFIG_DIR", "~/.hermes" if hermes_active else "~/.config/hv")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotfiles-dir", default=os.environ.get("DOTFILES_DIR", "~/Work/willgriffin/repos/dotfiles"))
    parser.add_argument("--have-config-dir", default=os.environ.get("HAVE_CONFIG_DIR", os.getcwd()))
    parser.add_argument("--profiles", default=os.environ.get("HV_AGENT_PROFILE", active_profiles_default))
    parser.add_argument("--contextforge-dir", default=os.environ.get("HV_CONTEXTFORGE_SNAPSHOT_DIR", f"{hv_config_dir}/contextforge"))
    parser.add_argument("--local-overrides-dir", default=os.environ.get("HV_LOCAL_OVERRIDES_DIR", f"{hv_config_dir}/overrides"))
    parser.add_argument("--output-dir", default=os.environ.get("HV_GENERATED_DIR", f"{hv_config_dir}/generated"))
    parser.add_argument("--home-dir", default="~")
    parser.add_argument("--lock-path", default=os.environ.get("HV_AGENT_LOCK", f"{hv_config_dir}/agent-lock.json"))
    parser.add_argument("--report-path", default=os.environ.get("HV_INSTALL_REPORT", f"{hv_config_dir}/install-report.md"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dotfiles = Path(args.dotfiles_dir).expanduser().resolve()
    have_config = Path(args.have_config_dir).expanduser().resolve()
    active_profiles = split_profiles(args.profiles)
    contextforge = Path(args.contextforge_dir).expanduser().resolve()
    local = Path(args.local_overrides_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    home_dir = Path(args.home_dir).expanduser().resolve()
    lock_path = Path(args.lock_path).expanduser().resolve()
    report_path = Path(args.report_path).expanduser().resolve()

    hermes_dir = Path(os.environ.get("HERMES_HOME", str(home_dir / ".hermes"))).expanduser().resolve()
    repo_roots = [dotfiles, have_config, hermes_dir]

    link_report = ensure_local_override_templates(local, args.dry_run)
    link_report.extend(ensure_hermes_home(hermes_dir, active_profiles, args.dry_run))
    link_report.extend(adopt_existing_agent_docs(home_dir, local, output_dir, repo_roots, args.dry_run))

    layers = [
        manifest_layer("dotfiles", dotfiles, "agent/manifest.json", LAYER_PRIORITIES["dotfiles"]),
        manifest_layer("have-config", have_config, "hv/manifest.json", LAYER_PRIORITIES["have-config"]),
    ]
    for profile in active_profiles:
        profile_root = have_config / "profiles" / profile
        layer = manifest_layer(f"profile:{profile}", profile_root, "manifest.json", LAYER_PRIORITIES["profile"])
        if profile in detected_profiles:
            layer.notes.extend(detection_notes)
        layers.append(layer)
    if not active_profiles:
        layers.append(SourceLayer("profile", have_config / "profiles", None, LAYER_PRIORITIES["profile"], False, detection_notes))
    layers.extend(
        [
            manifest_layer("contextforge", contextforge, "manifest.json", LAYER_PRIORITIES["contextforge"]),
            manifest_layer("local", local, "manifest.json", LAYER_PRIORITIES["local"]),
        ]
    )

    candidates: list[Candidate] = []
    docs: list[DocSnippet] = []
    env_requirements: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []

    for layer in layers:
        layer_candidates, layer_docs, layer_env, layer_services = collect_manifest(layer)
        candidates.extend(layer_candidates)
        docs.extend(layer_docs)
        env_requirements.extend({**item, "source": layer.name} for item in layer_env)
        services.extend({**item, "source": layer.name} for item in layer_services)

    local_candidates, local_docs = collect_local_conventions(local, LAYER_PRIORITIES["local"])
    candidates.extend(local_candidates)
    docs.extend(local_docs)

    resolved = resolve_candidates(candidates)
    env_checked, env_missing = validate_env(env_requirements)
    doc_outputs = {
        target: assemble_doc(target, docs)
        for target in ["agents", "claude"]
        if any(doc_target_matches(target, snippet.targets) for snippet in docs)
    }

    link_report.extend(materialize(resolved, doc_outputs, output_dir, home_dir, repo_roots, args.dry_run))

    if not args.dry_run:
        write_lock(lock_path, layers, resolved, docs, env_checked, services)
    write_report(report_path, layers, resolved, doc_outputs, env_checked, env_missing, services, link_report, args.dry_run)

    print(f"HappyVertical agent report: {report_path}")
    if not args.dry_run:
        print(f"HappyVertical agent lock: {lock_path}")

    if env_missing:
        print("Missing required environment variables for enabled capabilities:", file=sys.stderr)
        for item in env_missing:
            print(f"  {item['capability']}: {', '.join(item['missing'])}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
