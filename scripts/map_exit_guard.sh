#!/usr/bin/env bash
# Guard for the exit code of a per-entity `linkml-map map-data` run.
#
# Called by pipeline.Makefile's map recipe. Decides whether the child's exit
# code should fail the pipeline:
#
#   * A SIGNAL KILL (exit >= 128, e.g. 137 = SIGKILL/OOM, 143 = SIGTERM,
#     139 = SIGSEGV) means the process was terminated mid-run and its output is
#     INCOMPLETE. That must ALWAYS fail — even in non-strict mode — so a killed
#     entity can never be masked as "success" (silent truncation / 0-byte output).
#
#   * A normal non-zero exit (1..125, e.g. linkml-map's own --continue-on-error
#     row errors) is tolerated in non-strict mode, as before; in strict mode it
#     fails.
#
#   * 0 always passes.
#
# Usage: map_exit_guard.sh <exit_code> <entity> <strict> [logfile]
set -uo pipefail

rc="${1:?exit code required}"
entity="${2:?entity name required}"
strict="${3:?strict flag required}"
log="${4:-/dev/null}"

echo "map-data '${entity}' exited with code ${rc}" | tee -a "${log}"

if [ "${rc}" -ge 128 ]; then
    echo "✗ FATAL: map-data '${entity}' was killed by signal $((rc - 128)) (exit ${rc}); output is INCOMPLETE and must not be reported as success." \
        | tee -a "${log}" >&2
    exit "${rc}"
fi

if [ "${rc}" -ne 0 ] && [ "${strict}" != "false" ]; then
    exit "${rc}"
fi

exit 0
