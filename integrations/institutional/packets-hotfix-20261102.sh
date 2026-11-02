#!/usr/bin/env bash
# Funding packets hotfix for fsn1, 2026-11-02. Review it, then run each phase as root.
#
# One dated overlay image, FROM the packets image the box runs now
# (INSTITUTIONAL_IMAGE sha256:408c00c5..., tag financial-evidence-packets:dated-14b82eeba65f,
# source 14b82ee). It copies three modules from hotfix/packets-overlay-20261102 at
# e53de52, which is 14b82ee plus two fixes, so they match every other module in the image:
#   reliability.py        #206  a retired release keeps its own reliability window
#   institutional.py      #204  attempt receipts are written atomically; empty
#   institutional_api.py  #204  receipts are counted, never parsed
#
# Units and images, as read from the box on 2026-11-02:
#   INSTITUTIONAL_IMAGE  financial-evidence-packets.service     API on 127.0.0.1:6910; restarted by `apply`
#                        financial-evidence-packet-capture      timer/path oneshot; its next run uses the new image
#                        financial-evidence-usage-expiry        timer oneshot; its next run uses the new image
#   WORKSPACE_IMAGE      financial-evidence-workspace.service   unchanged: it imports only reliability.now
#                                                              and reliability.timestamp, which no fix touches
#   (no image)           financial-evidence-runtime             a venv pinned by implementation hash; its
#                                                              store.py fix (#204) needs a runtime release,
#                                                              not this overlay. See `runtime-note`.
#
# Phases (each one checks what the previous one recorded):
#   bash packets-hotfix-20261102.sh preflight     read-only checks
#   bash packets-hotfix-20261102.sh build         fetch e53de52 and build the dated image
#   bash packets-hotfix-20261102.sh smoke         no-network checks and tests inside the new image
#   bash packets-hotfix-20261102.sh apply         back up institutional.env, switch the image, restart packets only
#   bash packets-hotfix-20261102.sh verify        endpoints, one capture run, reliability values
#   bash packets-hotfix-20261102.sh rollback      restore the backup and restart packets
#   bash packets-hotfix-20261102.sh runtime-note  what the runtime fix needs instead
# Nothing here prints institutional.env beyond its INSTITUTIONAL_IMAGE line.
set -euo pipefail
umask 022

HOTFIX_COMMIT=e53de52259aca56123644966564b5b0cecd7a463
HOTFIX_REF=refs/heads/hotfix/packets-overlay-20261102
BASE_IMAGE=sha256:408c00c54ed3dc3275ac2266c28af84fbf881a5d440f25d6e0244a6dfe4e75d6
BASE_COMMIT=14b82eeba65ff3ec1466ebacdd9a2d110ff95fdc
REPO_URL=https://github.com/beepboop2025/financial-evidence-skills.git
TAG="financial-evidence-packets:dated-${HOTFIX_COMMIT:0:12}"
WORK="/var/tmp/fe-packets-hotfix-${HOTFIX_COMMIT:0:12}"
CONTEXT="$WORK/.overlay-context"
DOCKERFILE=Dockerfile.packets-hotfix-20261102
ENV_FILE=/etc/financial-evidence/institutional.env
STATE=/root/fe-packets-hotfix-20261102.state
SITE=/usr/local/lib/python3.13/site-packages/financial_evidence
API=http://127.0.0.1:6910
PUBLIC=https://api.seiche.info/funding-evidence
MODULES=(reliability.py institutional.py institutional_api.py)
declare -A EXPECTED=(
  [reliability.py]=20c653c9aeb9bdbe228daca38f6641b404550819c3028d090ea1f841ff8b21cb
  [institutional.py]=464f444bd52bd2d010569ca46220a30bf0c366ccaa07a2b28b7cdaac5e0d2b66
  [institutional_api.py]=03f27f8b10ee677c49d51eac71c33953da8b5e129a6b3d9f4ed3ec6ff8466650
)
# The live units' container hardening, with no network for checks and tests.
# shellcheck disable=SC2054  # the tmpfs options are one comma-separated argument
RUN=(docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges
     --user 65532:65532 --tmpfs /tmp:rw,nosuid,size=32m)

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
die() { log "STOP: $*"; exit 1; }
state_get() { [[ -f "$STATE" ]] && sed -n "s/^$1=//p" "$STATE" | tail -1 || true; }
state_set() { touch "$STATE"; chmod 600 "$STATE"; printf '%s=%s\n' "$1" "$2" >> "$STATE"; }
current_image() { sed -n 's/^INSTITUTIONAL_IMAGE=//p' "$ENV_FILE"; }
require_root() { [[ $EUID -eq 0 ]] || die "run as root"; }

wait_healthy() {
  local _
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 5 "$API/healthz" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  die "packets API did not answer /healthz within 60 s"
}

# Hash every module of the installed package inside an image, one "name sha256" per line.
module_hashes() {
  "${RUN[@]}" --entrypoint python "$1" -c '
import hashlib, pathlib, sys
root = pathlib.Path(sys.argv[1])
for path in sorted(root.rglob("*.py")):
    print(path.relative_to(root), hashlib.sha256(path.read_bytes()).hexdigest())
' "$SITE"
}

preflight() {
  require_root
  [[ "$(grep -c '^INSTITUTIONAL_IMAGE=' "$ENV_FILE")" == 1 ]] || die "expected one INSTITUTIONAL_IMAGE line in $ENV_FILE"
  local current new
  current="$(current_image)"
  new="$(state_get NEW_IMAGE)"
  log "institutional.env INSTITUTIONAL_IMAGE=$current"
  if [[ -n "$new" && "$current" == "$new" ]]; then
    log "the hotfix image is already live; use verify or rollback"
  elif [[ "$current" != "$BASE_IMAGE" ]]; then
    die "the box runs $current, not the reviewed base $BASE_IMAGE; rebuild the overlay FROM what runs now"
  fi
  [[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$BASE_IMAGE")" == "$BASE_COMMIT" ]] \
    || die "base image revision label is not $BASE_COMMIT"
  systemctl is-active --quiet financial-evidence-packets.service || die "financial-evidence-packets is not active"
  log "packets container image: $(docker inspect --format '{{.Image}}' financial-evidence-packets)"
  local free_kb
  free_kb="$(df --output=avail -k /var/lib/docker | tail -1)"
  (( free_kb > 2 * 1024 * 1024 )) || die "less than 2 GB free for Docker"
  log "preflight passed"
}

build() {
  preflight
  rm -rf -- "$WORK"
  git clone --quiet --no-checkout --filter=blob:none "$REPO_URL" "$WORK"
  git -C "$WORK" fetch --quiet origin "$HOTFIX_REF"
  git -C "$WORK" -c advice.detachedHead=false checkout --quiet "$HOTFIX_COMMIT"
  [[ "$(git -C "$WORK" rev-parse HEAD)" == "$HOTFIX_COMMIT" ]] || die "checkout is not $HOTFIX_COMMIT"
  local name
  for name in "${MODULES[@]}"; do
    [[ "$(sha256sum "$WORK/src/financial_evidence/$name" | cut -d' ' -f1)" == "${EXPECTED[$name]}" ]] \
      || die "$name does not match its reviewed hash"
  done
  # A minimal build context: the Dockerfile and the three reviewed modules only.
  rm -rf -- "$CONTEXT"
  mkdir -p "$CONTEXT/src/financial_evidence"
  cp "$WORK/$DOCKERFILE" "$CONTEXT/"
  for name in "${MODULES[@]}"; do cp "$WORK/src/financial_evidence/$name" "$CONTEXT/src/financial_evidence/"; done
  # The classic builder accepts FROM <image ID>; the earlier dated overlays on this box were built with it.
  DOCKER_BUILDKIT=0 docker build --quiet -f "$CONTEXT/$DOCKERFILE" \
    --build-arg SOURCE_COMMIT="$HOTFIX_COMMIT" -t "$TAG" "$CONTEXT" >/dev/null
  local image
  image="$(docker image inspect --format '{{.Id}}' "$TAG")"
  state_set NEW_IMAGE "$image"
  state_set BUILT_AT "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  log "built $TAG = $image"
}

smoke() {
  require_root
  local new
  new="$(state_get NEW_IMAGE)"
  [[ -n "$new" ]] || die "no built image recorded; run build"
  [[ "$(docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$new")" == "$HOTFIX_COMMIT" ]] \
    || die "new image revision label is not $HOTFIX_COMMIT"
  [[ "$(docker image inspect --format '{{json .Config.Entrypoint}} {{json .Config.Cmd}} {{.Config.User}}' "$new")" \
    == "$(docker image inspect --format '{{json .Config.Entrypoint}} {{json .Config.Cmd}} {{.Config.User}}' "$BASE_IMAGE")" ]] \
    || die "entrypoint, command or user differs from the base image"

  # Exactly the three reviewed modules differ from the base image, with the reviewed bytes.
  local diffs expected_diff name
  diffs="$(diff <(module_hashes "$BASE_IMAGE") <(module_hashes "$new") | sed -n 's/^> //p' || true)"
  expected_diff="$(for name in "${MODULES[@]}"; do printf '%s %s\n' "$name" "${EXPECTED[$name]}"; done | sort)"
  [[ "$(sort <<<"$diffs")" == "$expected_diff" ]] || { printf '%s\n' "$diffs"; die "the image changes other modules or other bytes"; }
  log "module check passed: only ${MODULES[*]} changed"

  "${RUN[@]}" --entrypoint python "$new" -c '
import os
import financial_evidence.institutional as institutional
import financial_evidence.institutional_api as api
import financial_evidence.reliability as reliability
assert os.environ["FINANCIAL_EVIDENCE_SOURCE_COMMIT"] == "'"$HOTFIX_COMMIT"'"
assert callable(reliability.summarize_releases) and callable(institutional.read_attempts)
app = api.create_app("/tmp/archive", "/tmp/usage")
assert {"/reliability", "/history", "/latest"} <= {route.path for route in app.routes}
print("imports and routes ok")'

  # The packet test subsets from the hotfix tree, run against the installed overlay
  # (the tests add a /src path that does not exist in the image, so they import site-packages).
  local suite out
  for suite in test_reliability_release_windows.py test_institutional.py test_public_packet_rights.py test_original_publishers.py; do
    out="$("${RUN[@]}" -v "$WORK/tests:/tests:ro" --entrypoint python "$new" -m unittest discover -s /tests -p "$suite" 2>&1)" \
      || { printf '%s\n' "$out" | tail -30; die "$suite failed inside the image"; }
    log "$suite: $(printf '%s\n' "$out" | grep -E '^(Ran|OK)' | tr '\n' ' ')"
    printf '%s\n' "$out" | grep -q '^Ran [1-9]' || die "$suite ran no tests"
  done
  state_set SMOKE_OK "$new"
  log "smoke passed for $new"
}

apply() {
  require_root
  local new current backup tmp
  new="$(state_get NEW_IMAGE)"
  [[ -n "$new" && "$(state_get SMOKE_OK)" == "$new" ]] || die "run build and smoke first"
  current="$(current_image)"
  if [[ "$current" == "$new" ]]; then
    log "institutional.env already points at $new"
  else
    [[ "$current" == "$BASE_IMAGE" ]] || die "institutional.env points at $current, not the reviewed base"
    backup="$ENV_FILE.bak-$(date -u +%Y%m%dT%H%M%SZ)-pre-packets-hotfix-${HOTFIX_COMMIT:0:12}"
    cp -p "$ENV_FILE" "$backup"
    state_set ENV_BACKUP "$backup"
    tmp="$(mktemp "$ENV_FILE.XXXXXX")"
    sed "s|^INSTITUTIONAL_IMAGE=${BASE_IMAGE}\$|INSTITUTIONAL_IMAGE=${new}|" "$ENV_FILE" > "$tmp"
    chown root:root "$tmp"; chmod 600 "$tmp"
    # Every other line must be byte-identical; compared silently so no value is printed.
    cmp -s <(grep -v '^INSTITUTIONAL_IMAGE=' "$ENV_FILE") <(grep -v '^INSTITUTIONAL_IMAGE=' "$tmp") \
      || { rm -f -- "$tmp"; die "the edit would change more than INSTITUTIONAL_IMAGE"; }
    grep -qx "INSTITUTIONAL_IMAGE=$new" "$tmp" || { rm -f -- "$tmp"; die "the new image line was not written"; }
    mv -f -- "$tmp" "$ENV_FILE"
    log "institutional.env now uses $new (backup: $backup)"
  fi
  # Only the long-running API restarts. Capture and usage expiry are oneshots that
  # read institutional.env at their next start.
  state_set APPLIED_AT "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  systemctl restart financial-evidence-packets.service
  wait_healthy
  [[ "$(docker inspect --format '{{.Image}}' financial-evidence-packets)" == "$new" ]] || die "the packets container is not on $new"
  log "financial-evidence-packets restarted on $new"
}

verify() {
  require_root
  local new
  new="$(state_get NEW_IMAGE)"
  [[ -n "$new" && "$(current_image)" == "$new" ]] || die "the hotfix image is not live"
  [[ "$(docker inspect --format '{{.Image}}' financial-evidence-packets)" == "$new" ]] || die "the packets container is not on $new"
  curl -fsS --max-time 10 "$API/healthz" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["status"] == "ok" and d["source_commit"] == sys.argv[1], d
print("healthz ok, source_commit", d["source_commit"])' "$HOTFIX_COMMIT"

  # Retired releases now report their own sampled availability, readiness and p95.
  local target
  for target in "$API/reliability" "$PUBLIC/reliability"; do
    curl -fsS --max-time 20 "$target" | python3 -c '
import json, sys
report = json.load(sys.stdin)
keys = ("sampled_availability_pct", "sampled_readiness_pct", "successful_request_p95_seconds")
missing = []
for prior in report["prior_releases"]:
    release, end = prior["expected_release"], prior["evaluated_at"]
    for perspective, view in prior["perspectives"].items():
        values = [view[key] for key in keys]
        print("  %-32s %-18s window %s..%s slots %s/%s avail %s ready %s p95 %s" % (
            release, perspective, view["window_started_at"][:16], end[:16],
            view["observed_slots"], view["expected_slots"], *values))
        if any(value is None for value in values):
            missing.append((release, perspective))
assert report["prior_releases"], "no prior releases reported"
assert not missing, "null sampled values remain: %r" % (missing,)
print("reliability ok:", sys.argv[1])' "$target"
  done

  curl -fsS --max-time 20 "$API/history" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert "empty_attempt_receipts" in d, "history lacks empty_attempt_receipts (receipt fix not live)"
print("history ok, empty_attempt_receipts =", d["empty_attempt_receipts"])'
  curl -fsS --max-time 20 -o /dev/null "$API/latest" && log "latest ok"

  # One capture on the new image, then the receipt it wrote must be complete JSON.
  local started newest
  started="$(date +%s)"
  systemctl start financial-evidence-packet-capture.service
  [[ "$(systemctl show -p Result --value financial-evidence-packet-capture.service)" == success ]] || die "capture run did not succeed"
  newest="$(find /var/lib/financial-evidence-institutional/archive/attempts -maxdepth 1 -name '*.json' -newermt "@$started" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
  [[ -n "$newest" && -s "$newest" ]] || die "the capture wrote no non-empty attempt receipt"
  python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); print("capture receipt ok:", d.get("attempt_id"), "error =", d.get("error"))' "$newest"

  log "runtime (unchanged by this overlay): 'database is locked' in the last 24 h: $(journalctl -u financial-evidence-runtime.service --since -24h -o cat 2>/dev/null | grep -c 'database is locked' || true)"
  log "verify passed"
}

rollback() {
  require_root
  local backup base_line
  backup="${1:-$(state_get ENV_BACKUP)}"
  [[ -n "$backup" && -f "$backup" ]] || die "no recorded institutional.env backup; pass its path"
  base_line="$(grep -c "^INSTITUTIONAL_IMAGE=${BASE_IMAGE}\$" "$backup" || true)"
  [[ "$base_line" == 1 ]] || die "$backup does not point at the reviewed base image"
  cp -p "$backup" "$ENV_FILE"
  systemctl restart financial-evidence-packets.service
  wait_healthy
  [[ "$(docker inspect --format '{{.Image}}' financial-evidence-packets)" == "$BASE_IMAGE" ]] || die "packets is not back on $BASE_IMAGE"
  curl -fsS --max-time 10 "$API/healthz" | python3 -c 'import json, sys; d = json.load(sys.stdin); assert d["source_commit"] == sys.argv[1], d; print("rolled back, source_commit", d["source_commit"])' "$BASE_COMMIT"
  state_set ROLLED_BACK_AT "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  log "capture and usage expiry use the base image again from their next run; the hotfix image $TAG is kept for inspection"
}

runtime_note() {
  cat <<'NOTE'
financial-evidence-runtime is not a container. It runs
/opt/financial-evidence-runtime/current/.venv (current -> releases/0.1.7), and
financial-evidence-runtime-monitor runs ops.py from
/opt/financial-evidence-runtime-ops/releases/32d26fbb.../, whose runtime-release.json pins
package 0.1.7, source 286e86bc, the wheel hash and implementation_sha256 925593f3...
The monitor refuses a different implementation, so copying store.py into the venv would
break it. The #204 runtime fix (fd47f87, cherry-picks cleanly onto 286e86bc) needs its own
release: build a 0.1.7.post1 wheel from 286e86bc plus fd47f87, install it into a new
/opt/financial-evidence-runtime/releases/<version> venv, publish a new operations release
whose runtime-release.json records the new wheel and implementation hashes, rerun
configure.py and install.py with --previous-plan as in
integrations/agent-runtime/operations/README.md, then switch `current`.
On 2026-11-02 there were 0 "database is locked" failures in the last 24 h; the 33 seen
in 96 h all fell between 22:00 and 22:49Z on 2026-10-31.
NOTE
}

case "${1:-}" in
  preflight) preflight ;;
  build) build ;;
  smoke) smoke ;;
  apply) apply ;;
  verify) verify ;;
  rollback) shift; rollback "${1:-}" ;;
  runtime-note) runtime_note ;;
  *) sed -n '2,32p' "$0"; exit 2 ;;
esac
