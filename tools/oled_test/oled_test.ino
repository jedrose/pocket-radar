// OLED test: checks the screen on the MR60BHA2 kit's Grove port, with an fps counter
// Hardware: Grove 1.12" SH1107 OLED V3.0 (128x128) -> kit Grove port (D0, D10)
// Driver: U8g2, hardware I2C at 400 kHz
//
// If the screen stays blank but Serial is printing fps,
// swap the two pin numbers below and re-upload.

#include <Arduino.h>
#include <U8g2lib.h>

#define OLED_SCL D0
#define OLED_SDA D10

// SH1107 128x128 driver over the ESP32's hardware I2C, on the Grove pins
U8G2_SH1107_SEEED_128X128_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, OLED_SCL, OLED_SDA);

// Radar geometry: semicircle centered at bottom middle of the 128x128 screen
const int CX = 64;
const int CY = 124;
const int R  = 60;

float sweepDeg = 0;
float sweepStep = 3;  // degrees per frame

unsigned long lastFpsTime = 0;
int frames = 0;
int fps = 0;

void setup() {
  Serial.begin(115200);
  u8g2.setBusClock(400000);  // 400 kHz fast-mode I2C
  u8g2.begin();
  u8g2.setFont(u8g2_font_6x10_tf);
  Serial.println("OLED test starting");
}

void loop() {
  u8g2.clearBuffer();

  // Header: status on the left, frame rate on the right
  u8g2.drawStr(0, 9, "OLED OK");
  char buf[12];
  snprintf(buf, sizeof(buf), "%d fps", fps);
  u8g2.drawStr(128 - u8g2.getStrWidth(buf), 9, buf);

  // Range rings (top half only) and baseline
  const uint8_t upper = U8G2_DRAW_UPPER_LEFT | U8G2_DRAW_UPPER_RIGHT;
  u8g2.drawCircle(CX, CY, R, upper);
  u8g2.drawCircle(CX, CY, R * 2 / 3, upper);
  u8g2.drawCircle(CX, CY, R / 3, upper);
  u8g2.drawHLine(CX - R, CY, 2 * R + 1);

  // Sweep line
  float rad = sweepDeg * PI / 180.0;
  int x = CX + (int)(R * cos(rad));
  int y = CY - (int)(R * sin(rad));
  u8g2.drawLine(CX, CY, x, y);

  u8g2.sendBuffer();

  // Bounce the sweep back and forth across 0-180 degrees
  sweepDeg += sweepStep;
  if (sweepDeg >= 180 || sweepDeg <= 0) sweepStep = -sweepStep;

  // Frame rate, once per second
  frames++;
  if (millis() - lastFpsTime >= 1000) {
    fps = frames;
    frames = 0;
    lastFpsTime = millis();
    Serial.printf("fps: %d\n", fps);
  }
}
