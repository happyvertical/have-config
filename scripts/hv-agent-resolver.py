#!/usr/bin/env python3
"""Resolve HappyVertical agent definitions into local generated files.

The resolver composes these layers:

1. dotfiles baseline workflows
2. have-config organization standard
3. optional profile defaults, such as Hermes
4. Context Forge install-time snapshot
5. machine-local overrides

Commands, skills, and reusable scripts use winner-takes-all resolution by layer
priority. Agent documents are cumulative and assembled in layer order.
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

CONTRACT_SECRET_KEYWORDS = (
    "api_key",
    "apikey",
    "client_secret",
    "cookie",
    "password",
    "private_key",
    "recovery_code",
    "secret",
    "token",
)


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def first_env_value(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


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
        if declared_priority is not None:
            try:
                declared_priority_int = int(declared_priority)
                if isinstance(declared_priority, bool):
                    raise ValueError
            except (TypeError, ValueError):
                notes.append(
                    f"invalid declared priority {declared_priority!r} ignored; using fixed {default_priority}"
                )
            else:
                if declared_priority_int != default_priority:
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

    for item in data.get("scripts", []):
        path = resolve_path(root, item.get("path"))
        content = item.get("content")
        name = item["name"]
        candidates.append(
            Candidate(
                kind="script",
                agent=item.get("agent", "no-agent"),
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


def collect_service_registry(root: Path) -> list[dict[str, Any]]:
    registry = root / "services" / "services.json"
    if not registry.exists():
        return []
    data = load_json(registry)
    return [{**service, "source": "services/services.json"} for service in data.get("services", [])]


def selected_contract_slug() -> str:
    return first_env_value(
        "HV_AGENT_CONTRACT",
        "HV_AGENT_CONTRACT_SLUG",
        "HV_AGENT_SLUG",
        "HERMES_AGENT_ID",
    )


def contract_candidates(
    slug: str,
    active_profiles: list[str],
    have_config: Path,
    contextforge: Path,
    local: Path,
) -> list[tuple[str, Path]]:
    names = [f"{slug}.json"]
    candidates: list[tuple[str, Path]] = []
    candidates.append(("local", local / "contracts" / names[0]))
    candidates.append(("contextforge", contextforge / "contracts" / names[0]))
    for profile in active_profiles:
        candidates.append(
            (
                f"profile:{profile}",
                have_config / "profiles" / profile / "contracts" / names[0],
            )
        )
    candidates.append(("have-config", have_config / "contracts" / names[0]))
    return candidates


def find_agent_contract(
    active_profiles: list[str],
    have_config: Path,
    contextforge: Path,
    local: Path,
) -> tuple[dict[str, Any] | None, str | None, str | None, list[str]]:
    explicit_path = first_env_value("HV_AGENT_CONTRACT_PATH")
    notes: list[str] = []
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        if not path.exists():
            raise ValueError(f"HV_AGENT_CONTRACT_PATH does not exist: {path}")
        data = load_json(path)
        validate_agent_contract(data, str(path))
        return data, str(path), data.get("slug"), notes

    slug = selected_contract_slug()
    if not slug:
        return None, None, None, notes

    for layer, path in contract_candidates(slug, active_profiles, have_config, contextforge, local):
        if path.exists():
            data = load_json(path)
            validate_agent_contract(data, f"{layer}:{path}")
            if data.get("slug") != slug:
                raise ValueError(
                    f"agent contract slug mismatch: selected {slug!r}, file has {data.get('slug')!r}"
                )
            return data, f"{layer}:{path}", slug, notes

    searched = ", ".join(str(path) for _, path in contract_candidates(slug, active_profiles, have_config, contextforge, local))
    raise ValueError(f"agent contract {slug!r} not found; searched {searched}")


def validate_agent_contract(data: dict[str, Any], source: str) -> None:
    required_top = ["slug", "kind", "identity", "role", "permissions", "services", "runtime"]
    missing_top = [key for key in required_top if key not in data]
    if missing_top:
        raise ValueError(f"{source} missing required contract keys: {', '.join(missing_top)}")

    if not isinstance(data.get("slug"), str) or not data["slug"].strip():
        raise ValueError(f"{source} contract slug must be a non-empty string")
    if not isinstance(data.get("kind"), str) or not data["kind"].strip():
        raise ValueError(f"{source} contract kind must be a non-empty string")

    identity = data.get("identity")
    if not isinstance(identity, dict):
        raise ValueError(f"{source} identity must be an object")
    for key in ["email", "idp_account"]:
        if not isinstance(identity.get(key), str) or not identity[key].strip():
            raise ValueError(f"{source} identity.{key} must be a non-empty string")

    role = data.get("role")
    if not isinstance(role, dict):
        raise ValueError(f"{source} role must be an object")
    if not isinstance(role.get("primary_repo"), str) or not role["primary_repo"].strip():
        raise ValueError(f"{source} role.primary_repo must be a non-empty string")
    if role.get("project_leader") is not True:
        raise ValueError(f"{source} role.project_leader must be true for project Hermes contracts")

    project_lead = data.get("project_lead")
    if not isinstance(project_lead, dict):
        raise ValueError(f"{source} project_lead must be an object")
    vikunja = project_lead.get("vikunja")
    if not isinstance(vikunja, dict):
        raise ValueError(f"{source} project_lead.vikunja must be an object")
    for key in ["url", "project", "board"]:
        if not isinstance(vikunja.get(key), str) or not vikunja[key].strip():
            raise ValueError(f"{source} project_lead.vikunja.{key} must be a non-empty string")
    buckets = vikunja.get("buckets")
    if not isinstance(buckets, list) or not all(isinstance(item, str) and item.strip() for item in buckets):
        raise ValueError(f"{source} project_lead.vikunja.buckets must be a non-empty string list")

    permissions = data.get("permissions")
    if not isinstance(permissions, dict):
        raise ValueError(f"{source} permissions must be an object")
    if not isinstance(permissions.get("github"), dict):
        raise ValueError(f"{source} permissions.github must be an object")

    services = data.get("services")
    if not isinstance(services, dict):
        raise ValueError(f"{source} services must be an object")
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError(f"{source} runtime must be an object")
    if not isinstance(runtime.get("hindsight_bank"), str) or not runtime["hindsight_bank"].strip():
        raise ValueError(f"{source} runtime.hindsight_bank must be a non-empty string")

    secret_paths = find_secret_values(data)
    if secret_paths:
        raise ValueError(
            f"{source} appears to contain secret material at: {', '.join(secret_paths)}. "
            "Use Warden/SOPS references, not secret values."
        )


def find_secret_values(value: Any, path: str = "") -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            key_l = str(key).lower()
            if any(keyword in key_l for keyword in CONTRACT_SECRET_KEYWORDS):
                if isinstance(child, str) and child.strip() and not is_reference_value(child):
                    matches.append(child_path)
            matches.extend(find_secret_values(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            matches.extend(find_secret_values(child, f"{path}[{idx}]"))
    return matches


def is_reference_value(value: str) -> bool:
    allowed_prefixes = (
        "env:",
        "file:",
        "kubernetes:",
        "sops:",
        "secret:",
        "vault:",
        "warden:",
    )
    if value.startswith(allowed_prefixes) or "*" in value or value.endswith("_TOKEN"):
        return True
    return (
        value.startswith("hermes-")
        or value.endswith(".secret.enc.yaml")
        or value.endswith(".secret.template.yaml")
    )


def list_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def contract_display_name(identity: dict[str, Any]) -> str:
    explicit = str(identity.get("display_name", "")).strip()
    if explicit:
        return explicit
    email = str(identity.get("email", "")).strip()
    if "@" in email:
        return email.split("@", 1)[0]
    return email


def render_agent_project_brief(contract: dict[str, Any], source: str | None) -> str:
    identity = contract.get("identity", {})
    role = contract.get("role", {})
    permissions = contract.get("permissions", {})
    project_lead = contract.get("project_lead", {})
    vikunja = project_lead.get("vikunja", {})
    delegation = project_lead.get("delegation", {})
    services = contract.get("services", {})
    runtime = contract.get("runtime", {})

    lines = [
        f"# Hermes Project Brief: {contract['slug']}",
        "",
        f"- Contract source: `{source or 'unknown'}`",
        f"- Identity: `{identity.get('email', '')}` (`{identity.get('idp_account', '')}`)",
        f"- Display name: {contract_display_name(identity)}",
        f"- Kind: `{contract.get('kind', '')}`",
        f"- Primary role: project leader for `{role.get('primary_repo', '')}`",
        f"- Hindsight bank: `{runtime.get('hindsight_bank', '')}`",
        "",
        "## Repository Context",
        "",
        f"- Primary repo: `{role.get('primary_repo', '')}`",
    ]
    related = list_strings(role.get("related_repos"))
    if related:
        lines.extend(f"- Related repo: `{repo}`" for repo in related)
    orientation = list_strings(role.get("orientation"))
    if orientation:
        lines.extend(["", "## Orientation", ""])
        lines.extend(f"- {item}" for item in orientation)

    lines.extend(
        [
            "",
            "## Project Board",
            "",
            f"- Vikunja URL: `{vikunja.get('url', '')}`",
            f"- Project: `{vikunja.get('project', '')}`",
            f"- Board: `{vikunja.get('board', '')}`",
        ]
    )
    buckets = list_strings(vikunja.get("buckets"))
    if buckets:
        lines.append(f"- Buckets: {', '.join(f'`{bucket}`' for bucket in buckets)}")
    labels = list_strings(vikunja.get("labels"))
    if labels:
        lines.append(f"- Labels: {', '.join(f'`{label}`' for label in labels)}")
    done_criteria = list_strings(vikunja.get("done_criteria"))
    if done_criteria:
        lines.extend(["", "Done means:"])
        lines.extend(f"- {item}" for item in done_criteria)

    use_subagents = list_strings(delegation.get("use_subagents_for"))
    if use_subagents:
        lines.extend(["", "## Delegation", ""])
        lines.extend(f"- Use sub-agents/sessions for `{item}`." for item in use_subagents)
    if delegation.get("worker_record_required") is True:
        lines.append("- Every delegated worker run needs a linked Vikunja worker task or comment trail.")

    lines.extend(["", "## Permission Summary", ""])
    github = permissions.get("github", {})
    if isinstance(github, dict):
        for repo, level in sorted(github.items()):
            lines.append(f"- GitHub `{repo}`: `{level}`")
    kubernetes = permissions.get("kubernetes", {})
    if isinstance(kubernetes, dict):
        namespaces = list_strings(kubernetes.get("namespaces"))
        if namespaces:
            lines.append(f"- Kubernetes namespaces: {', '.join(f'`{namespace}`' for namespace in namespaces)}")
        if kubernetes.get("service_account"):
            lines.append(f"- Kubernetes service account: `{kubernetes['service_account']}`")
    sops_profiles = list_strings(permissions.get("sops_profiles"))
    if sops_profiles:
        lines.append(f"- SOPS profiles: {', '.join(f'`{profile}`' for profile in sops_profiles)}")
    warden_paths = list_strings(permissions.get("warden_paths"))
    if warden_paths:
        lines.append(f"- Warden paths: {', '.join(f'`{path}`' for path in warden_paths)}")

    lines.extend(["", "## Service Expectations", ""])
    for name, state in sorted(services.items()):
        lines.append(f"- `{name}`: `{state}`")

    lines.extend(
        [
            "",
            "## Operating Rules",
            "",
            "- Track substantial development work on Vikunja before starting implementation.",
            "- Keep Vikunja comments current for pickup, blockers, PRs, CI, deploy, and completion.",
            "- Use Warden/SOPS references for credentials; never print or store decrypted secret values in task comments, reports, or PRs.",
            "- Check have-config drift during setup and after policy changes; rematerialize local generated files when stale.",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def dedupe_services(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keyed: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    for service in services:
        service_id = service.get("id")
        if service_id:
            keyed[service_id] = service
        else:
            anonymous.append(service)
    return [keyed[key] for key in sorted(keyed)] + anonymous


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


def write_script_candidate(candidate: Candidate, dest: Path) -> None:
    """Write a script candidate as a file, including inline content."""
    if candidate.content is not None:
        ensure_parent(dest)
        dest.write_text(candidate.content.rstrip() + "\n", encoding="utf-8")
        return
    write_candidate(candidate, dest)


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
    is_local_bin_link = path.parent.name == "bin" and path.parent.parent.name == ".local"
    if is_local_bin_link:
        return False
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
    agent_contract: dict[str, Any] | None,
    agent_contract_source: str | None,
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

    lines.extend(["", "## Resolved Commands, Skills, And Scripts", ""])
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
        source = service.get("source", "unknown")
        url = service.get("url") or ""
        lines.append(f"- `{service.get('id')}` {url} CLI: {status} (source: {source})")

    lines.extend(["", "## Agent Contract", ""])
    if agent_contract:
        identity = agent_contract.get("identity", {})
        role = agent_contract.get("role", {})
        runtime = agent_contract.get("runtime", {})
        lines.append(f"- Contract: `{agent_contract.get('slug')}` from `{agent_contract_source}`")
        lines.append(f"- Identity: `{identity.get('email')}`")
        lines.append(f"- Primary repo: `{role.get('primary_repo')}`")
        lines.append(f"- Hindsight bank: `{runtime.get('hindsight_bank')}`")
    else:
        lines.append("- No agent contract selected.")

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
    agent_contract: dict[str, Any] | None,
    agent_contract_source: str | None,
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
        "agent_contract": None,
    }
    if agent_contract:
        data["agent_contract"] = {
            "slug": agent_contract.get("slug"),
            "kind": agent_contract.get("kind"),
            "source": agent_contract_source,
            "sha256": sha256_text(json.dumps(agent_contract, sort_keys=True)),
            "identity_email": (agent_contract.get("identity") or {}).get("email"),
            "primary_repo": (agent_contract.get("role") or {}).get("primary_repo"),
            "hindsight_bank": (agent_contract.get("runtime") or {}).get("hindsight_bank"),
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
    agent_contract: dict[str, Any] | None,
    agent_contract_source: str | None,
    output_dir: Path,
    home_dir: Path,
    repo_roots: list[Path],
    dry_run: bool,
) -> list[str]:
    report: list[str] = []
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        for child in ["skills", "commands", "scripts", "contracts"]:
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
        elif winner.kind == "script":
            dest = output_dir / "scripts" / winner.name
            if not dry_run:
                write_script_candidate(winner, dest)
                if winner.metadata.get("executable") is True:
                    dest.chmod(dest.stat().st_mode | 0o111)
            if winner.metadata.get("executable") is True:
                link_target(dest, home_dir / ".local" / "bin" / winner.name, output_dir, repo_roots, dry_run, report)

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
    if agent_contract:
        slug = str(agent_contract["slug"])
        contract_dest = output_dir / "contracts" / f"{slug}.json"
        brief_dest = output_dir / "docs" / "hermes" / "project-brief.md"
        home_contract = home_dir / "agent-contract.json"
        home_brief = home_dir / "project-brief.md"
        brief = render_agent_project_brief(agent_contract, agent_contract_source)
        if dry_run:
            report.append(f"- would materialize agent contract `{slug}` from `{agent_contract_source}`")
            report.append(f"- would write Hermes project brief to `{home_brief}`")
        else:
            write_json(contract_dest, agent_contract)
            ensure_parent(brief_dest)
            brief_dest.write_text(brief, encoding="utf-8")
        link_target(contract_dest, home_contract, output_dir, repo_roots, dry_run, report)
        link_target(brief_dest, home_brief, output_dir, repo_roots, dry_run, report)
    elif not dry_run:
        for stale_target in [home_dir / "agent-contract.json", home_dir / "project-brief.md"]:
            if is_managed_target(stale_target, output_dir, repo_roots) and (
                stale_target.exists() or stale_target.is_symlink()
            ):
                stale_target.unlink()
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
                    "- `skills/codex/<name>/SKILL.md` overrides Codex skills.",
                    "- `skills/claude/<name>/SKILL.md` overrides Claude skills when supported.",
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
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--profiles", default=os.environ.get("HV_AGENT_PROFILE", active_profiles_default))
    pre_args, _ = pre_parser.parse_known_args()
    default_profiles = split_profiles(pre_args.profiles)
    hermes_active = "hermes" in default_profiles
    hv_config_dir = os.environ.get(
        "HV_CONFIG_DIR",
        os.environ.get("HERMES_HOME", "~/.hermes") if hermes_active else "~/.config/hv",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotfiles-dir", default=os.environ.get("DOTFILES_DIR", f"{hv_config_dir}/dotfiles"))
    parser.add_argument("--have-config-dir", default=os.environ.get("HAVE_CONFIG_DIR", os.getcwd()))
    parser.add_argument("--profiles", default=pre_args.profiles)
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
    services.extend(collect_service_registry(have_config))
    services = dedupe_services(services)

    local_candidates, local_docs = collect_local_conventions(local, LAYER_PRIORITIES["local"])
    candidates.extend(local_candidates)
    docs.extend(local_docs)

    agent_contract, agent_contract_source, _, _ = find_agent_contract(
        active_profiles,
        have_config,
        contextforge,
        local,
    )

    resolved = resolve_candidates(candidates)
    env_checked, env_missing = validate_env(env_requirements)
    doc_outputs = {
        target: assemble_doc(target, docs)
        for target in ["agents", "claude"]
        if any(doc_target_matches(target, snippet.targets) for snippet in docs)
    }

    link_report.extend(
        materialize(
            resolved,
            doc_outputs,
            agent_contract,
            agent_contract_source,
            output_dir,
            home_dir,
            repo_roots,
            args.dry_run,
        )
    )

    if not args.dry_run:
        write_lock(lock_path, layers, resolved, docs, env_checked, services, agent_contract, agent_contract_source)
    write_report(
        report_path,
        layers,
        resolved,
        doc_outputs,
        env_checked,
        env_missing,
        services,
        agent_contract,
        agent_contract_source,
        link_report,
        args.dry_run,
    )

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
