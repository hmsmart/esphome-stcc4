import esphome.codegen as cg
from esphome.components import i2c, sensirion_common, sensor
import esphome.config_validation as cv
from esphome.const import (
    CONF_AMBIENT_PRESSURE_COMPENSATION,
    CONF_AMBIENT_PRESSURE_COMPENSATION_SOURCE,
    CONF_CO2,
    CONF_HUMIDITY,
    CONF_ID,
    CONF_MEASUREMENT_MODE,
    CONF_TEMPERATURE,
    CONF_TEMPERATURE_SOURCE,
    CONF_UPDATE_INTERVAL,
    DEVICE_CLASS_CARBON_DIOXIDE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    ICON_MOLECULE_CO2,
    ICON_THERMOMETER,
    ICON_WATER_PERCENT,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_PARTS_PER_MILLION,
    UNIT_PERCENT,
)

CODEOWNERS = ["@will-tm"]
DEPENDENCIES = ["i2c"]
AUTO_LOAD = ["sensirion_common"]

stcc4_ns = cg.esphome_ns.namespace("stcc4")
STCC4Component = stcc4_ns.class_(
    "STCC4Component", cg.PollingComponent, sensirion_common.SensirionI2CDevice
)

MeasurementMode = stcc4_ns.enum("MeasurementMode")
CONF_HUMIDITY_SOURCE = "humidity_source"

MEASUREMENT_MODE_OPTIONS = {
    "continuous": MeasurementMode.CONTINUOUS,
    "single_shot": MeasurementMode.SINGLE_SHOT,
}

# Datasheet 3.4.6 step 6: single shot mode expects a sampling interval between 5s and 600s
SINGLE_SHOT_MIN_INTERVAL_MS = 5_000
SINGLE_SHOT_MAX_INTERVAL_MS = 600_000

# "never" disables automatic polling entirely; measurements are then driven by the component.update
# action. Resolved from the validator rather than hardcoded so it tracks the sentinel ESPHome uses.
NEVER_INTERVAL_MS = cv.update_interval("never").total_milliseconds


def _validate_single_shot_interval(config):
    """Bound update_interval in single shot mode.

    Outside the 5s-600s window the automatic self-calibration algorithm degrades. That failure is
    silent and takes days to become visible in the readings, so it is worth rejecting at validation
    time rather than letting it run. Continuous mode is unconstrained: it drives its own 1s
    sampling and update_interval only controls how often the buffered result is read out.
    """
    if config[CONF_MEASUREMENT_MODE] != "single_shot":
        return config

    interval_ms = config[CONF_UPDATE_INTERVAL].total_milliseconds
    if interval_ms == NEVER_INTERVAL_MS:
        # Automatic polling is off and measurements come from the component.update action, so the
        # real sampling cadence lives in the user's automation and cannot be checked here. The
        # datasheet constraint still applies to how often they actually trigger it.
        return config

    if not SINGLE_SHOT_MIN_INTERVAL_MS <= interval_ms <= SINGLE_SHOT_MAX_INTERVAL_MS:
        raise cv.Invalid(
            f"update_interval must be between 5s and 600s in single_shot measurement mode, "
            f"got {interval_ms / 1000:g}s. The sensor's automatic self-calibration assumes a "
            f"sampling interval in this range (datasheet 3.4.6).",
            path=[CONF_UPDATE_INTERVAL],
        )
    return config

CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(STCC4Component),
            cv.Optional(CONF_CO2): sensor.sensor_schema(
                unit_of_measurement=UNIT_PARTS_PER_MILLION,
                icon=ICON_MOLECULE_CO2,
                accuracy_decimals=0,
                device_class=DEVICE_CLASS_CARBON_DIOXIDE,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_TEMPERATURE): sensor.sensor_schema(
                unit_of_measurement=UNIT_CELSIUS,
                icon=ICON_THERMOMETER,
                accuracy_decimals=2,
                device_class=DEVICE_CLASS_TEMPERATURE,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_HUMIDITY): sensor.sensor_schema(
                unit_of_measurement=UNIT_PERCENT,
                icon=ICON_WATER_PERCENT,
                accuracy_decimals=2,
                device_class=DEVICE_CLASS_HUMIDITY,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
            cv.Optional(CONF_TEMPERATURE_SOURCE): cv.use_id(sensor.Sensor),
            cv.Optional(CONF_HUMIDITY_SOURCE): cv.use_id(sensor.Sensor),
            # Range the sensor accepts, in hPa (datasheet 3.4.5: 40'000 - 110'000 Pa). cv.pressure
            # alone does not range check, so an out-of-range value would reach the uint16_t cast in
            # set_ambient_pressure_compensation() unvalidated.
            cv.Optional(CONF_AMBIENT_PRESSURE_COMPENSATION): cv.All(
                cv.pressure, cv.Range(min=400, max=1100)
            ),
            cv.Optional(CONF_AMBIENT_PRESSURE_COMPENSATION_SOURCE): cv.use_id(
                sensor.Sensor
            ),
            cv.Optional(CONF_MEASUREMENT_MODE, default="continuous"): cv.enum(
                MEASUREMENT_MODE_OPTIONS, lower=True
            ),
        }
    )
    .extend(cv.polling_component_schema("60s"))
    .extend(i2c.i2c_device_schema(0x64)),
    _validate_single_shot_interval,
)

SENSOR_MAP = {
    CONF_CO2: "set_co2_sensor",
    CONF_TEMPERATURE: "set_temperature_sensor",
    CONF_HUMIDITY: "set_humidity_sensor",
}


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await i2c.register_i2c_device(var, config)

    for key, func_name in SENSOR_MAP.items():
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(getattr(var, func_name)(sens))

    if CONF_TEMPERATURE_SOURCE in config:
        sens = await cg.get_variable(config[CONF_TEMPERATURE_SOURCE])
        cg.add(var.set_temperature_source(sens))

    if CONF_HUMIDITY_SOURCE in config:
        sens = await cg.get_variable(config[CONF_HUMIDITY_SOURCE])
        cg.add(var.set_humidity_source(sens))

    if CONF_AMBIENT_PRESSURE_COMPENSATION in config:
        cg.add(
            var.set_ambient_pressure_compensation(
                config[CONF_AMBIENT_PRESSURE_COMPENSATION]
            )
        )

    if CONF_AMBIENT_PRESSURE_COMPENSATION_SOURCE in config:
        sens = await cg.get_variable(config[CONF_AMBIENT_PRESSURE_COMPENSATION_SOURCE])
        cg.add(var.set_ambient_pressure_source(sens))

    cg.add(var.set_measurement_mode(config[CONF_MEASUREMENT_MODE]))
