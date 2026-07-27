import streamlit as st
import requests
import time
import hashlib
import os
from datetime import datetime, timedelta

# --- [설정 및 파일 관리] ---
USER_FILE = "User.txt"


def load_user_data():
    """파일에서 이름과 전화번호를 로드합니다."""
    if os.path.exists(USER_FILE):
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    return lines[0], lines[1]
        except:
            pass
    return "", ""


def save_user_data(name, number):
    """파일에 이름과 전화번호를 저장합니다."""
    try:
        with open(USER_FILE, "w", encoding="utf-8") as f:
            f.write(f"{name}\n{number}")
    except:
        pass


def check_password(input_pw):

    # """입력받은 비밀번호를 해싱하여 비교합니다."""
    if not input_pw:
        return False

    if input_pw.strip() == st.secrets["password"]:
        return True
    else:
        return False

# --- [가격 정책 변수화] ---
WEEKEND_RATE = 25000
WEEKDAY_RATE = 12500
LIGHT_RATE = 10000

# --- [세션 상태 관리] ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'selected_dates' not in st.session_state:
    st.session_state.selected_dates = set()

# --- [로그인 화면] ---
if not st.session_state.authenticated:
    st.set_page_config(page_title="인증 필요", layout="centered")
    st.title("🔐 SCDA 예약 시스템 접속")

    pw_input = st.text_input("비밀번호를 입력하세요", type="password")

    if st.button("접속하기"):
        if check_password(pw_input):
            st.session_state.authenticated = True
            st.success("✅ 인증 성공!")
            st.rerun()
        else:
            st.error("❌ 비밀번호가 틀렸습니다.")

    st.stop()

# --- [여기부터 인증된 사용자 화면] ---
st.set_page_config(page_title="ECHAD 스마트 예약기", layout="wide")
st.title("⚽ ECHAD 스마트 예약 시스템")

with st.sidebar:
    st.subheader("⚙️ 설정")
    if st.button("로그아웃"):
        st.session_state.authenticated = False
        st.rerun()

# 1. 사용자 정보 입력 (파일에서 로드한 값 적용)
saved_name, saved_number = load_user_data()

with st.expander("👤 사용자 정보 설정", expanded=True):
    name = st.text_input("신청자 이름", value=saved_name, placeholder="예: 홍길동")
    number = st.text_input("전화번호", value=saved_number, placeholder="01012345678 (숫자만)")

# 2. 예약 방식 선택
st.subheader("📅 예약 방식 선택")
mode = st.radio("원하는 방식을 선택하세요", ["요일 반복 (기존)", "날짜 직접 선택 (개별 설정)"], horizontal=True)

time_options = [f"{i:02d}:00" for i in range(6, 23)]
booking_targets = []

now = datetime.now()
next_month_start = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
target_year = next_month_start.year
target_month = next_month_start.month

if mode == "요일 반복 (기존)":
    st.info(f"📅 **예약 대상 월: {target_year}년 {target_month:02d}월**")

    col1, col2 = st.columns(2)
    with col1:
        day_names = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]
        day_name = st.selectbox("반복할 요일", day_names, index=6)
        day_idx = day_names.index(day_name)
    with col2:
        common_time = st.selectbox("공통 시작 시간", time_options, index=1)

    c1, c2 = st.columns(2)
    common_2h = c1.checkbox("공통 2시간 사용", value=True)
    common_light = c2.checkbox("공통 조명 사용", value=False)

    check_date = next_month_start
    for _ in range(35):
        if check_date.month != target_month: break
        if (check_date.weekday() + 1) % 7 == day_idx:
            booking_targets.append((check_date, common_time, common_2h, common_light))
        check_date += timedelta(days=1)
    st.caption(f"💡 {target_month}월 {day_name}은 총 {len(booking_targets)}번 설정되었습니다.")

else:
    st.info("날짜를 선택하고 '날짜 추가' 버튼을 눌러주세요.")
    col_date, col_btn = st.columns([2, 1])

    with col_date:
        new_date = st.date_input("예약할 날짜 선택", value=datetime.now() + timedelta(days=1))
    with col_btn:
        st.write(" ")
        if st.button("➕ 날짜 추가"):
            st.session_state.selected_dates.add(new_date)

    if st.session_state.selected_dates:
        col_clear1, col_clear2 = st.columns([5, 1])
        with col_clear2:
            if st.button("🗑️ 전체 초기화"):
                st.session_state.selected_dates = set()
                st.rerun()

        st.write("---")
        st.markdown("🕒 **각 날짜별 상세 설정** (시간 / 2시간 / 조명)")

        sorted_dates = sorted(list(st.session_state.selected_dates))
        for d in sorted_dates:
            row_cols = st.columns([1.5, 1.5, 1, 1])
            with row_cols[0]:
                weekday_str = ['월', '화', '수', '목', '금', '토', '일'][d.weekday()]
                st.write(f"🗓️ {d.strftime('%m/%d')} ({weekday_str})")
            with row_cols[1]:
                t = st.selectbox(f"시간", time_options, index=1, key=f"time_{d}", label_visibility="collapsed")
            with row_cols[2]:
                is_2h = st.checkbox("2시간", value=True, key=f"2h_{d}")
            with row_cols[3]:
                is_light = st.checkbox("조명", value=False, key=f"light_{d}")

            booking_targets.append((d, t, is_2h, is_light))

# 3. 공통 시스템 설정
st.write("---")
c1, c2 = st.columns(2)
option_wait = c1.checkbox("🕒 25일 대기 모드 (09:59:55 타겟)", value=True)
is_test = c2.toggle("🧪 테스트 모드 (실제 예약 시 반드시 끌 것)", value=False)

submit = st.button("🚀 예약 작업 시작 (START)", use_container_width=True)
st.link_button("🌐 공식 사이트 확인", "http://www.scdaedeok.or.kr//arena_booking.html?arenaId=SF0.1", use_container_width=True)

# --- 예약 실행 로직 ---
if submit:
    # 데이터 저장 호출
    save_user_data(name, number)

    clean_number = "".join(filter(str.isdigit, number))
    if not name.strip() or len(clean_number) != 11:
        st.error("⚠️ 이름과 전화번호(11자리)를 정확히 입력해주세요.")
        st.stop()
    if not booking_targets:
        st.error("⚠️ 예약할 날짜가 선택되지 않았습니다.")
        st.stop()

    if option_wait:
        status_box = st.warning("🕒 예약 시작 시간(25일 09:59:55)까지 대기합니다...")
        while True:
            now = datetime.now()
            if now.day == 25 and now.hour == 9 and now.minute == 59 and now.second >= 55:
                break
            time.sleep(0.5)

    st.info(f"총 {len(booking_targets)}건의 예약을 시도합니다.")
    progress_bar = st.progress(0)
    success_count = 0
    total_money = 0

    #url = "http://www.scdaedeok.or.kr//rest/arenas/bookingsheet"
    #url = "https://scdaedeok.or.kr/arena_booking.html?arenaId=SF0.1"
    url = "https://scdaedeok.or.kr/rest/arenas/bookingsheet"
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

    for i, (target_date, target_time, target_2h, target_light) in enumerate(booking_targets):
        hour_start = target_time[:2]
        final_time_str = hour_start
        usage_hours = 1
        if target_2h:
            final_time_str = f"{hour_start},{int(hour_start) + 1}"
            usage_hours = 2

        is_weekend = target_date.weekday() >= 5
        base_rate = WEEKEND_RATE if is_weekend else WEEKDAY_RATE
        current_light_fee = LIGHT_RATE if target_light else 0
        current_amt = (base_rate * usage_hours) + current_light_fee

        payload = {
            "applicantName": name, "cellphone": clean_number, "teamName": name,
            "memberCount": "14", "objectId": "SF0.1",
            "bookingDate": target_date.strftime("%Y/%m/%d"),
            "bookingTime": final_time_str, "useLight": "Y" if target_light else "N",
            "amount": str(current_amt)
        }

        if not is_test:
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=5)
                if "200" in resp.text:
                    success_count += 1
                    total_money += current_amt
                else:
                    st.error(f"❌ {target_date.strftime('%m/%d')} 실패: {resp.text}")
            except:
                st.error(f"❌ {target_date.strftime('%m/%d')} 전송 오류")
        else:
            st.write(
                f"📝 [테스트] {target_date.strftime('%m/%d')} | {target_time} | {usage_hours}시간 | 조명:{target_light} | 최종금액:{current_amt}원")
            success_count += 1
            total_money += current_amt

        progress_bar.progress((i + 1) / len(booking_targets))

    st.success(f"✅ 완료! 성공: {success_count}건 / 총액: {total_money}원")
    st.balloons()

