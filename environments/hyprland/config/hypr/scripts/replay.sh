#!/usr/bin/env bash
set -euo pipefail

action=${1:-start}
case "$action" in
    start|restart) ;;
    *) printf 'Usage: %s [start|restart]\n' "$0" >&2; exit 2 ;;
esac

cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/hyprland"
mkdir -p "$HOME/clips" "$cache_dir"
exec >>"$cache_dir/replay.log" 2>&1

# Serialize launches; the recorder must not inherit this lock.
exec 9>"${XDG_RUNTIME_DIR:-$cache_dir}/gsr-replay.lock"
flock -n 9 || exit 0

recorder_pattern='^([^[:space:]]*/)?gpu-screen-recorder([[:space:]]|$)'
is_running() {
    pgrep -u "$UID" -f "$recorder_pattern" >/dev/null
}

if [[ "$action" == restart ]]; then
    pkill -SIGINT -u "$UID" -f "$recorder_pattern" || true
    for attempt in {1..50}; do
        if ! is_running; then break; fi
        sleep 0.1
    done
    if is_running; then
        printf 'Replay restart failed: the previous recorder did not stop.\n' >&2
        exit 1
    fi
elif is_running; then
    exit 0
fi

gpu-screen-recorder -w portal -restore-portal-session yes -f 60 -r 60 -c mp4 \
    -a default_output -o "$HOME/clips" -bm cbr -q 35000 9>&- &
recorder_pid=$!

# Keep the launch lock until the new executable is visible to the next call.
for attempt in {1..50}; do
    if ! kill -0 "$recorder_pid" 2>/dev/null; then
        wait "$recorder_pid"
        exit 1
    fi
    if is_running; then exit 0; fi
    sleep 0.1
done
printf 'Replay launch could not be confirmed.\n' >&2
exit 1
