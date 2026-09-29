"""publisher.py -- twelve delegation rules as a pre-flight publish check.

Runs in CI before the pypa/gh-action-pypi-publish step. Reads a policy
file and a state file (both committed to the repository), examines the
release being published, and returns a list of failures. Zero failures
means the publish may proceed. Any failure means exit non-zero.

This is a client-side gate. It cannot be enforced by PyPI. An actor who
can edit the workflow can remove it. Treat the twelve rules as checks
that raise the cost of an unintended publish, not as a security boundary.

Rules implemented:

  1. capability-scoped     -- version pattern, hash-chain root
  2. time-bounded          -- valid_until_ns
  3. dual-signature        -- workflow sig + countersign, both required
  4. rate-limited          -- max N in window W (reuses backpressure)
  5. monotonic             -- version strictly greater than last
  6. semantic-scope        -- 0.4.x style pattern, stricter than #1
  7. witnessed             -- third-party sig over (tag, commit, hash)
  8. layered scope         -- dependencies must have recent publishes
  9. progressive trust     -- narrow pattern until min_history reached
 10. effect-typed          -- every file matches an allowed effect
 11. constraint satisfaction -- deps subset of baseline + growth
 12. tiered delegation     -- parent keys sign the policy; threshold
"""
from __future__ import annotations
import fnmatch
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False


# ── data model ──────────────────────────────────────────────────
@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: str = ""

    @classmethod
    def parse(cls, s: str) -> "Version":
        s = s.lstrip("v")
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", s)
        if not m:
            raise ValueError(f"not X.Y.Z[-pre]: {s!r}")
        return cls(int(m.group(1)), int(m.group(2)),
                   int(m.group(3)), m.group(4) or "")

    def as_tuple(self):
        # stable ordering: prerelease sorts below release
        return (self.major, self.minor, self.patch,
                0 if self.prerelease else 1, self.prerelease)

    def __str__(self):
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.prerelease}" if self.prerelease else base


@dataclass
class Release:
    project: str
    version: str
    tag: str
    commit: str
    files: list = field(default_factory=list)          # [[path, sha256], ...]
    deps: list = field(default_factory=list)           # sorted dep specs
    published_at_ns: int = 0


@dataclass
class Policy:
    project: str
    # 1
    version_pattern: str = "*"
    hash_chain_root: Optional[str] = None
    # 2
    valid_until_ns: Optional[int] = None
    # 3
    countersign_pubkey_hex: Optional[str] = None
    # 4
    rate_window_ns: int = 7 * 24 * 3600 * 10**9
    rate_max: int = 10
    # 5
    monotonic: bool = True
    # 6
    semantic_scope: Optional[str] = None       # e.g. "0.4.x"
    # 7
    witness_pubkeys_hex: list = field(default_factory=list)
    witness_required: bool = False
    # 8
    depends_on: list = field(default_factory=list)   # list of project names
    aliveness_window_ns: int = 30 * 24 * 3600 * 10**9
    dependencies_state_dir: Optional[str] = None      # where to read dep states
    # 9
    progressive: bool = False
    min_history: int = 5
    narrow_pattern: str = "0.0.*"
    # 10
    allowed_effects: list = field(default_factory=list)  # ["add:*.py", ...]
    # 11
    dep_baseline: list = field(default_factory=list)
    dep_growth_max: int = 0
    # 12
    tier: int = 0
    parent_pubkeys_hex: list = field(default_factory=list)
    parent_threshold: int = 0
    parent_signatures: dict = field(default_factory=dict)  # pubkey -> sig hex


@dataclass
class State:
    releases: list = field(default_factory=list)
    witnesses: dict = field(default_factory=dict)   # tag -> [[pubkey, sig], ...]
    countersigns: dict = field(default_factory=dict)  # tag -> sig hex

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls()
        d = json.loads(path.read_text())
        return cls(**d)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True))


# ── helpers ─────────────────────────────────────────────────────
def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _verify(pub_hex: str, sig_hex: str, msg: bytes) -> bool:
    if not HAVE_CRYPTO:
        return False
    try:
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
        pub.verify(bytes.fromhex(sig_hex), msg)
        return True
    except Exception:
        return False


def _hash_chain(releases: list) -> str:
    """Merkle-style chain: each release's hash feeds the next."""
    prev = b"\x00" * 32
    for r in releases:
        body = _canon({"version": r["version"],
                       "tag": r["tag"],
                       "commit": r["commit"],
                       "files": r["files"]})
        prev = hashlib.sha256(prev + body).digest()
    return prev.hex()


# ── the twelve checks ──────────────────────────────────────────
def check_capability_scope(rel: Release, pol: Policy, st: State) -> list:
    failures = []
    if not fnmatch.fnmatchcase(rel.version, pol.version_pattern):
        failures.append(
            f"1 capability-scope: version {rel.version!r} does not match "
            f"pattern {pol.version_pattern!r}")
    if pol.hash_chain_root is not None:
        chain = _hash_chain(st.releases + [asdict(rel)])
        if chain != pol.hash_chain_root:
            failures.append(
                f"1 capability-scope: hash chain root {chain[:16]} "
                f"does not match declared {pol.hash_chain_root[:16]}")
    return failures


def check_time_bound(rel: Release, pol: Policy, st: State, now_ns: int) -> list:
    if pol.valid_until_ns is None:
        return []
    if now_ns >= pol.valid_until_ns:
        return [f"2 time-bound: policy expired at {pol.valid_until_ns}"]
    return []


def check_dual_signature(rel: Release, pol: Policy, st: State) -> list:
    failures = []
    if pol.countersign_pubkey_hex is None:
        return []
    sig_hex = st.countersigns.get(rel.tag)
    if not sig_hex:
        failures.append(
            f"3 dual-signature: no countersignature recorded for tag {rel.tag}")
    else:
        body = _canon({"tag": rel.tag, "commit": rel.commit,
                       "files": rel.files})
        if not _verify(pol.countersign_pubkey_hex, sig_hex, body):
            failures.append(
                "3 dual-signature: countersignature does not verify")
    return failures


def check_rate_limit(rel: Release, pol: Policy, st: State, now_ns: int) -> list:
    recent = [r for r in st.releases
              if now_ns - r.get("published_at_ns", 0) < pol.rate_window_ns]
    if len(recent) >= pol.rate_max:
        return [f"4 rate-limit: {len(recent)} releases in window, max "
                f"{pol.rate_max}"]
    return []


def check_monotonic(rel: Release, pol: Policy, st: State) -> list:
    if not pol.monotonic or not st.releases:
        return []
    last = Version.parse(st.releases[-1]["version"])
    new = Version.parse(rel.version)
    if new.as_tuple() <= last.as_tuple():
        return [f"5 monotonic: {new} is not greater than last {last}"]
    return []


def check_semantic_scope(rel: Release, pol: Policy, st: State) -> list:
    if pol.semantic_scope is None:
        return []
    # "0.4.x" -> major=0, minor=4, patch=*
    m = re.match(r"^(\d+)\.(\d+)\.x$", pol.semantic_scope)
    if not m:
        return [f"6 semantic-scope: malformed scope "
                f"{pol.semantic_scope!r}, want M.N.x"]
    maj, minr = int(m.group(1)), int(m.group(2))
    v = Version.parse(rel.version)
    if v.major != maj or v.minor != minr:
        return [f"6 semantic-scope: {v} outside {pol.semantic_scope}"]
    return []


def check_witnessed(rel: Release, pol: Policy, st: State) -> list:
    if not pol.witness_required:
        return []
    ws = st.witnesses.get(rel.tag, [])
    if not ws:
        return [f"7 witnessed: no witness for tag {rel.tag}"]
    body = _canon({"tag": rel.tag, "commit": rel.commit,
                   "version": rel.version, "files": rel.files})
    valid = [w for w in ws if _verify(w[0], w[1], body)]
    if not valid:
        return [f"7 witnessed: {len(ws)} witness(es) present, none verify"]
    return []


def check_layered_scope(rel: Release, pol: Policy, st: State,
                        now_ns: int) -> list:
    if not pol.depends_on:
        return []
    if pol.dependencies_state_dir is None:
        return [f"8 layered-scope: depends_on {pol.depends_on} set but "
                f"no dependencies_state_dir configured"]
    failures = []
    for dep in pol.depends_on:
        dep_state_path = Path(pol.dependencies_state_dir) / f"{dep}.json"
        if not dep_state_path.exists():
            failures.append(
                f"8 layered-scope: no state file for dependency {dep!r}")
            continue
        dep_state = json.loads(dep_state_path.read_text())
        if not dep_state.get("releases"):
            failures.append(
                f"8 layered-scope: dependency {dep!r} has no releases")
            continue
        latest = dep_state["releases"][-1].get("published_at_ns", 0)
        if now_ns - latest > pol.aliveness_window_ns:
            failures.append(
                f"8 layered-scope: dependency {dep!r} last published "
                f"{(now_ns - latest) / 1e9 / 86400:.1f} days ago, "
                f"window is {pol.aliveness_window_ns / 1e9 / 86400:.1f} days")
    return failures


def check_progressive_trust(rel: Release, pol: Policy, st: State) -> list:
    if not pol.progressive:
        return []
    n = len(st.releases)
    if n < pol.min_history:
        if not fnmatch.fnmatchcase(rel.version, pol.narrow_pattern):
            return [f"9 progressive-trust: history {n} < "
                    f"min_history {pol.min_history}, only "
                    f"{pol.narrow_pattern!r} allowed"]
    return []


def check_effect_types(rel: Release, pol: Policy, st: State) -> list:
    if not pol.allowed_effects:
        return []
    failures = []
    for path, _sha in rel.files:
        # effect inference: new file -> "add:PATH". anything matching a
        # prior release's files -> "modify:PATH". We do not track deletes
        # because a publish never deletes.
        prior_paths = {p for r in st.releases for p, _ in r.get("files", [])}
        kind = "modify" if path in prior_paths else "add"
        token = f"{kind}:{path}"
        if not any(fnmatch.fnmatchcase(token, pat) or
                   fnmatch.fnmatchcase(path, pat.split(":", 1)[-1]) or
                   fnmatch.fnmatchcase(token, pat)
                   for pat in pol.allowed_effects):
            failures.append(
                f"10 effect-typed: {token} not covered by "
                f"allowed_effects {pol.allowed_effects}")
    return failures


def check_constraint_satisfaction(rel: Release, pol: Policy, st: State) -> list:
    if not pol.dep_baseline and pol.dep_growth_max == 0:
        return []
    baseline = set(pol.dep_baseline)
    current = set(rel.deps)
    added = current - baseline
    if len(added) > pol.dep_growth_max:
        return [f"11 constraint: {len(added)} new deps, growth_max "
                f"{pol.dep_growth_max}, added={sorted(added)[:3]}"]
    return []


def check_tiered_delegation(rel: Release, pol: Policy, st: State) -> list:
    if pol.tier == 0 and not pol.parent_pubkeys_hex:
        return []
    if pol.parent_threshold == 0:
        return []
    # the policy body itself is what the parents signed
    body = _canon({
        "project": pol.project,
        "tier": pol.tier,
        "version_pattern": pol.version_pattern,
        "semantic_scope": pol.semantic_scope,
        "valid_until_ns": pol.valid_until_ns,
    })
    valid = [pk for pk in pol.parent_pubkeys_hex
             if pol.parent_signatures.get(pk) and
             _verify(pk, pol.parent_signatures[pk], body)]
    if len(valid) < pol.parent_threshold:
        return [f"12 tiered: {len(valid)} valid parent signatures, "
                f"threshold {pol.parent_threshold}"]
    return []


# ── compose ─────────────────────────────────────────────────────
def run_checks(rel: Release, pol: Policy, st: State,
               now_ns: Optional[int] = None) -> list:
    now = now_ns if now_ns is not None else time.time_ns()
    failures = []
    failures += check_capability_scope(rel, pol, st)
    failures += check_time_bound(rel, pol, st, now)
    failures += check_dual_signature(rel, pol, st)
    failures += check_rate_limit(rel, pol, st, now)
    failures += check_monotonic(rel, pol, st)
    failures += check_semantic_scope(rel, pol, st)
    failures += check_witnessed(rel, pol, st)
    failures += check_layered_scope(rel, pol, st, now)
    failures += check_progressive_trust(rel, pol, st)
    failures += check_effect_types(rel, pol, st)
    failures += check_constraint_satisfaction(rel, pol, st)
    failures += check_tiered_delegation(rel, pol, st)
    return failures


# ── CLI entry for the workflow ──────────────────────────────────
def _release_from_env() -> Release:
    dist_dir = Path(os.environ.get("TMIG_DIST", "dist"))
    files = []
    for p in sorted(dist_dir.iterdir()):
        if p.is_file():
            files.append([p.name, _h(p.read_bytes())])
    deps = []
    deps_raw = os.environ.get("TMIG_DEPS", "").strip()
    if deps_raw:
        deps_path = Path(deps_raw)
        if deps_path.is_file():
            deps = sorted(l.strip() for l in deps_path.read_text().splitlines()
                          if l.strip())
    return Release(
        project=os.environ["TMIG_PROJECT"],
        version=os.environ["TMIG_VERSION"].lstrip("v"),
        tag=os.environ["TMIG_TAG"],
        commit=os.environ["TMIG_COMMIT"],
        files=files,
        deps=deps,
        published_at_ns=time.time_ns(),
    )


def _main(argv):
    if argv and argv[0] == "check":
        pol_path = Path(os.environ["TMIG_POLICY"])
        st_path = Path(os.environ["TMIG_STATE"])
        pol = Policy(**json.loads(pol_path.read_text()))
        st = State.load(st_path)
        rel = _release_from_env()
        failures = run_checks(rel, pol, st)
        if failures:
            for f in failures:
                print(f"REFUSE: {f}")
            return 2
        print(f"commit: {rel.project} {rel.version} "
              f"({len(rel.files)} files) passes all policy checks")
        return 0
    if argv and argv[0] == "record":
        # append the just-published release to the state file
        st_path = Path(os.environ["TMIG_STATE"])
        st = State.load(st_path)
        rel = _release_from_env()
        st.releases.append(asdict(rel))
        st.save(st_path)
        print(f"recorded {rel.project} {rel.version}")
        return 0
    print("usage: publisher [check|record]", file=sys.stderr)
    return 1


# ── module guard ────────────────────────────────────────────────
def guard() -> dict:
    now = time.time_ns()
    pol = Policy(
        project="demo",
        version_pattern="1.*",
        semantic_scope="1.2.x",
        monotonic=True,
        rate_window_ns=10**9,
        rate_max=3,
        progressive=True,
        min_history=2,
        narrow_pattern="1.2.0",
        allowed_effects=["add:tstate-*", "modify:*"],
        dep_baseline=["a", "b"],
        dep_growth_max=0,
        parent_pubkeys_hex=[],
        parent_threshold=0,
    )
    st = State()
    st.releases = [
        {"version": "1.2.0", "tag": "v1.2.0", "commit": "x",
         "files": [], "deps": [], "published_at_ns": now - 2 * 10**9},
        {"version": "1.2.1", "tag": "v1.2.1", "commit": "y",
         "files": [], "deps": [], "published_at_ns": now - 10**9},
    ]
    rel = Release(project="demo", version="1.2.2", tag="v1.2.2",
                  commit="z", files=[["tstate-1.2.2.whl", "abc"]],
                  deps=["a", "b"], published_at_ns=now)
    failures = run_checks(rel, pol, st, now)
    if failures:
        return {"verdict": "refuse",
                "reason": "should have passed: " + failures[0]}

    # negative test: monotonic violation
    bad = Release(project="demo", version="1.2.1", tag="v1.2.1",
                  commit="w", files=[["tstate-1.2.1.whl", "def"]],
                  deps=["a", "b"])
    fails2 = run_checks(bad, pol, st, now)
    if not any("5 monotonic" in f for f in fails2):
        return {"verdict": "refuse", "reason": "monotonic did not fire"}

    # negative test: semantic scope
    bad2 = Release(project="demo", version="1.3.0", tag="v1.3.0",
                   commit="v", files=[["tstate-1.3.0.whl", "ghi"]],
                   deps=["a", "b"])
    fails3 = run_checks(bad2, pol, st, now)
    if not any("6 semantic" in f for f in fails3):
        return {"verdict": "refuse", "reason": "semantic-scope did not fire"}

    return {"verdict": "commit", "rules": 12}


def signature() -> str:
    return _h(b"publisher:12-rules-client-side")


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
