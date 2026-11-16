import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz
from github import Github

st.set_page_config(page_title="통합 게임 숙제 매니저", page_icon="🎮", layout="wide")

KST = pytz.timezone('Asia/Seoul')
DATA_FILE = "loa_data.json"

# 사진 속 25개 서버 초기 세팅
DEFAULT_SERVERS = [
    ("1번계정", "아브 3"), ("1번계정", "카마인 5"),
    ("2번계정", "x 아브 3"), ("2번계정", "루페온 3"),
    ("3번계정", "아브 8"), ("3번계정", "루페온"),
    ("4번계정", "아브 12"),
    ("5번계정", "아브"), ("5번계정", "카제"), ("5번계정", "니나브 3"), ("5번계정", "실리안"), ("5번계정", "카단"), ("5번계정", "루페온 9"), ("5번계정", "아만 -스"),
    ("6번계정", "x 아브"), ("6번계정", "아만 1"), ("6번계정", "루페온"),
    ("7번계정", "x 아브 9"), ("7번계정", "실리안"), ("7번계정", "루페온 4"), ("7번계정", "카제"),
    ("8번계정", "x 아브 7"), ("8번계정", "실리안"), ("8번계정", "루페온 5"), ("8번계정", "카마인")
]

# 최근 주간 초기화 시점 계산 (기본값: 목요일 오전 6시 기준 / 수요일로 바꾸려면 3을 2로 변경)
def get_last_weekly_reset(now, reset_weekday=3): # 월:0, 화:1, 수:2, 목:3
    days_since = (now.weekday() - reset_weekday) % 7
    candidate = (now - timedelta(days=days_since)).replace(hour=6, minute=0, second=0, microsecond=0)
    if candidate > now:
        candidate -= timedelta(days=7)
    return candidate

def create_initial_data(now_str):
    rows = []
    for idx, (acc, srv) in enumerate(DEFAULT_SERVERS):
        row = {
            "id": idx,
            "계정명": acc,
            "서버": srv,
            "생활완료": False,
            "생활기록시간": "",
            "보석배": False,
            "보석배시간": "",
            "낙원": False,
            "이벤": False,
            "싱글": False,
        }
        # 6캐릭 x 3레이드 체크칸
        for c in range(1, 7):
            for r in range(1, 4):
                row[f"C{c}_R{r}"] = False
        rows.append(row)
    return {"last_reset_check": now_str, "reset_day": "목요일 06:00", "rows": rows}

# GitHub 연동 함수 (서버 재부팅 시에도 데이터 영구 보존)
def load_data():
    now = datetime.now(KST)
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(DATA_FILE)
            return json.loads(contents.decoded_content.decode("utf-8"))
        except Exception:
            return create_initial_data(now.isoformat())
    else:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return create_initial_data(now.isoformat())

def save_data(data):
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            try:
                contents = repo.get_contents(DATA_FILE)
                repo.update_file(contents.path, "Update LOA data", json_str, contents.sha)
            except Exception:
                repo.create_file(DATA_FILE, "Create LOA data", json_str)
        except Exception as e:
            st.error(f"GitHub 저장 오류: {e}")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

#시간 경과에 따른 생기 회복 & 주간 리셋 자동 처리
def process_auto_updates(data):
    now = datetime.now(KST)
    changed = False
    
    reset_weekday = 3 if data.get("reset_day", "목요일 06:00").startswith("목") else 2
    last_reset = get_last_weekly_reset(now, reset_weekday)
    last_check = datetime.fromisoformat(data["last_reset_check"])
    if last_check.tzinfo is None:
        last_check = KST.localize(last_check)

    # 1. 주간 초기화 시간이 지났으면 주간 숙제 일괄 해제
    if last_check < last_reset:
        for row in data["rows"]:
            row["보석배"] = False
            row["보석배시간"] = ""
            row["낙원"] = False
            row["이벤"] = False
            row["싱글"] = False
            for c in range(1, 7):
                for r in range(1, 4):
                    row[f"C{c}_R{r}"] = False
        data["last_reset_check"] = now.isoformat()
        changed = True

    # 2. 생활(생기 10,500) 계산: 10분당 30 회복 -> 3,500분(58시간 20분) 경과 시 풀충전 및 자동 체크 해제
    for row in data["rows"]:
        if row["생활완료"] and row["생활기록시간"]:
            done_time = datetime.fromisoformat(row["생활기록시간"])
            if done_time.tzinfo is None:
                done_time = KST.localize(done_time)
            elapsed_min = (now - done_time).total_seconds() / 60.0
            recovered = int((elapsed_min // 10) * 30)
            
            if recovered >= 10500:
                row["생활완료"] = False
                row["생활기록시간"] = ""
                changed = True
                row["생기상태"] = "🔥 10,500 풀충전!"
            else:
                rem_min = 3500 - elapsed_min
                rem_h = int(rem_min // 60)
                rem_m = int(rem_min % 60)
                done_str = done_time.strftime("%m/%d %H:%M")
                row["생기상태"] = f"⏳ {recovered:,} ({done_str} 완료 / {rem_h}시간 {rem_m}분 후 풀)"
        else:
            row["생기상태"] = "🔥 10,500 (수확 가능)"

    if changed:
        save_data(data)
    return data

# 데이터 불러오기
if "loa_data" not in st.session_state:
    st.session_state.loa_data = load_data()

st.session_state.loa_data = process_auto_updates(st.session_state.loa_data)
data = st.session_state.loa_data

# 상단 타이틀 및 게임별 탭 분리
st.title("🎮 나만의 게임 숙제 & 수익 관리 매니저")
tab_loa, tab_maple, tab_gersang = st.tabs(["⚓ 로스트아크 (25서버)", "🍁 메이플스토리", "💰 천하제일상 거상"])

with tab_loa:
    col_top1, col_top2, col_top3 = st.columns([2, 2, 1])
    with col_top1:
        st.caption("💡 **계정명/서버명**은 더블클릭해서 바로 수정 가능하며, 체크박스를 누르면 시간 기록과 저장이 자동으로 진행됩니다.")
    with col_top2:
        reset_opt = st.radio(
            "주간 초기화 기준일 설정",
            ["목요일 06:00", "수요일 06:00"],
            index=0 if data.get("reset_day", "목요일 06:00") == "목요일 06:00" else 1,
            horizontal=True
        )
        if reset_opt != data.get("reset_day"):
            data["reset_day"] = reset_opt
            save_data(data)
            st.rerun()
    with col_top3:
        if st.button("🔄 현재 시간 기준 새로고침", use_container_width=True):
            st.session_state.loa_data = process_auto_updates(data)
            st.rerun()

    # 표 형태로 데이터 준비
    df = pd.DataFrame(data["rows"])
    
    display_cols = [
        "계정명", "서버", "생활완료", "생기상태",
        "보석배", "보석배시간", "낙원", "이벤", "싱글"
    ]
    for c in range(1, 7):
        for r in range(1, 4):
            display_cols.append(f"C{c}_R{r}")

    column_config = {
        "계정명": st.column_config.TextColumn("계정명", width="small"),
        "서버": st.column_config.TextColumn("서버", width="small"),
        "생활완료": st.column_config.CheckboxColumn("🌿생활", width="small"),
        "생기상태": st.column_config.TextColumn("생기 회복 현황 (10,500 기준)", width="medium", disabled=True),
        "보석배": st.column_config.CheckboxColumn("🚢보석배", width="small"),
        "보석배시간": st.column_config.TextColumn("보석 수령일시", width="small", disabled=True),
        "낙원": st.column_config.CheckboxColumn("🏝️낙원", width="small"),
        "이벤": st.column_config.CheckboxColumn("🎁이벤", width="small"),
        "싱글": st.column_config.CheckboxColumn("🪙싱글", width="small"),
    }
    
    # 6캐릭 x 3레이드 컬럼 이름 깔끔하게 표시 (예: 1캐-1, 1캐-2, 1캐-3)
    for c in range(1, 7):
        for r in range(1, 4):
            col_key = f"C{c}_R{r}"
            column_config[col_key] = st.column_config.CheckboxColumn(f"{c}캐-{r}", width="small")

    edited_df = st.data_editor(
        df[display_cols],
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=920,
        key="loa_editor"
    )

    # 클릭/수정 감지 및 타임스탬프 자동 입력
    now = datetime.now(KST)
    changed = False
    for idx in range(len(data["rows"])):
        orig = data["rows"][idx]
        edit = edited_df.iloc[idx]

        # 1. 계정명 & 서버명 변경 감지
        if orig["계정명"] != edit["계정명"] or orig["서버"] != edit["서버"]:
            orig["계정명"] = edit["계정명"]
            orig["서버"] = edit["서버"]
            changed = True

        # 2. 생활 체크 감지 -> 현재 시간 자동 기록
        if orig["생활완료"] != edit["생활완료"]:
            orig["생활완료"] = bool(edit["생활완료"])
            if orig["생활완료"]:
                orig["생활기록시간"] = now.isoformat()
            else:
                orig["생활기록시간"] = ""
            changed = True

        # 3. 보석배 체크 감지 -> 수령 날짜/시간 자동 기록
        if orig["보석배"] != edit["보석배"]:
            orig["보석배"] = bool(edit["보석배"])
            if orig["보석배"]:
                orig["보석배시간"] = now.strftime("%m/%d %H:%M")
            else:
                orig["보석배시간"] = ""
            changed = True

        # 4. 주간 단답형 체크 및 6캐릭x3레이드 체크 감지
        for k in ["낙원", "이벤", "싱글"] + [f"C{c}_R{r}" for c in range(1, 7) for r in range(1, 4)]:
            if orig[k] != edit[k]:
                orig[k] = bool(edit[k])
                changed = True

    if changed:
        st.session_state.loa_data = process_auto_updates(data)
        save_data(st.session_state.loa_data)
        st.rerun()

with tab_maple:
    st.info("🍁 로스트아크 세팅이 완료되면 이어서 메이플스토리 화면을 구성할 공간입니다.")

with tab_gersang:
    st.info("💰 로스트아크와 메이플스토리 세팅 후 거상 화면을 구성할 공간입니다.")
