import sys
import time
import requests
import json
import threading
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QCheckBox,
                             QPushButton, QComboBox, QMessageBox)
from PyQt6.QtCore import pyqtSignal, QObject


# 스레드 통신용 시그널
class WorkerSignals(QObject):
    status = pyqtSignal(str)
    money = pyqtSignal(str)
    finished = pyqtSignal()


class HttpBookingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ISTEST = True  # 테스트 모드 (실제 예약 시 False로 변경)
        self.initUI()
        self.load_user_data()

    def initUI(self):
        self.setWindowTitle("SCDA HTTP 예약기 (Python)")
        self.setGeometry(100, 100, 350, 450)

        layout = QVBoxLayout()

        # 이름/번호
        self.tb_name = QLineEdit()
        self.tb_number = QLineEdit()
        layout.addWidget(QLabel("신청자 이름:"))
        layout.addWidget(self.tb_name)
        layout.addWidget(QLabel("전화번호:"))
        layout.addWidget(self.tb_number)

        # 요일 (C# cb_0~cb_6 대응)
        self.cb_days = QComboBox()
        self.cb_days.addItems(["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"])
        layout.addWidget(QLabel("예약 요일:"))
        layout.addWidget(self.cb_days)

        # 시간 및 옵션
        self.cb_time = QComboBox()
        self.cb_time.addItems([f"{i:02d}:00" for i in range(6, 23)])
        layout.addWidget(QLabel("시작 시간:"))
        layout.addWidget(self.cb_time)

        self.cb_2hour = QCheckBox("2시간 사용")
        self.cb_light = QCheckBox("조명 사용")
        self.cb_waiting = QCheckBox("25일 09:59:55 대기")
        layout.addWidget(self.cb_2hour)
        layout.addWidget(self.cb_light)
        layout.addWidget(self.cb_waiting)

        # 상태 및 결과
        self.lb_status = QLabel("대기 중")
        self.lb_money = QLabel("0")
        layout.addWidget(QLabel("상태:"))
        layout.addWidget(self.lb_status)
        layout.addWidget(QLabel("예약 총액 (성공 기준):"))
        layout.addWidget(self.lb_money)

        # 버튼
        self.btn_start = QPushButton("START")
        self.btn_start.clicked.connect(self.toggle_booking)
        layout.addWidget(self.btn_start)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_user_data(self):
        try:
            with open("User.txt", "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    self.tb_name.setText(lines[0])
                    self.tb_number.setText(lines[1])
        except FileNotFoundError:
            pass


    def toggle_booking(self):
        if self.btn_start.text() == "START":
            # 파일 저장
            with open("User.txt", "w", encoding="utf-8") as f:
                f.write(f"{self.tb_name.text()}\n{self.tb_number.text()}")

            self.btn_start.setText("CANCEL")
            self.is_running = True
            self.signals = WorkerSignals()
            self.signals.status.connect(self.lb_status.setText)
            self.signals.money.connect(self.lb_money.setText)
            self.signals.finished.connect(self.on_finished)

            threading.Thread(target=self.booking_logic, daemon=True).start()
        else:
            self.is_running = False
            self.btn_start.setText("START")

    def booking_logic(self):
        # 1. 시간 대기 로직 (C# 동일)
        if self.cb_waiting.isChecked():
            self.signals.status.emit("대기 중...")
            while self.is_running:
                now = datetime.now()
                # 매달 25일 09:59:55 대기
                if now.day == 25 and now.hour == 9 and now.minute == 59 and now.second >= 55:
                    break
                time.sleep(0.5)

        if not self.is_running: return
        self.signals.status.emit("예약 중")

        # 2. 파라미터 준비
        user_name = self.tb_name.text()
        user_number = self.tb_number.text()
        use_light = "Y" if self.cb_light.isChecked() else "N"
        start_time_str = self.cb_time.currentText()[:2]  # "19:00" -> "19"

        booking_time = start_time_str
        if self.cb_2hour.isChecked():
            next_time = int(start_time_str) + 1
            booking_time = f"{start_time_str},{next_time}"

        selected_day_idx = self.cb_days.currentIndex()  # 0:일 ~ 6:토

        # 3. 날짜 설정 (다음 달 1일로 이동 후 해당 요일 찾기)
        now = datetime.now()
        # 다음 달 1일 계산
        if now.month == 12:
            next_month_start = datetime(now.year + 1, 1, 1)
        else:
            next_month_start = datetime(now.year, now.month + 1, 1)

        target_month = next_month_start.month
        total_money = 0

        # API 헤더
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        }
        url = "http://www.scdaedeok.or.kr//rest/arenas/bookingsheet"

        # 35일간 루프 돌며 요일 매칭 (C# 로직 동일)
        check_date = next_month_start
        for _ in range(35):
            if check_date.month != target_month:
                break

            # 요일 체크 (파이썬 weekday: 월=0...일=6 -> 일=0으로 변환 필요)
            py_day = (check_date.weekday() + 1) % 7

            if py_day == selected_day_idx:
                # 가격 계산
                hour_rate = 25000 if check_date.weekday() >= 5 else 12500  # 토,일은 25000
                light_rate = 10000

                count = 2 if "," in booking_time else 1
                current_total = hour_rate * count
                if use_light == "Y":
                    current_total += (light_rate * count)

                # JSON 데이터 생성
                payload = {
                    "applicantName": user_name,
                    "cellphone": user_number,
                    "teamName": user_name,
                    "memberCount": "14",
                    "objectId": "SF0.1",
                    "bookingDate": check_date.strftime("%Y/%m/%d"),
                    "bookingTime": booking_time,
                    "useLight": use_light,
                    "amount": str(current_total)
                }

                if not self.ISTEST:
                    try:
                        resp = requests.post(url, headers=headers, json=payload)
                        if "200" in resp.text:
                            total_money += current_total
                    except Exception as e:
                        print(f"Error: {e}")
                else:
                    # 테스트 모드일 때는 성공했다고 가정하고 금액만 합산
                    print(f"Test Mode - Payload: {payload}")
                    total_money += current_total

            check_date += timedelta(days=1)
            if not self.is_running: break

        self.signals.money.emit(str(total_money))
        self.signals.status.emit("완료")
        self.signals.finished.emit()

    def on_finished(self):
        self.btn_start.setText("START")
        QMessageBox.information(self, "완료", "예약 시도가 끝났습니다.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = HttpBookingApp()
    ex.show()
    sys.exit(app.exec())