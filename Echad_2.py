import streamlit as st
import requests
import time
from datetime import datetime, timedelta
import os

# --- 설정 및 데이터 로드 ---
USER_FILE = "User.txt"

def load_data():
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    return lines[0], lines[1]
        except:
            pass
    return "", ""

def save_data(name, number):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        f.write(f"{name}\n{number}")

# --- UI 구성 (PyQt6 대신 Streamlit 도구 사용) ---
st.set_page_config(page_title="SCDA 예약 매니저", layout="centered")
st.title("⚽ SCDA 예약 시스템 (Web/Mobile)")

saved_name, saved_number = load_data()

# 입력 폼
with st.form("booking_form"):
    st.subheader("1. 사용자 정보")
    name = st.text_input("신청자 이름", value=saved_name)
    number = st.text_input("전화번호", value=saved_number)
    
    st.subheader("2. 예약 설정")
    col1, col2 = st.columns(2)
    with col1:
        day_name = st.selectbox("요일", ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"])
        day_idx = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"].index(day_name)
    with col2:
        time_val = st.selectbox("시작 시간", [f"{i:02d}:00" for i in range(6, 23)], index=13) # 19:00 기본

    c1, c2, c3 = st.columns(3)
    option_2h = c1.checkbox("2시간")
    option_light = c2.checkbox("조명")
    option_wait = c3.checkbox("25일 대기 모드", value=True)
    
    # 실제 예약을 하려면 이 토글을 꺼야 합니다.
    is_test = st.toggle("테스트 모드 (실제 예약 안함)", value=True)
    
    submit = st.form_submit_button("예약 시작 (START)")

# [추가된 부분] 2. 공식 사이트 바로가기 버튼 (폼 바깥이나 아래에 배치)
st.link_button("🌐 공식 예약 페이지 열기", "http://www.scdaedeok.or.kr//rest/arenas/bookingsheet", use_container_width=True)


# --- 예약 로직 (기존 C# 로직과 동일) ---
if submit:
    save_data(name, number)
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    # 1. 대기 로직 (25일 09:59:55)
    if option_wait:
        status_text.warning("현재 대기 중입니다... (25일 09:59:55까지)")
        while True:
            now = datetime.now()
            # 25일 9시 59분 55초 조건 (서버 시간 기준임에 유의)
            if now.day == 25 and now.hour == 9 and now.minute == 59 and now.second >= 55:
                break
            # 중단 버튼이 없으므로 테스트 시 주의
            time.sleep(1)
            # 스트림릿 특성상 무한루프 시 화면 갱신을 위해 아주 짧게 멈춤
            if not st.session_state.get('is_running', True): break 
    
    status_text.info("🚀 예약을 시작합니다!")
    
    # 2. 데이터 준비
    use_light = "Y" if option_light else "N"
    start_time_str = time_val[:2]
    booking_time = start_time_str
    if option_2h:
        booking_time = f"{start_time_str},{int(start_time_str)+1}"

    now = datetime.now()
    # 다음달 1일 구하기
    next_month_start = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
    target_month = next_month_start.month
    total_money = 0
    
    url = "http://www.scdaedeok.or.kr//rest/arenas/bookingsheet"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    
    # 3. 루프 실행 (한 달치 예약)
    check_date = next_month_start
    success_count = 0
    
    for i in range(35):
        if check_date.month != target_month:
            break
        
        py_day = (check_date.weekday() + 1) % 7 # 일요일 0 기준
        if py_day == day_idx:
            # 가격 계산 로직 (C# 코드 참고)
            hour_rate = 25000 if check_date.weekday() >= 5 else 12500
            count = 2 if option_2h else 1
            current_total = (hour_rate + (10000 if option_light else 0)) * count
            
            payload = {
                "applicantName": name, "cellphone": number, "teamName": name,
                "memberCount": "14", "objectId": "SF0.1",
                "bookingDate": check_date.strftime("%Y/%m/%d"),
                "bookingTime": booking_time, "useLight": use_light,
                "amount": str(current_total)
            }

            if not is_test:
                try:
                    resp = requests.post(url, json=payload, headers=headers, timeout=5)
                    if "200" in resp.text:
                        total_money += current_total
                        success_count += 1
                except: pass
            else:
                st.write(f"📝 [테스트] {check_date.strftime('%Y/%m/%d')} 전송 데이터: {payload}")
                total_money += current_total
                success_count += 1
        
        check_date += timedelta(days=1)
        progress_bar.progress((i + 1) / 35)

    status_text.success(f"✅ 작업 완료! 성공: {success_count}건 / 총액: {total_money}원")
    st.balloons()

