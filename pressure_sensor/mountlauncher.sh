#!/bin/bash

# Wait for WISPR's secondary SD card (exposed via SDIO) to be enumerated,
# then mount it permanently. tdh_pressure.py writes directly to the mount
# point — no mount/unmount per burst.
# WISPR calls sd_card_enable() after GPS PPS sync, which can be up to 90s
# post-boot, so allow up to 10 minutes before giving up.

MOUNT_POINT=/media/wispr_sd
DEVICE_P1=/dev/mmcblk1p1   # partitioned card (MBR present)
DEVICE_RAW=/dev/mmcblk1    # raw card with no partition table (fallback)
LOG=/home/pi/wispr_pi/pressure_sensor/logs/mountlauncher.log
MAX_ATTEMPTS=60        # 10 minute timeout for WISPR sd_card_enable()
RETRY_INTERVAL=10      # seconds between retries

mkdir -p "$MOUNT_POINT"
mkdir -p "$(dirname "$LOG")"

echo "$(date -u): Waiting for WISPR SD card to be enumerated..." | tee "$LOG"

for ((i=1; i<=MAX_ATTEMPTS; i++)); do
    if [ -b "$DEVICE_P1" ] || [ -b "$DEVICE_RAW" ]; then
        echo "$(date -u): WISPR SD card found — mounting..." | tee -a "$LOG"
        if [ -b "$DEVICE_P1" ]; then
            DEVICE="$DEVICE_P1"
        else
            DEVICE="$DEVICE_RAW"
        fi
        if mount "$DEVICE" "$MOUNT_POINT" 2>>"$LOG"; then
            mkdir -p "$MOUNT_POINT/pressure_sensor/data"
            echo "$(date -u): Mounted $DEVICE at $MOUNT_POINT" | tee -a "$LOG"
            exit 0
        else
            echo "$(date -u): ERROR — mount failed" | tee -a "$LOG"
            exit 1
        fi
    fi
    echo "$(date -u): Attempt $i/$MAX_ATTEMPTS — device not found, retrying in ${RETRY_INTERVAL}s" | tee -a "$LOG"
    sleep "$RETRY_INTERVAL"
done

echo "$(date -u): ERROR — WISPR SD card not found after $MAX_ATTEMPTS attempts" | tee -a "$LOG"
exit 1
