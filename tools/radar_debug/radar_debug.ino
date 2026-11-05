// Radar debug: prints a status line every second, plus target XY when the radar reports them.
#include <Arduino.h>
#include "Seeed_Arduino_mmWave.h"
#include <HardwareSerial.h>

HardwareSerial mmWaveSerial(0);
SEEED_MR60BHA2 mmWave;

uint32_t frames = 0, targetFrames = 0;
size_t lastTargets = 0;
unsigned long lastHumanMs = 0, lastPrint = 0;
float dist = -1, breath = -1, heart = -1;

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("Radar debug starting");
  mmWave.begin(&mmWaveSerial);
}

void loop() {
  if (mmWave.update(100)) {
    frames++;
    if (mmWave.isHumanDetected()) lastHumanMs = millis();

    PeopleCounting t;
    if (mmWave.getPeopleCountingTargetInfo(t)) {
      targetFrames++;
      lastTargets = t.targets.size();
      for (size_t i = 0; i < t.targets.size(); i++) {
        Serial.printf("  T%u  x=%.2f  y=%.2f  speed=%.1f cm/s\n", (unsigned)(i + 1),
                      t.targets[i].x_point, t.targets[i].y_point,
                      t.targets[i].dop_index * RANGE_STEP);
      }
    }

    float v;
    if (mmWave.getDistance(v)) dist = v;
    if (mmWave.getBreathRate(v)) breath = v;
    if (mmWave.getHeartRate(v)) heart = v;
  }

  if (millis() - lastPrint >= 1000) {
    lastPrint = millis();
    bool human = lastHumanMs && (millis() - lastHumanMs < 3000);
    Serial.printf("[%lus] frames=%lu targetFrames=%lu targets=%u human=%s dist=%.2f breath=%.1f heart=%.1f\n",
                  millis() / 1000, frames, targetFrames, (unsigned)lastTargets,
                  human ? "YES" : "no", dist, breath, heart);
  }
}
