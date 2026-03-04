#!/bin/bash
# Nagios plugin: check_iostat.sh — uses /proc/diskstats (no sysstat needed)
# Usage: check_iostat.sh -d <device> -wt <warn_tps> -ct <crit_tps> -wa <warn_await> -ca <crit_await>


DEVICE="sda"
WARN_TPS=300; CRIT_TPS=600
WARN_AWAIT=20; CRIT_AWAIT=50
INTERVAL=2


while [[ $# -gt 0 ]]; do
  case $1 in
    -d)  DEVICE=$2;     shift 2 ;;
    -wt) WARN_TPS=$2;   shift 2 ;;
    -ct) CRIT_TPS=$2;   shift 2 ;;
    -wa) WARN_AWAIT=$2; shift 2 ;;
    -ca) CRIT_AWAIT=$2; shift 2 ;;
    *)   shift ;;
  esac
done


# /proc/diskstats fields (by column number):
#  $4 = reads_completed   $7 = ms_spent_reading
#  $8 = writes_completed  $11 = ms_spent_writing
read_diskstats() {
  awk -v dev="$DEVICE" '$3 == dev {print $4, $7, $8, $11}' /proc/diskstats
}


SNAP1=$(read_diskstats)
[ -z "$SNAP1" ] && { echo "UNKNOWN: Device $DEVICE not found in /proc/diskstats"; exit 3; }


sleep $INTERVAL
SNAP2=$(read_diskstats)


R1=$(echo $SNAP1 | awk '{print $1}');  MS_R1=$(echo $SNAP1 | awk '{print $2}')
W1=$(echo $SNAP1 | awk '{print $3}');  MS_W1=$(echo $SNAP1 | awk '{print $4}')
R2=$(echo $SNAP2 | awk '{print $1}');  MS_R2=$(echo $SNAP2 | awk '{print $2}')
W2=$(echo $SNAP2 | awk '{print $3}');  MS_W2=$(echo $SNAP2 | awk '{print $4}')


DELTA_IOS=$(( (R2 - R1) + (W2 - W1) ))
DELTA_MS=$(( (MS_R2 - MS_R1) + (MS_W2 - MS_W1) ))


TPS=$(awk "BEGIN {printf \"%.1f\", $DELTA_IOS / $INTERVAL}")
if [ $DELTA_IOS -gt 0 ]; then
  AWAIT=$(awk "BEGIN {printf \"%.1f\", $DELTA_MS / $DELTA_IOS}")
else
  AWAIT="0.0"
fi


TPS_INT=$(printf "%.0f" $TPS)
AWAIT_INT=$(printf "%.0f" $AWAIT)


PERF="tps=${TPS};${WARN_TPS};${CRIT_TPS};; await=${AWAIT}ms;${WARN_AWAIT};${CRIT_AWAIT};;"
STATUS="TPS=${TPS} Await=${AWAIT}ms (device: ${DEVICE})"


if [ $TPS_INT -ge $CRIT_TPS ] || [ $AWAIT_INT -ge $CRIT_AWAIT ]; then
  echo "CRITICAL: I/O $STATUS | $PERF"; exit 2
elif [ $TPS_INT -ge $WARN_TPS ] || [ $AWAIT_INT -ge $WARN_AWAIT ]; then
  echo "WARNING: I/O $STATUS | $PERF"; exit 1
else
  echo "OK: I/O $STATUS | $PERF"; exit 0
fi
