// Pocket radar: MR60BHA2 targets on a sweeping 128x128 OLED radar,
// plus heart and breathing rate once you hold still.
// Hardware: MR60BHA2 kit (XIAO ESP32C6) + Grove 1.12" SH1107 OLED on the kit's Grove port.
#include <Arduino.h>
#include <U8g2lib.h>
#include <math.h>
#include <HardwareSerial.h>
#include "Seeed_Arduino_mmWave.h"

// ---- Display ----
#define OLED_SCL D0
#define OLED_SDA D10
U8G2_SH1107_SEEED_128X128_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, OLED_SCL, OLED_SDA);

// ---- Radar ----
HardwareSerial mmWaveSerial(0);
SEEED_MR60BHA2 mmWave;

// ---- Tuning ----
#define FLIP_X 0                        // set to 1 if dots move the opposite way you do
const float MAX_RANGE_M       = 6.0;    // outer ring
const float VITALS_RANGE_M    = 1.5;    // heart/breath only trusted inside this
const uint32_t STILL_MS       = 3000;   // hold still this long before showing vitals
const uint32_t TARGET_TIMEOUT = 1000;   // drop dots if the radar goes quiet this long

// ---- Radar geometry (semicircle at the bottom of the screen) ----
const int CX = 64, CY = 124, R = 60;
const float PX_PER_M = R / MAX_RANGE_M;

// ---- State ----
struct Dot { float x, y; bool moving; };
Dot dots[MAX_TARGET_NUM];
int dotCount = 0;
uint32_t lastTargetMs = 0, lastMoveMs = 0;
float heartBpm = 0, breathRpm = 0;
float sweepDeg = 0, sweepStep = 4;      // degrees per frame
uint32_t lastLog = 0;
char fwStr[40] = "?";                   // radar firmware version, once it reports it
uint32_t lastFwQuery = 0;

float nearestM() {
  float best = 99;
  for (int i = 0; i < dotCount; i++) best = min(best, sqrtf(dots[i].x * dots[i].x + dots[i].y * dots[i].y));
  return best;
}

bool vitalsReady() {
  return dotCount > 0 && nearestM() <= VITALS_RANGE_M &&
         millis() - lastMoveMs >= STILL_MS && heartBpm > 0;
}

void readRadar() {
  if (!mmWave.update(5)) return;        // 5 ms read window keeps the screen fast

  bool hadTargets = dotCount > 0;
  PeopleCounting info;
  if (mmWave.getPeopleCountingTargetInfo(info)) {
    dotCount = min((int)info.targets.size(), MAX_TARGET_NUM);
    for (int i = 0; i < dotCount; i++) {
      dots[i].x = info.targets[i].x_point * (FLIP_X ? -1 : 1);
      dots[i].y = info.targets[i].y_point;
      dots[i].moving = info.targets[i].dop_index != 0;
      if (dots[i].moving) lastMoveMs = millis();
    }
    if (!hadTargets && dotCount > 0) lastMoveMs = millis();  // new arrival has to settle first
    lastTargetMs = millis();
  }

  float v;
  if (mmWave.getHeartRate(v)) heartBpm = v;
  if (mmWave.getBreathRate(v)) breathRpm = v;

  FirmwareInfo fi;
  if (mmWave.getFirmwareInfo(fi)) {
    snprintf(fwStr, sizeof(fwStr), "%u.%u.%u (raw 0x%08lX)",
             fi.firmware_verson.major_version, fi.firmware_verson.sub_version,
             fi.firmware_verson.modified_version, (unsigned long)fi.value);
  }
}

void drawGrid() {
  const uint8_t upper = U8G2_DRAW_UPPER_LEFT | U8G2_DRAW_UPPER_RIGHT;
  const float ringStepM = MAX_RANGE_M / 3.0f;   // 3 evenly spaced rings, outer one at MAX_RANGE_M
  for (int i = 1; i <= 3; i++) u8g2.drawCircle(CX, CY, (int)lroundf(i * ringStepM * PX_PER_M), upper);
  u8g2.drawHLine(CX - R, CY, 2 * R + 1);

  // dotted spokes every 30 degrees
  for (int a = 30; a < 180; a += 30) {
    float c = cos(a * DEG_TO_RAD), s = sin(a * DEG_TO_RAD);
    for (int d = 6; d < R; d += 4) u8g2.drawPixel(CX + (int)(d * c), CY - (int)(d * s));
  }

  u8g2.setFont(u8g2_font_4x6_tf);
  char label[16];
  for (int i = 1; i <= 3; i++) {
    float ringM = i * ringStepM;
    snprintf(label, sizeof(label), "%dm", (int)lroundf(ringM));
    u8g2.drawStr(CX + (int)lroundf(ringM * PX_PER_M) - 9, CY - 2, label);
  }
}

void drawSweep() {
  int dir = sweepStep > 0 ? 1 : -1;
  for (int k = 0; k < 3; k++) {
    float a = sweepDeg - k * 5 * dir;     // k=0 is the beam, k=1..2 a fading trail
    if (a < 0 || a > 180) continue;
    float c = cos(a * DEG_TO_RAD), s = sin(a * DEG_TO_RAD);
    if (k == 0) {
      u8g2.drawLine(CX, CY, CX + (int)(R * c), CY - (int)(R * s));
    } else {
      for (int d = 3; d < R; d += 2 * k + 1) u8g2.drawPixel(CX + (int)(d * c), CY - (int)(d * s));
    }
  }
}

void drawDots() {
  if (millis() - lastTargetMs > TARGET_TIMEOUT) dotCount = 0;
  for (int i = 0; i < dotCount; i++) {
    float x = dots[i].x, y = max(dots[i].y, 0.0f);
    float r = sqrtf(x * x + y * y);
    bool beyond = r > MAX_RANGE_M;
    if (beyond) { x *= MAX_RANGE_M / r; y *= MAX_RANGE_M / r; }  // pin far targets to the rim

    int px = CX + (int)lroundf(x * PX_PER_M);
    int py = CY - (int)lroundf(y * PX_PER_M);
    if (beyond) u8g2.drawCircle(px, py, 2);
    else        u8g2.drawDisc(px, py, 3);

    float ang = atan2f(y, x) * RAD_TO_DEG;            // 0 = right, 90 = straight out
    if (fabsf(ang - sweepDeg) < 12) u8g2.drawCircle(px, py, 6);  // ping as the beam passes
  }
}

void drawHud() {
  char buf[24];

  // Header: target count and nearest distance
  u8g2.setFont(u8g2_font_6x10_tf);
  if (dotCount == 0) {
    u8g2.drawStr(0, 9, "SCANNING");
  } else {
    snprintf(buf, sizeof(buf), "%d TARGET%s", dotCount, dotCount > 1 ? "S" : "");
    u8g2.drawStr(0, 9, buf);
    snprintf(buf, sizeof(buf), "%.1fm", nearestM());
    u8g2.drawStr(128 - u8g2.getStrWidth(buf), 9, buf);
  }

  // Vitals
  bool ready = vitalsReady();
  u8g2.setFont(u8g2_font_5x7_tf);
  u8g2.drawStr(0, 21, "HEART bpm");
  u8g2.drawStr(70, 21, "BREATH /min");

  u8g2.setFont(u8g2_font_logisoso20_tn);
  if (ready) {
    snprintf(buf, sizeof(buf), "%d", (int)lroundf(heartBpm));
    u8g2.drawStr(0, 46, buf);
    snprintf(buf, sizeof(buf), "%d", (int)lroundf(breathRpm));
    u8g2.drawStr(70, 46, buf);
  } else {
    u8g2.drawStr(0, 46, "--");
    u8g2.drawStr(70, 46, "--");
  }

  // Hint
  const char* hint = nullptr;
  if (dotCount > 0 && !ready) hint = nearestM() > VITALS_RANGE_M ? "move within 1.5m" : "hold still...";
  if (hint) {
    u8g2.setFont(u8g2_font_5x7_tf);
    u8g2.drawStr((128 - u8g2.getStrWidth(hint)) / 2, 57, hint);
  }
}

void setup() {
  Serial.begin(115200);
  u8g2.setBusClock(400000);
  u8g2.begin();
  mmWave.begin(&mmWaveSerial);
  Serial.println("Pocket radar starting");
}

void loop() {
  readRadar();

  u8g2.clearBuffer();
  drawGrid();
  drawSweep();
  drawDots();
  drawHud();
  u8g2.sendBuffer();

  sweepDeg += sweepStep;
  if (sweepDeg >= 180 || sweepDeg <= 0) sweepStep = -sweepStep;

  // Ask the radar for its firmware version (read-only) until it answers
  if (fwStr[0] == '?' && millis() - lastFwQuery >= 2000) {
    lastFwQuery = millis();
    mmWave.send(0xFFFF);
  }

  if (millis() - lastLog >= 1000) {
    lastLog = millis();
    Serial.printf("fw=%s targets=%d still=%lus vitals=%s heart=%.0f breath=%.0f |",
                  fwStr, dotCount, (millis() - lastMoveMs) / 1000,
                  vitalsReady() ? "YES" : "no", heartBpm, breathRpm);
    for (int i = 0; i < dotCount; i++)   // x,y in meters; * = moving
      Serial.printf(" T%d(%.2f, %.2f)%s", i + 1, dots[i].x, dots[i].y, dots[i].moving ? "*" : "");
    Serial.println();
  }
}
