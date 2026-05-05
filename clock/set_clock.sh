#!/bin/bash

# Reads the WISPR's RTC time from the serial port and sets the system clock.
# The WISPR firmware sends a "WTM,<epoch>" message ~45 seconds after boot
# and then every 5 minutes. This script processes each message as it arrives.

SERIAL_PORT=/dev/serial0

# Configure the serial port to match WISPR COM_BAUDRATE (9600 8N1, no flow control)
stty -F "$SERIAL_PORT" 9600 cs8 -cstopb -parenb -crtscts

while IFS= read -r line; do
    epoch=$(echo "$line" | grep -oP '(?<=WTM,)\d+')
    if [ -n "$epoch" ]; then
        date -s "@$epoch"
        echo "$(date -u): RPi clock set to epoch $epoch" | systemd-cat -t wispr-set-clock
    fi
done < "$SERIAL_PORT"
