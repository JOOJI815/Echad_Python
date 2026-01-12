import streamlit as st
import requests
import time
from datetime import datetime, timedelta

# --- 세션 상태 초기화 (날짜 직접 선택 모드용) ---
if 'selected_dates' not in st.session_state:
    st.session_state.selected_dates = set()

# --- UI 구성 ---
st.set_page_config(page_title="SCDA 스마트 예약기", layout="centered")
st.title("⚽ SCDA 스마트 예약 시스템")

# 1. 사용자 정보 입력 (저장/로드 기능 제거)
with st.expander("👤 사용자 정보 설정", expanded=True):
    name = st.text_input("신청자 이름", value="", placeholder="예: 홍길동")
    number = st.text_input("전화번호", value="", placeholder="01012345678 (숫자만)")

# 2. 예약 방식 선택
st.subheader("📅 예약 방식 선택")
mode = st.radio("원하는 방식을 선택하세요", ["요일 반복 (기존)", "날짜 직접 선택 (개별 설정)"], horizontal=True)

time_options = [f"{i:02d}:00" for i in range(6, 23)]
booking_targets = []

if mode == "요일 반복 (기존)":
    col1, col2 = st.columns(2)
    with col1:
        day_name = st.selectbox("반복할 요일", ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"])
        day_idx = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"].index(day_name)
    with col2:
        common_time = st.selectbox("공통 시작 시간", time_options, index=13)  # 19:00 기본

    # 다음 달 요일 계산 로직
    now = datetime.now()
    next_month_start = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
    target_month = next_month_start.month
    check_date = next_month_start
    for _ in range(35):
        if check_date.month != target_month: break
        if (check_date.weekday() + 1) % 7 == day_idx:
            booking_targets.append((check_date, common_time))
        check_date += timedelta(days=1)
    st.caption(f"💡 {day_name} 총 {len(booking_targets)}번 예약이 설정되었습니다.")

else:
    # 날짜 직접 추가 방식 (버전 호환성 높음)
    st.info("날짜를 선택하고 '날짜 추가' 버튼을 눌러주세요.")
    col_date, col_btn = st.columns([2, 1])

    with col_date:
        # 내일 날짜를 기본값으로 설정
        new_date = st.date_input("예약할 날짜 선택", value=datetime.now() + timedelta(days=1))
    with col_btn:
        st.write(" ")  # 레이아웃 정렬용
        if st.button("➕ 날짜 추가"):
            st.session_state.selected_dates.add(new_date)

    if st.session_state.selected_dates:
        col_clear1, col_clear2 = st.columns([3, 1])
        with col_clear2:
            if st.button("🗑️ 전체 초기화"):
                st.session_state.selected_dates = set()
                st.rerun()

        st.write("---")
        st.write("🕒 **각 날짜별 시작 시간 설정**")

        # 선택된 날짜 리스트 정렬 후 표시
        sorted_dates = sorted(list(st.session_state.selected_dates))
        for d in sorted_dates:
            c1, c2 = st.columns([1.2, 1])
            with c1:
                weekday_str = ['월', '화', '수', '목', '금', '토', '일'][d.weekday()]
                st.write(f"🗓️ {d.strftime('%m/%d')} ({weekday_str})")
            with c2:
                # 개별 날짜마다 독립적인 시간 선택 가능
                t = st.selectbox(f"시간", time_options, index=13, key=f"time_{d}", label_visibility="collapsed")
                booking_targets.append((d, t))

# 3. 공통 옵션 설정
st.write("---")
c1, c2, c3 = st.columns(3)
option_2h = c1.checkbox("2시간 사용", value=True)
option_light = c2.checkbox("조명 사용")
option_wait = c3.checkbox("25일 대기 모드")

is_test = st.toggle("테스트 모드 (실제 예약 시 반드시 끌 것)", value=True)

# 시작 버튼
submit = st.button("🚀 예약 작업 시작 (START)", use_container_width=True)
st.link_button("🌐 공식 사이트 확인", "http://www.scdaedeok.or.kr//arena_booking.html?arenaId=SF0.1", use_container_width=True)

# --- 예약 실행 로직 ---
if submit:
    # 1. 유효성 검사
    clean_number = "".join(filter(str.isdigit, number))
    if not name.strip():
        st.error("⚠️ 신청자 이름을 입력해주세요.")
        st.stop()
    if len(clean_number) != 11:
        st.error("⚠️ 전화번호 11자리를 정확히 입력해주세요.")
        st.stop()
    if not booking_targets:
        st.error("⚠️ 예약할 날짜가 선택되지 않았습니다.")
        st.stop()

    # 2. 대기 로직 (25일 아침 09:59:55)
    if option_wait:
        status_box = st.warning("🕒 예약 시작 시간(25일 09:59:55)까지 대기합니다...")
        while True:
            now = datetime.now()
            if now.day == 25 and now.hour == 9 and now.minute == 59 and now.second >= 55:
                break
            time.sleep(0.5)

    # 3. 예약 전송 실행
    st.info(f"총 {len(booking_targets)}건의 예약을 시도합니다.")
    progress_bar = st.progress(0)
    success_count = 0
    total_money = 0

    url = "http://www.scdaedeok.or.kr//rest/arenas/bookingsheet"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }

    for i, (target_date, target_time) in enumerate(booking_targets):
        # 시간 가공 (2시간 설정 포함)
        hour_start = target_time[:2]
        final_time_str = hour_start
        if option_2h:
            final_time_str = f"{hour_start},{int(hour_start) + 1}"

        # 주말 여부에 따른 가격 계산
        is_weekend = target_date.weekday() >= 5  # 5:토, 6:일
        base_rate = 25000 if is_weekend else 12500
        usage_count = 2 if option_2h else 1

        current_amt = (base_rate + (10000 if option_light else 0)) * usage_count

        # 전송 데이터(Payload) 구성
        payload = {
            "applicantName": name,
            "cellphone": clean_number,
            "teamName": name,
            "memberCount": "14",
            "objectId": "SF0.1",
            "bookingDate": target_date.strftime("%Y/%m/%d"),
            "bookingTime": final_time_str,
            "useLight": "Y" if option_light else "N",
            "amount": str(current_amt)
        }

        if not is_test:
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=5)
                if "200" in resp.text:
                    success_count += 1
                    total_money += current_amt
            except Exception as e:
                st.error(f"❌ {target_date.strftime('%m/%d')} 전송 중 오류 발생")
        else:
            # 테스트 모드 시 로그 출력
            st.write(f"📝 [테스트] {target_date.strftime('%Y/%m/%d')} / {target_time} / {current_amt}원 데이터 확인")
            success_count += 1
            total_money += current_amt

        progress_bar.progress((i + 1) / len(booking_targets))

    st.success(f"✅ 모든 작업 완료! 성공: {success_count}건 / 총액: {total_money}원")
    st.balloons()

