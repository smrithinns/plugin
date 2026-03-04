#!/bin/bash
# check_iostat.sh — auto-discovers physical disks via /sys/block/
# No sysstat needed — reads /proc/diskstats directly
# Usage: check_iostat.sh [-wt warn_tps] [-ct crit_tps] [-wa warn_await] [-ca crit_await]

WARN_TPS=300; CRIT_TPS=600; WARN_AWAIT=20; CRIT_AWAIT=50; INTERVAL=2

while [[ $# -gt 0 ]]; do
  case $1 in
    -wt) WARN_TPS=$2;   shift 2 ;;
    -ct) CRIT_TPS=$2;   shift 2 ;;
    -wa) WARN_AWAIT=$2; shift 2 ;;
    -ca) CRIT_AWAIT=$2; shift 2 ;;
    *)   shift ;;
  esac
done

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

declare -A SNAP1
for disk in $DISKS; do SNAP1[$disk]=$(read_diskstats "$disk"); done
sleep $INTERVAL
declare -A SNAP2
for disk in $DISKS; do SNAP2[$disk]=$(read_diskstats "$disk"); done

WORST_STATE=0; PERF=""; DETAILS=""

for disk in $DISKS; do
  S1=${SNAP1[$disk]}; S2=${SNAP2[$disk]}
  R1=$(echo $S1 | awk '{print $1}');   MSR1=$(echo $S1 | awk '{print $2}')
  W1=$(echo $S1 | awk '{print $3}');   MSW1=$(echo $S1 | awk '{print $4}')
  R2=$(echo $S2 | awk '{print $1}');   MSR2=$(echo $S2 | awk '{print $2}')
  W2=$(echo $S2 | awk '{print $3}');   MSW2=$(echo $S2 | awk '{print $4}')

  DELTA_IOS=$(( (R2 - R1) + (W2 - W1) ))
  DELTA_MS=$(( (MSR2 - MSR1) + (MSW2 - MSW1) ))

  TPS=$(awk "BEGIN {printf \"%.1f\", $DELTA_IOS / $INTERVAL}")
  if [ $DELTA_IOS -gt 0 ]; then
    AWAIT=$(awk "BEGIN {printf \"%.1f\", $DELTA_MS / $DELTA_IOS}")
  else
    AWAIT="0.0"
  fi

  TPS_INT=$(printf "%.0f" $TPS)
  AWAIT_INT=$(printf "%.0f" $AWAIT)

  PERF="${PERF} ${disk}_tps=${TPS};${WARN_TPS};${CRIT_TPS};; ${disk}_await=${AWAIT}ms;${WARN_AWAIT};${CRIT_AWAIT};;"
  DETAILS="${DETAILS} ${disk}:TPS=${TPS}/Await=${AWAIT}ms"

  if [ $TPS_INT -ge $CRIT_TPS ] || [ $AWAIT_INT -ge $CRIT_AWAIT ]; then
    [ $WORST_STATE -lt 2 ] && WORST_STATE=2
  elif [ $TPS_INT -ge $WARN_TPS ] || [ $AWAIT_INT -ge $WARN_AWAIT ]; then
    [ $WORST_STATE -lt 1 ] && WORST_STATE=1
  fi
done

DETAILS=$(echo $DETAILS | sed 's/^ //')

case $WORST_STATE in
  2) echo "CRITICAL: I/O $DETAILS |$PERF"; exit 2 ;;
  1) echo "WARNING:  I/O $DETAILS |$PERF"; exit 1 ;;
  *) echo "OK:       I/O $DETAILS |$PERF"; exit 0 ;;
esac
