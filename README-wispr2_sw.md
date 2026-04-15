# WISPR V2 Firmware

## Overview

`wispr2_sw` contains the embedded firmware and companion host-side utilities for the Wideband Intelligent Signal Processing and Recording (WISPR) V2 passive acoustic recorder platform. The code targets an Atmel SAM4S-based controller and is organized as an Atmel Studio 7 / ASF3 project set, with different application entry points for several deployed instrument variants for the CRAB buoys, PNNL drifting hydrophones, PacWave Perimeter hydrophones, Hawaii hydrophone gliders, and SD-card test builds.

From the source code, the primary role of this submodule is to:

- initialize the WISPR V2 hardware platform,
- configure clocks, GPIO, storage, timing, and serial interfaces,
- acquire synchronized acoustic data from an LTC2512-based ADC,
- optionally compute power spectral density products,
- write acquisition output to removable SD cards with timestamped headers, and
- expose command and configuration interfaces for deployment-specific control.

The firmware is built around deterministic timing. Acquisition start is synchronized to a one pulse per second (PPS) reference sourced either from the external RTC or a GPS receiver, depending on the application variant. This makes the codebase suitable for autonomous recorders where timestamp integrity, low-power operation, and robust storage rotation are more important than interactive throughput.

## Firmware Variants

The submodule includes multiple top-level application files, each representing a deployment profile rather than a completely different platform:

- `wispr_main_crab.c`: PMEL CRAB buoy application with RTC-based PPS synchronization and command/control support.
- `wispr_main_perimeter.c`: PacWave Perimeter application with a similar architecture to the CRAB build.
- `wispr_main_drifter.c`: PNNL drifter application that synchronizes startup time to GPS PPS and GPS messages.
- `wispr_hawaii_glider.c`: Hawaii glider-oriented application with similar logging and control behavior to the PNNL drifter.
- `wispr_test_sd.c`: SD card test application.
- `wispr_example1.c` and `wispr_example2.c`: smaller example applications.

Although each main program has deployment-specific differences, they share the same common subsystems in `src/` for board support, storage, acquisition, timing, communications, and data formatting.

## Functional Architecture

### Core Layers

The firmware is organized into a set of functional layers.

#### 1. Board Support and Hardware Bring-Up

Board-specific startup is implemented in the board support files:

- `board_v2.0.c/.h`
- `board_v2.1.c/.h`

These modules configure:

- system clocks and PLL,
- GPIO pin directions and default states,
- console UART availability,
- wakeup sources for low-power modes,
- reset reason reporting.

The public include `wispr.h` selects the correct board header using the `BOARD` compile-time symbol.

#### 2. Timebase and Synchronization

Timekeeping is distributed across several cooperating modules:

- `rtc_time.c/.h`: internal RTC and epoch conversions.
- `pcf2129.c/.h` and `ds3231.c/.h`: external RTC device support.
- `gps.c/.h`: GPS parsing and timing input support.
- `pps_timer.c/.h`: PPS capture and synchronization callback execution.
- `epoch.c/.h` and `rtx_time.c/.h`: time conversion and RTC helper utilities.

This layer gives the firmware a precise epoch reference and ensures data acquisition or time initialization can be aligned to a known PPS edge.

#### 3. Hydrophone Signal Acquisition 

The acquisition path is centered on the LTC2512 ADC interface:

- `ltc2512.c/.h`: ADC power-up, GPIO configuration, SSC setup, DMA/PDC buffering, trigger/pause/shutdown control.
- `daq.c/.h`: higher-level acquisition state handling, file creation, buffer reads, and SD write orchestration.

The code configures preamp gain, ADC decimation, sampling rate, and buffer sizing from the persistent WISPR configuration structure.

#### 4. Data Processing

When spectral products are enabled, the firmware uses:

- `spectrum.c/.h`
- CMSIS DSP headers and support code already present under ASF

Waveform buffers can be transformed into PSD estimates, averaged over multiple blocks, then forwarded through a deployment-specific output path such as the PMEL interface.

#### 5. Storage and File Management

Storage is managed through:

- `sd_card.c/.h`: SD card power switching, selection, mount/open/close logic, free-space queries, and configuration persistence.
- `fatfs/`: FatFs integration and disk I/O bridge.
- `wispr.c/.h`: on-media configuration and data-header serialization.

The code supports multiple SD cards, card switching, and timestamped file creation. New data files are opened automatically as files fill up or storage state changes.

#### 6. Control, Telemetry, and External Interfaces

Operational control and instrumentation are exposed through:

- `console.c/.h`: local configuration prompts and text console output.
- `com.c/.h`: framed serial command protocol with CRC checking.
- `uart_queue.c/.h`: buffered UART transport.
- `ina260.c/.h`: current and voltage monitoring.
- `i2c.c/.h`: shared I2C bus access.
- `pcf8574.c/.h`: GPIO expander interaction.
- `log.c/.h`: log-file writing for operational events.

This layer is how deployments pause, resume, sleep, reset, and report status.

## Boot and Runtime Sequence

The main application files follow a common boot sequence after processor startup.

### 1. MCU reset and C runtime startup

Microchip/ASF startup code initializes memory sections and transfers control to `main()`. The SAM4S startup template is located under `src/ASF/.../startup_sam4s.c`.

### 2. Board initialization

Each application begins by calling `board_init()`, which:

- initializes clocks,
- enables low-level board resources,
- configures GPIO defaults,
- prepares the console path, and
- records the reason for the previous reset.

This establishes the minimal execution environment for all later subsystems.

### 3. Console banner and diagnostic output

The selected main program initializes the console UART, prints build metadata, CPU/peripheral clock information, and the decoded board reset reason.

### 4. I2C and external RTC initialization

The firmware initializes the I2C bus and external RTC device. Depending on the build, this is usually `pcf2129` or `rtx` support. The code then:

- reads the current date/time,
- validates it,
- applies a fallback default when the RTC contents are invalid,
- initializes the internal RTC from that external source.

### 5. PPS timer setup and time synchronization

The firmware starts the PPS timing subsystem using either:

- RTC PPS input, or
- GPS PPS input.

It then calls `pps_timer_sync(...)` with a callback that executes on the next PPS edge. This is a key architectural step: time initialization and acquisition alignment are intentionally deferred until a known pulse boundary.

### 6. Communications and watchdog enablement

Depending on the application variant, the firmware initializes one or more UART channels for:

- console interaction,
- command/control messages,
- GPS input.

It then enables the watchdog timer. From this point onward, the main loop must continue servicing the watchdog to avoid unintended resets.

### 7. SD card discovery and configuration recovery

The firmware checks available SD cards, powers and selects cards through the board control pins, mounts the filesystem, and reads the last saved configuration block. If required, blank or newly prepared cards are initialized. The active card is then chosen based on availability and saved state.

### 8. User configuration review

Most application variants print the current WISPR configuration and offer a short timed window to modify it through the console. The configuration menu allows changes to items such as:

- instrument and location identifiers,
- sample size,
- sampling rate,
- preamp gain,
- ADC decimation,
- file duration,
- optional PSD parameters,
- RTC date/time.

The resulting configuration is saved back to SD card.

### 9. Sensor and power-monitor preparation

Before entering the main loop, the firmware initializes support devices such as the INA260 power monitor and updates runtime status fields like supply voltage and free card space.

### 10. State initialization

The application sets the initial run state and mode. Typical states include:

- `WISPR_IDLE`
- `WISPR_RUNNING`
- `WISPR_PAUSED`
- `WISPR_SLEEP_WFI`
- `WISPR_SLEEP_BACKUP`
- `WISPR_RESET`

Typical modes include:

- `WISPR_DAQ` for waveform acquisition,
- `WISPR_PSD` for spectral processing,
- combined operation in some flows.

### 11. Main runtime loop

The main loop acts as a state machine.

In `WISPR_RUNNING`:

- the code starts acquisition if the ADC is not already active,
- `daq_read_buffer()` waits for or retrieves a completed ADC buffer,
- the watchdog is reset after successful buffer acquisition,
- waveform data is written to SD card when DAQ mode is enabled,
- PSD processing is performed when PSD mode is enabled,
- the MCU sleeps between buffers using wait-for-interrupt to reduce idle power.

In `WISPR_PAUSED`:

- acquisition is stopped,
- the firmware delays in a controlled loop,
- it can return to the previous state after the configured pause interval.

In `WISPR_IDLE`:

- the system remains armed but inactive,
- the watchdog is serviced,
- the core waits in sleep until an interrupt or command occurs.

In `WISPR_SLEEP_BACKUP`:

- files are closed,
- configuration is saved,
- SD cards are unmounted or powered down,
- wakeup sources are configured,
- the system enters deep backup sleep and resumes through reset on wake.

In `WISPR_RESET`:

- UARTs are flushed,
- acquisition is stopped safely,
- a software reset is issued.

## Data Path Summary

At a functional level, the waveform logging path is:

1. Load persistent configuration.
2. Configure the LTC2512 ADC and hydrophone.
3. Arm acquisition and synchronize trigger timing to PPS.
4. Capture samples into DMA-backed SSC receive buffers.
5. Package each buffer with a compact WISPR binary header.
6. Open or rotate timestamped SD-card files as needed.
7. Prepend an ASCII metadata header to each new file.
8. Append raw waveform buffers to storage.

When PSD processing is enabled, the waveform buffer also feeds the spectrum module, which accumulates and averages FFT results before transmitting or storing the final spectrum product according to the active build.

## Configuration and Data Structures

The central shared types live in `wispr.h`.

Important structures include:

- `wispr_config_t`: persistent instrument configuration and runtime status.
- `wispr_adc_t`: acquisition parameters such as sample size, sampling rate, gain, and decimation.
- `wispr_psd_t`: FFT and averaging parameters for spectrum generation.
- `wispr_data_header_t`: compact binary header stored with each data buffer.

`wispr.c` implements serialization and parsing for configuration blocks and data headers. This makes the firmware format readable both on the device and by host-side utilities in `utils/`.

## Notes on Storage Format

The firmware uses two header layers in normal acquisition:

- a compact binary buffer header (`wispr_data_header_t`) embedded with each record buffer, and
- a human-readable ASCII file header written into the first block of each new data file.

This design supports both embedded parsing and easier offline inspection once files are copied from SD media.

## Development Context

This directory is not a generic portable firmware framework. It is a deployment-oriented embedded codebase tightly coupled to:

- the WISPR V2 hardware pinout,
- ASF/Microchip SAM4S support libraries,
- specific RTC, ADC, and power-monitor devices,
- multiple fielded deployment profiles with small behavioral differences.

If you are modifying or extending the firmware, the usual starting points are:

1. choose the relevant `wispr_*.cproj` / `*.atsln` variant,
2. inspect the corresponding main file in `src/`,
3. trace shared behavior through `wispr_config`, `daq`, `ltc2512`, `sd_card`, and `pps_timer`.
