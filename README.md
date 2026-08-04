# esphome-stcc4

Files taken from [PR#14037](https://github.com/esphome/esphome/pull/14037), author is @will-tm

## Features
Add support for the Sensirion STCC4 miniature CO₂ sensor based on thermal conductivity measurement.
The STCC4 features a dedicated I²C controller interface for an onboard SHT4x sensor, providing automatic temperature/humidity compensation and readings alongside CO₂ concentration. For boards without an onboard SHT4x, external RHT compensation is supported via temperature_source and humidity_source configuration options.
Implementation details aligned with the official Sensirion embedded driver.

## Supported Microcontrollers

Tested with:
- ESP32 (wt32-eth01)

## Usage
### Step 1: Build a control circuit.
Connect the power supply and the I2C from the microcontroller to the sensor. Be careful, the color of the wires may differ.

### Step 2: Configure your ESPHome device with YAML
See the file `example_stcc4.yaml`

## Choosing an update interval

**Continuous mode: use 5s or higher.** Avoid `update_interval: 1s`.

In continuous mode the sensor samples on its own 1 s schedule, with an effective interval of
1000 ms ± 150 ms (datasheet §3.4.1), and holds the most recent result until it is read out. Polling
at 1 s puts the ESP clock and the sensor clock into a phase fight: a read that lands early is NACKed
("no measurement data available", §3.4.3), and the retry that eventually succeeds 150 ms later
empties the buffer 150 ms *after* the poll that requested it. The next poll then fires only 850 ms
after that read and is early again — permanently. Readings still arrive, but every one of them costs
two failed reads first.

At 5 s or above, every poll finds data waiting and succeeds on the first attempt. This costs you
nothing in signal quality: CO₂ response time is τ63% = 20 s (datasheet Table 1), so 1 s polling only
resamples the same 20-second-smoothed value more often.

### Recovery from a stalled measurement

A sensor in continuous mode can stop measuring without the component being told — a brownout, or an
I²C general call reset issued by another device on the bus, which every device that honours general
call will act on (datasheet §3.4.10). The sensor then sits in idle, acknowledging its address but
NACKing every read, and no amount of retrying will produce data.

After **three consecutive update cycles** fail outright, the component stops the measurement, waits
out the 1200 ms execution time (§3.4.2) and starts it again, logging a warning when it does. Because
the trigger is counted in cycles rather than seconds, recovery takes three update intervals — fast
at 5 s, slow if you poll rarely.

It waits for three cycles rather than reacting to the first on purpose. Restarting a measurement
reinitializes the bypass phase and the timer for the first ASC state save whenever the sensor is
within its first hour of operation (§1.1.4), so a flaky bus that restarted the measurement every
cycle would pin the sensor at its 390 ppm bypass output and prevent it ever calibrating — a quieter
and worse failure than the one being recovered from.

**Single shot mode: use between 5s and 600s.** The automatic self-calibration algorithm assumes a
sampling interval in this range (datasheet §3.4.6); intervals outside it degrade calibration over
time. 10 s is the datasheet's reference figure for the specified accuracy and average current.

In single shot mode the sensor is held in sleep mode between measurements and woken only for the
~700 ms it takes to measure and read out, following the sequence in datasheet §3.4.6. Sleep draws
1 µA against 55 µA for idle and 950 µA for continuous mode (datasheet Table 3), so a longer update
interval directly buys battery life. Compensation values and calibration state survive sleep
(§3.4.7) and are not re-sent on each wake.

### On-demand measurements

`update_interval: never` is accepted in single shot mode. It disables automatic polling and leaves
the sensor asleep until something triggers a measurement explicitly:

```yaml
binary_sensor:
  - platform: gpio
    pin: GPIO0
    on_press:
      - component.update: my_stcc4
```

The 5s–600s bound is not enforced at validation time in this case, because the real sampling
cadence lives in your automation rather than in the config. It still applies: if you trigger
measurements further apart than 600 s, self-calibration degrades exactly as it would with a
too-long update interval. The component measures the gap between single shot measurements at
runtime and logs a warning when it exceeds 600 s, so this shows up in the log rather than silently
in the readings weeks later.
