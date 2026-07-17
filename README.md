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
