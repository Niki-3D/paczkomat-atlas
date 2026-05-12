#!/usr/bin/env bash
set -euo pipefail
CMD="${CLAUDE_TOOL_INPUT:-}"
if echo "$CMD" | grep -qE 'rm -rf /(\s|$)|rm -rf ~/|rm -rf \*|:\(\)\{:\|:&\};:|mkfs|dd if=.*of=/dev/'; then
  echo '{"block": true, "message": "Dangerous command pattern detected. Refusing."}' >&2
  exit 2
fi
exit 0
