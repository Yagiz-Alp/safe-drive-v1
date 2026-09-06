import csv
import math
import os
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.utils import platform

from plyer import accelerometer, gps, gyroscope


class SafeDriveApp(App):
    def build(self):
        self.running = False
        self.speed = 0.0
        self.previous_speed = 0.0
        self.latitude = 0.0
        self.longitude = 0.0
        self.acceleration = (0.0, 0.0, 0.0)
        self.rotation = (0.0, 0.0, 0.0)
        self.csv_file = "safe_drive_data.csv"

        root = BoxLayout(
            orientation="vertical",
            padding=20,
            spacing=10
        )

        root.add_widget(Label(
            text="SAFE-DRIVE 🇹🇷",
            font_size="30sp",
            bold=True
        ))

        self.status_label = Label(
            text="Sistem hazır",
            font_size="18sp"
        )
        root.add_widget(self.status_label)

        self.risk_label = Label(
            text="RİSK\n0 / 100",
            font_size="30sp",
            bold=True
        )
        root.add_widget(self.risk_label)

        self.progress = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=28
        )
        root.add_widget(self.progress)

        self.gps_label = Label(text="GPS: Bekleniyor...")
        self.speed_label = Label(
            text="Hız: 0.0 km/h",
            font_size="22sp"
        )
        self.acc_label = Label(text="İvme: 0.00 m/s²")
        self.gyro_label = Label(
            text="Jiroskop: 0.00 / 0.00 / 0.00"
        )

        root.add_widget(self.gps_label)
        root.add_widget(self.speed_label)
        root.add_widget(self.acc_label)
        root.add_widget(self.gyro_label)

        self.start_button = Button(
            text="▶ SÜRÜŞÜ BAŞLAT",
            font_size="20sp",
            size_hint_y=None,
            height=60
        )
        self.start_button.bind(on_press=self.start_drive)
        root.add_widget(self.start_button)

        self.stop_button = Button(
            text="■ SÜRÜŞÜ DURDUR",
            font_size="20sp",
            size_hint_y=None,
            height=60,
            disabled=True
        )
        self.stop_button.bind(on_press=self.stop_drive)
        root.add_widget(self.stop_button)

        return root

    def create_csv(self):
        if not os.path.exists(self.csv_file):
            with open(
                self.csv_file,
                "w",
                newline="",
                encoding="utf-8"
            ) as file:
                writer = csv.writer(file)
                writer.writerow([
                    "tarih",
                    "saat",
                    "latitude",
                    "longitude",
                    "speed_kmh",
                    "risk"
                ])

    def gps_location(self, **kwargs):
        self.latitude = float(kwargs.get("lat", self.latitude))
        self.longitude = float(kwargs.get("lon", self.longitude))

        gps_speed = kwargs.get("speed")
        if gps_speed is not None:
            self.speed = float(gps_speed) * 3.6

    def calculate_risk(self):
        risk = 0

        speed_change = abs(self.speed - self.previous_speed)

        total_acceleration = math.sqrt(
            sum(value ** 2 for value in self.acceleration)
        )
        movement_acceleration = abs(total_acceleration - 9.81)

        gyro_total = sum(abs(value) for value in self.rotation)

        if self.speed > 120:
            risk += 30
        elif self.speed > 100:
            risk += 20
        elif self.speed > 80:
            risk += 10

        if speed_change > 30:
            risk += 30
        elif speed_change > 20:
            risk += 20
        elif speed_change > 10:
            risk += 10

        if movement_acceleration > 10:
            risk += 20
        elif movement_acceleration > 6:
            risk += 10

        if gyro_total > 10:
            risk += 20
        elif gyro_total > 6:
            risk += 10

        return min(risk, 100)

    def update_screen(self):
        risk = self.calculate_risk()

        self.progress.value = risk
        self.risk_label.text = f"RİSK\n{risk} / 100"
        self.speed_label.text = f"Hız: {self.speed:.1f} km/h"
        self.gps_label.text = (
            f"GPS:\n{self.latitude:.6f}, {self.longitude:.6f}"
        )

        if risk >= 70:
            self.status_label.text = "🔴 YÜKSEK RİSK"
        elif risk >= 40:
            self.status_label.text = "🟠 DİKKAT"
        else:
            self.status_label.text = "🟢 NORMAL"

        self.previous_speed = self.speed

    def save_data(self):
        now = datetime.now()

        with open(
            self.csv_file,
            "a",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow([
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                self.latitude,
                self.longitude,
                round(self.speed, 2),
                self.calculate_risk()
            ])

    def collect_data(self, _dt):
        if platform == "android":
            try:
                self.acceleration = accelerometer.acceleration
                self.rotation = gyroscope.rotation
            except Exception:
                pass

        self.update_screen()
        self.save_data()

    def start_drive(self, _button):
        self.running = True
        self.create_csv()

        self.start_button.disabled = True
        self.stop_button.disabled = False

        if platform == "android":
            try:
                gps.configure(on_location=self.gps_location)
                gps.start(minTime=1000, minDistance=1)
                accelerometer.enable()
                gyroscope.enable()
                self.status_label.text = "🟢 SÜRÜŞ TAKİBİ AKTİF"
            except Exception as error:
                self.status_label.text = f"Sensör hatası: {error}"
        else:
            self.status_label.text = (
                "Windows testi: Telefon sensörleri burada çalışmaz."
            )

        Clock.schedule_interval(self.collect_data, 1)

    def stop_drive(self, _button):
        self.running = False

        self.start_button.disabled = False
        self.stop_button.disabled = True

        Clock.unschedule(self.collect_data)
        self.status_label.text = "Sürüş kaydı durduruldu."

    def on_stop(self):
        Clock.unschedule(self.collect_data)


if __name__ == "__main__":
    SafeDriveApp().run()