#!/bin/bash
# check_iostat.sh — auto-discovers physical disks via /sys/block/
# No sysstat needed — reads /proc/diskstats directly
# Usage: check_iostat.sh [-wt warn_tps] [-ct crit_tps] [-wa warn_await] [-ca crit_await]


WARN_TPS=300; CRIT_TPS=600; WARN_AWAIT=20; CRIT_AWAIT=50; INTERVAL=2
while [[ $# -gt 0 ]]; do
  case $1 in
    -wt) WARN_TPS=$2;   shift 2 ;;   -ct) CRIT_TPS=$2;   shift 2 ;;
    -wa) WARN_AWAIT=$2; shift 2 ;;   -ca) CRIT_AWAIT=$2; shift 2 ;;
    *)   shift ;;
  esac
done


# Auto-discover physical disks — skip loop* and removable devices
get_disks() {
  for dev in /sys/block/*/; do
    name=$(basename "$dev")
    [[ "$name" == loop* ]] && continue
    [[ "$name" == ram* ]]  && continue
    removable=$(cat "${dev}removable" 2>/dev/null)
    [[ "$removable" == "1" ]] && continue
    echo "$name"
  done
}


read_diskstats() {
  awk -v d="$1" '$3 == d {print $4, $7, $8, $11}' /proc/diskstats
}


DISKS=$(get_disks)
[ -z "$DISKS" ] && { echo "UNKNOWN: No physical disks found"; exit 3; }


# Snapshot 1 — capture all disks simultaneously
declare -A SNAP1
for disk in $DISKS; do SNAP1[$disk]=$(read_diskstats "$disk"); done
sleep $INTERVAL
declare -A SNAP2
for disk in $DISKS; do SNAP2[$disk]=$(read_diskstats "$disk"); done


WORST_STATE=0; PERF=""; DETAILS=""
for disk in $DISKS; do
  # Parse snapshots, compute DELTA_IOS and DELTA_MS per disk
  # Calculate TPS = DELTA_IOS / INTERVAL
  # Calculate AWAIT = DELTA_MS / DELTA_IOS (0.0 if no I/O)
  # Append to PERF string: disk_tps=...; disk_await=...
  # Update WORST_STATE (0=OK, 1=WARN, 2=CRIT) based on thresholds
done


case $WORST_STATE in
  2) echo "CRITICAL: I/O $DETAILS | $PERF"; exit 2 ;;
  1) echo "WARNING:  I/O $DETAILS | $PERF"; exit 1 ;;
  *) echo "OK:       I/O $DETAILS | $PERF"; exit 0 ;;
esac
