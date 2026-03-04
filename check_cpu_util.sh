#!/bin/bash
# Nagios plugin: check_cpu_util.sh
# Checks CPU utilization via /proc/stat (1-second sample)


WARN=80
CRIT=90


while [[ $# -gt 0 ]]; do
  case $1 in
    -w) WARN=$2; shift 2 ;;
    -c) CRIT=$2; shift 2 ;;
    *)  shift ;;
  esac
done


# Read two /proc/stat snapshots 1 second apart
read_cpu() { awk '/^cpu /{print $2,$3,$4,$5,$6,$7,$8}' /proc/stat; }


SNAP1=$(read_cpu); sleep 1; SNAP2=$(read_cpu)


IDLE1=$(echo $SNAP1 | awk '{print $4}')
TOTAL1=$(echo $SNAP1 | awk '{s=0; for(i=1;i<=NF;i++) s+=$i; print s}')
IDLE2=$(echo $SNAP2 | awk '{print $4}')
TOTAL2=$(echo $SNAP2 | awk '{s=0; for(i=1;i<=NF;i++) s+=$i; print s}')


DIFF_IDLE=$(( IDLE2 - IDLE1 ))
DIFF_TOTAL=$(( TOTAL2 - TOTAL1 ))
CPU_UTIL=$(awk "BEGIN {printf \"%.1f\", (1 - $DIFF_IDLE/$DIFF_TOTAL) * 100}")
CPU_INT=$(printf "%.0f" $CPU_UTIL)


PERF="cpu_util=${CPU_UTIL}%;${WARN};${CRIT};0;100"


if [ $CPU_INT -ge $CRIT ]; then
  echo "CRITICAL: CPU utilization is ${CPU_UTIL}% | $PERF"; exit 2
elif [ $CPU_INT -ge $WARN ]; then
  echo "WARNING: CPU utilization is ${CPU_UTIL}% | $PERF"; exit 1
else
  echo "OK: CPU utilization is ${CPU_UTIL}% | $PERF"; exit 0
fi
