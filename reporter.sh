#!/bin/bash
# by Pit Rho (http://www.pitrho.com)

REPORT_CPU=false
REPORT_MEM=false
REPORT_DISK=false
REPORT_NET=false
REPORT_FREQUENCY=1
REPORT_MESSAGE=""

while getopts ":cmdnf:" opt; do
  case $opt in
    c)
      # CPU
      REPORT_CPU=true
      echo "Reporting CPU Usage ..."
      ;;
    m)
      # Memory
      REPORT_MEM=true
      echo "Reporting Memory Usage ..."
      ;;
    d)
      # Disk
      REPORT_DISK=true
      echo "Reporting Disk Usage ..."
      ;;
    n)
      # Network
      REPORT_NET=true
      echo "Reporting Network Usage ..."
      ;;
    f)
      # Frequency
      REPORT_FREQUENCY=${OPTARG}
      ;;
    \?)
      echo "Invalid option -$OPTARG ..."
      ;;
  esac
done

# CPU diff by Paul Colby (http://colby.id.au)
PREV_TOTAL=0
PREV_IDLE=0

while true; do
  REPORT_MESSAGE=""  # Clear each round

  if [ "$REPORT_CPU" = true ] ; then
    CPU=(`cat /prochost/stat | grep '^cpu '`) # Get the total CPU statistics.
    unset CPU[0]                          # Discard the "cpu" prefix.
    IDLE=${CPU[4]}                        # Get the idle CPU time.

    # Calculate the total CPU time.
    TOTAL=0

    for VALUE in "${CPU[@]:0:4}"; do
      let "TOTAL=$TOTAL+$VALUE"
    done

    # Calculate the CPU usage since we last checked.
    let "DIFF_IDLE=$IDLE-$PREV_IDLE"
    let "DIFF_TOTAL=$TOTAL-$PREV_TOTAL"
    let "DIFF_USAGE=(1000*($DIFF_TOTAL-$DIFF_IDLE)/$DIFF_TOTAL+5)/10"
    CPU_MESSAGE="CPU: $DIFF_USAGE%"
    REPORT_MESSAGE+=$CPU_MESSAGE" "
  fi

  if [ "$REPORT_MEM" = true ] ; then
    # Remember the total and idle CPU times for the next check.
    PREV_TOTAL="$TOTAL"
    PREV_IDLE="$IDLE"

    # Get our memory usage
    MEMORY_TOTAL=(`cat /prochost/meminfo | grep ^MemTotal: `)
    MEMORY_TOTAL=${MEMORY_TOTAL[1]}
    MEMORY_FREE=(`cat /prochost/meminfo | grep ^MemFree: `)
    MEMORY_FREE=${MEMORY_FREE[1]}
    MEMORY_UNIT=${MEMORY_FREE[2]}
    let "MEMORY_USED=($MEMORY_TOTAL-$MEMORY_FREE)"
    MEMORY_PCT=$(bc -l <<< "scale=4; ($MEMORY_USED/$MEMORY_TOTAL)*100")

    MEMORY_USED_GB=$(bc -l <<< "scale=4; ($MEMORY_USED/1000000)")
    MEMORY_TOTAL_GB=$(bc -l <<< "scale=4; ($MEMORY_TOTAL/1000000)")
    MEM_MESSAGE="Memory Used: ${MEMORY_PCT:0:-2}% (${MEMORY_USED_GB:0:-2}GB of ${MEMORY_TOTAL_GB:0:-2}GB)"
    REPORT_MESSAGE+=$MEM_MESSAGE" "
  fi

  if [ "$REPORT_DISK" = true ] ; then
    DISK_USAGE=$(df -lh | awk '{if ($6 == "/") { print $5 " (" $3 "/" $2 ")"}}' | head -1)
    DISK_MESSAGE="Disk Usage: "$DISK_USAGE" "
    REPORT_MESSAGE+=$DISK_MESSAGE
  fi

  if [ "$REPORT_NET" = true ] ; then
    NETWORK_MESSAGE="Netowrk stats not yet implemented ..."
    REPORT_MESSAGE+=$NETWORK_MESSAGE" "
  fi

  # Report our message to stdout
  echo -e $REPORT_MESSAGE


  # Wait before checking again.
  sleep $REPORT_FREQUENCY
done
