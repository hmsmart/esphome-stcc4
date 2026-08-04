#pragma once

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/sensirion_common/i2c_sensirion.h"

namespace esphome {
namespace stcc4 {

enum MeasurementMode : uint8_t {
  CONTINUOUS,
  SINGLE_SHOT,
};

class STCC4Component : public PollingComponent, public sensirion_common::SensirionI2CDevice {
 public:
  void setup() override;
  void dump_config() override;
  void update() override;

  void set_co2_sensor(sensor::Sensor *co2) { this->co2_sensor_ = co2; }
  void set_temperature_sensor(sensor::Sensor *temperature) { this->temperature_sensor_ = temperature; }
  void set_humidity_sensor(sensor::Sensor *humidity) { this->humidity_sensor_ = humidity; }
  void set_temperature_source(sensor::Sensor *temperature) { this->temperature_source_ = temperature; }
  void set_humidity_source(sensor::Sensor *humidity) { this->humidity_source_ = humidity; }
  void set_ambient_pressure_compensation(float pressure_in_hpa);
  void set_ambient_pressure_source(sensor::Sensor *pressure) { this->ambient_pressure_source_ = pressure; }
  void set_measurement_mode(MeasurementMode mode) { this->measurement_mode_ = mode; }

 protected:
  bool update_rht_compensation_();
  bool update_ambient_pressure_compensation_(uint16_t pressure_in_hpa);
  void write_compensation_();
  bool start_measurement_();
  void read_measurement_();
  void attempt_read_measurement_();
  bool try_read_measurement_();
  void finish_measurement_();
  void check_measurement_stalled_();
  void restart_measurement_();

  sensor::Sensor *co2_sensor_{nullptr};
  sensor::Sensor *temperature_sensor_{nullptr};
  sensor::Sensor *humidity_sensor_{nullptr};
  sensor::Sensor *temperature_source_{nullptr};
  sensor::Sensor *humidity_source_{nullptr};
  sensor::Sensor *ambient_pressure_source_{nullptr};

  uint16_t ambient_pressure_{0};
  uint32_t last_measurement_time_{0};
  uint8_t read_retries_left_{0};
  uint8_t failed_cycles_{0};
  bool initialized_{false};
  bool restarting_{false};
  MeasurementMode measurement_mode_{CONTINUOUS};
};

}  // namespace stcc4
}  // namespace esphome
