#!/bin/bash

# Mount the WISPR SD card (exposed via SDIO by the WISPR firmware after boot).
# Retries until the device appears, since WISPR's sd_card_enable() fires
# after its own boot sequence (GPS sync, RTC init, etc.) which can take
# 30-90 seconds. Gives up after MAX_ATTEMPTS and logs the failure.

MOUNT_POINT=/media/wispr_sd
DEVICE_P1=/dev/mmcblk1p1    # partitioned card (MBR present)
DEVICE_RAW=/dev/mmcblk1     # raw exFAT with no partition table (fallback)
LOG=/home/pi/wispr_pi/pressure_sensor/logs/mountlauncher.log
MAX_ATTEMPTS=60             # 10 minute timeout for the WISPR to find a PPS lock
RETRY_INTERVAL=10           # seconds between retries

mkdir -p "$MOUNT_POINT"
mkdir -p "$(dirname "$LOG")"

echo "$(date -u): Waiting for WISPR SD card..." | tee "$LOG"

for ((i=1; i<=MAX_ATTEMPTS; i++)); do
    if [ -b "$DEVICE_P1" ]; then
        DEVICE="$DEVICE_P1"
    elif [ -b "$DEVICE_RAW" ]; then
        DEVICE="$DEVICE_RAW"
    else
        echo "$(date -u): Attempt $i/$MAX_ATTEMPTS — device not found, retrying in ${RETRY_INTERVAL}s" | tee -a "$LOG"
        sleep "$RETRY_INTERVAL"
        continue
    fi

    if mount "$DEVICE" "$MOUNT_POINT" 2>>"$LOG"; then
        echo "$(date -u): Mounted $DEVICE at $MOUNT_POINT" | tee -a "$LOG"
        exit 0
    else
        echo "$(date -u): Attempt $i/$MAX_ATTEMPTS — mount failed, retrying in ${RETRY_INTERVAL}s" | tee -a "$LOG"
        sleep "$RETRY_INTERVAL"
    fi
done

echo "$(date -u): ERROR — failed to mount WISPR SD card after $MAX_ATTEMPTS attempts" | tee -a "$LOG"
exit 1
