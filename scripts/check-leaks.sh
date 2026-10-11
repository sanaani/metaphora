#!/bin/sh
# The one leak check. The pre-commit hook, the pre-push hook and CI all run it.
#
#   scripts/check-leaks.sh staged     what is about to be committed (pre-commit)
#   scripts/check-leaks.sh tree       every tracked file (pre-push, CI)
#   scripts/check-leaks.sh history    every commit (CI)
#
# Three checks:
#   1. gitleaks: credentials of every common shape (default rules + .gitleaks.toml).
#   2. The private deny-list: client, company and personal terms, read from
#      $METAPHORA_DENYLIST or ~/.config/metaphora/denylist.txt. It is never in the repo,
#      because listing those terms in a public file would itself leak them.
#   3. Size: no tracked file over 2 MB, so no dataset slips in.
set -e
mode=${1:-staged}
top=$(git rev-parse --show-toplevel)
cd "$top"
fail=0

# 1. gitleaks
gl=$(command -v gitleaks || true)
[ -n "$gl" ] || [ ! -x "$HOME/metaphora-data/tools/gitleaks.exe" ] || gl="$HOME/metaphora-data/tools/gitleaks.exe"
[ -n "$gl" ] || [ ! -x "$HOME/metaphora-data/tools/gitleaks" ] || gl="$HOME/metaphora-data/tools/gitleaks"
if [ -z "$gl" ]; then
  echo "leaks: gitleaks not found; install it (docs/data-policy.md)" >&2; exit 1
fi
case "$mode" in
  staged)  "$gl" git --staged --no-banner --redact -c .gitleaks.toml . || fail=1 ;;
  tree)    "$gl" dir --no-banner --redact -c .gitleaks.toml . || fail=1 ;;
  history) "$gl" git --no-banner --redact -c .gitleaks.toml . || fail=1 ;;
  *) echo "usage: $0 staged|tree|history" >&2; exit 2 ;;
esac

# 2. deny-list
list=${METAPHORA_DENYLIST:-$HOME/.config/metaphora/denylist.txt}
if [ ! -s "$list" ]; then
  echo "leaks: deny-list missing ($list); see docs/data-policy.md" >&2; exit 1
fi
terms=$(mktemp); text=$(mktemp); trap 'rm -f "$terms" "$text"' EXIT
# Case is folded with tr, not grep -i: Git for Windows' grep aborts on -i with a pattern
# file, and an aborted grep must never read as "no match".
grep -v '^\s*#' "$list" | tr -d '\r' | sed '/^\s*$/d' | tr '[:upper:]' '[:lower:]' > "$terms"
case "$mode" in
  staged)  git diff --cached -U0 --no-color | grep '^+' | grep -v '^+++' > "$text" || true ;;
  tree)    git ls-files -z | xargs -0 -r cat > "$text" ;;
  history) git log --all -p --no-color | grep '^+' > "$text" || true ;;
esac
rc=0
hits=$(tr '[:upper:]' '[:lower:]' < "$text" | grep -a -w -c -F -f "$terms") || rc=$?
if [ "$rc" -gt 1 ]; then
  echo "leaks: deny-list grep failed (exit $rc); treating as a leak" >&2; fail=1
elif [ "${hits:-0}" -gt 0 ]; then
  echo "leaks: $hits deny-listed match(es) in $mode content. Terms are not printed;" >&2
  echo "       find them by searching the changed files for each term in $list" >&2
  fail=1
fi

# 3. size
big=$(git ls-files -z | xargs -0 -r du -k 2>/dev/null | awk '$1 > 2048 {print $2}')
if [ "$mode" = staged ]; then
  big=$(git diff --cached --name-only -z --diff-filter=AM | xargs -0 -r du -k 2>/dev/null \
        | awk '$1 > 2048 {print $2}')
fi
if [ -n "$big" ]; then
  echo "leaks: files over 2 MB (data belongs in ~/metaphora-data):" >&2; echo "$big" >&2; fail=1
fi

[ "$fail" -eq 0 ] && echo "leaks: clean ($mode)" || { echo "leaks: FAILED ($mode)" >&2; exit 1; }
