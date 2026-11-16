import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz
from github import Github

st.set_page_config(page_title="통합 게임 숙제 & 타임 매니저", page_icon="🎮", layout="wide")

KST = pytz.timezone('Asia/Seoul')
DATA_FILE = "loa_data_v3.json"

# 25개 서버 초기 세팅
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

RAID_OPTIONS = ["➖", "1/3", "2/3", "✅3/3", "🔧계승중"]
TRUST_OPTIONS = ["🟡작업중", "🟢안전", "🔴부족"]

# ⏱️ 끊기지 않는 게임별 타이머 & 알람 위젯
def render_game_timer(game_key, game_name, default_min=60):
    end_key = f"timer_end_{game_key}"
    run_key = f"timer_run_{game_key}"
    
    if end_key not in st.session_state:
        st.session_state[end_key] = None
    if run_key not in st.session_state:
        st.session_state[run_key] = False

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 2.5])
        with c1:
            mins = st.number_input(f"⏱️ {game_name} 목표 시간(분)", min_value=1, max_value=300, value=default_min, step=5, key=f"in_{game_key}")
        with c2:
            st.write("")
            if st.button("▶️ 타이머 시작", key=f"start_{game_key}", use_container_width=True):
                st.session_state[end_key] = datetime.now(KST).timestamp() * 1000 + int(mins * 60 * 1000)
                st.session_state[run_key] = True
                st.rerun()
        with c3:
            st.write("")
            if st.button("⏹️ 정지/초기화", key=f"stop_{game_key}", use_container_width=True):
                st.session_state[run_key] = False
                st.session_state[end_key] = None
                st.rerun()
        with c4:
            if st.session_state[run_key] and st.session_state[end_key]:
                target_ms = st.session_state[end_key]
                html_code = f"""
                <div id="box_{game_key}" style="font-family:sans-serif; font-size:20px; font-weight:bold; padding:10px; border-radius:8px; background:#1E293B; color:#38BDF8; text-align:center; border:2px solid #38BDF8;">
                    ⏳ 남은 시간 계산 중...
                </div>
                <script>
                const target = {target_ms};
                const el = document.getElementById("box_{game_key}");
                let beeped = false;
                function playAlarm() {{
                    try {{
                        const ctx = new (window.AudioContext || window.webkitAudioContext)();
                        for(let i=0; i<3; i++) {{
                            const osc = ctx.createOscillator();
                            const gain = ctx.createGain();
                            osc.type = 'sine';
                            osc.frequency.setValueAtTime(880, ctx.currentTime + i*0.4);
                            gain.gain.setValueAtTime(0.2, ctx.currentTime + i*0.4);
                            osc.connect(gain);
                            gain.connect(ctx.destination);
                            osc.start(ctx.currentTime + i*0.4);
                            osc.stop(ctx.currentTime + i*0.4 + 0.25);
                        }}
                    }} catch(e) {{}}
                }}
                const timer = setInterval(() => {{
                    const diff = target - Date.now();
                    if (diff <= 0) {{
                        clearInterval(timer);
                        el.style.background = "#991B1B";
                        el.style.color = "#FFFFFF";
                        el.style.borderColor = "#F87171";
                        el.innerHTML = "🔔 목표 시간 종료! 미련 없이 다음 게임으로 넘어가세요!";
                        if (!beeped) {{ playAlarm(); beeped = true; }}
                    }} else {{
                        const h = Math.floor(diff / 3600000);
                        const m = Math.floor((diff % 3600000) / 60000);
                        const s = Math.floor((diff % 60000) / 1000);
                        const hStr = h > 0 ? String(h).padStart(2,'0') + ':' : '';
                        el.innerHTML = "🔥 남은 시간: " + hStr + String(m).padStart(2,'0') + ":" + String(s).padStart(2,'0');
                    }}
                }}, 500);
                </script>
                """
                components.html(html_code, height=55)
            else:
                st.info("👆 오늘 이 게임에 투자할 시간을 정하고 **[▶️ 타이머 시작]**을 누르세요.")

# 오전 6시 기준 로아 '게임 날짜' 계산 함수 (카던 휴게 자동 회복용)
def get_loa_day(dt):
    if dt.tzinfo is None:
        dt = KST.localize(dt)
    return (dt - timedelta(hours=6)).date()

def get_last_weekly_reset(now, reset_weekday=3):
    days_since = (now.weekday() - reset_weekday) % 7
    candidate = (now - timedelta(days=days_since)).replace(hour=6, minute=0, second=0, microsecond=0)
    if candidate > now:
        candidate -= timedelta(days=7)
    return candidate

# 카던 휴게 표시 문자열 생성
def format_cd_display(pts, run_str, now):
    if pts < 0:
        return "➖(제외)"
    bars = pts // 20
    half = ".5" if (pts % 20 >= 10) else ""
    
    # 오늘(오전 6시 이후) 돌았는지 확인
    ran_today = False
    short_date = ""
    if run_str:
        try:
            rt = datetime.fromisoformat(run_str)
            if rt.tzinfo is None:
                rt = KST.localize(rt)
            short_date = rt.strftime("%m/%d")
            if get_loa_day(rt) == get_loa_day(now):
                ran_today = True
        except Exception:
            pass

    if ran_today:
        return f"✅{bars}{half}칸 ({short_date}완료)"
    if bars >= 5:
        return "🔥5칸(풀)" if not short_date else f"🔥5칸 ({short_date})"
    if bars >= 3:
        return f"🟡{bars}{half}칸" + (f" ({short_date})" if short_date else "")
    return f"⚪{bars}{half}칸" + (f" ({short_date})" if short_date else "")

def create_initial_data(now_str):
    now = datetime.fromisoformat(now_str)
    rows = []
    for idx, (acc, srv) in enumerate(DEFAULT_SERVERS):
        row = {
            "id": idx,
            "계정명": acc,
            "서버": srv,
            "신뢰도": "🟡작업중",
            "생활완료": False,
            "생활기록시간": "",
            "생기수치": 10500,
            "생기상태": "🔥 10,500 (수확 가능)",
            "보석배": False,
            "보석배시간": "",
            "낙원": False,
            "이벤": False,
            "싱글": False,
            "카던큐브": "",
            "보석메모": "",
        }
        for c in range(1, 7):
            row[f"CD{c}_pts"] = 100 # 초기값: 한참 쉬었으므로 전원 5칸(100점) 세팅
            row[f"CD{c}_upd"] = now_str
            row[f"CD{c}_run"] = ""
            row[f"CD{c}"] = format_cd_display(100, "", now)
            row[f"C{c}"] = "➖"
        rows.append(row)
    return {"last_reset_check": now_str, "reset_day": "목요일 06:00", "rows": rows}

def ensure_schema(data):
    now = datetime.now(KST)
    now_str = now.isoformat()
    if not isinstance(data, dict) or "rows" not in data:
        return create_initial_data(now_str)
    data.setdefault("last_reset_check", now_str)
    data.setdefault("reset_day", "목요일 06:00")
    for idx, row in enumerate(data.get("rows", [])):
        row.setdefault("id", idx)
        row.setdefault("계정명", f"{idx+1}번")
        row.setdefault("서버", "서버")
        row.setdefault("신뢰도", "🟡작업중")
        row.setdefault("생활완료", False)
        row.setdefault("생활기록시간", "")
        row.setdefault("생기수치", 10500)
        row.setdefault("생기상태", "🔥 10,500 (수확 가능)")
        row.setdefault("보석배", False)
        row.setdefault("보석배시간", "")
        row.setdefault("낙원", False)
        row.setdefault("이벤", False)
        row.setdefault("싱글", False)
        row.setdefault("카던큐브", "")
        row.setdefault("보석메모", "")
        for c in range(1, 7):
            row.setdefault(f"CD{c}_pts", 100) # 기본 5칸(100점)
            row.setdefault(f"CD{c}_upd", now_str)
            row.setdefault(f"CD{c}_run", "")
            row.setdefault(f"CD{c}", format_cd_display(row[f"CD{c}_pts"], row[f"CD{c}_run"], now))
            row.setdefault(f"C{c}", "➖")
    return data

def load_data():
    now = datetime.now(KST)
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(DATA_FILE)
            data = json.loads(contents.decoded_content.decode("utf-8"))
            return ensure_schema(data)
        except Exception:
            return create_initial_data(now.isoformat())
    else:
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return ensure_schema(json.load(f))
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
                repo.update_file(contents.path, "Update LOA v3 data", json_str, contents.sha)
            except Exception:
                repo.create_file(DATA_FILE, "Create LOA v3 data", json_str)
        except Exception as e:
            st.error(f"GitHub 저장 오류: {e}")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        f.write(json_str)

def process_auto_updates(data):
    data = ensure_schema(data)
    now = datetime.now(KST)
    changed = False
    
    reset_weekday = 3 if data.get("reset_day", "목요일 06:00").startswith("목") else 2
    last_reset = get_last_weekly_reset(now, reset_weekday)
    last_check = datetime.fromisoformat(data["last_reset_check"])
    if last_check.tzinfo is None:
        last_check = KST.localize(last_check)

    # 1. 주간 초기화 (생활, 카던 휴식게이지, 신뢰도, 메모는 주간 초기화에서 제외!)
    if last_check < last_reset:
        for row in data["rows"]:
            row["보석배"] = False
            row["보석배시간"] = ""
            row["낙원"] = False
            row["이벤"] = False
            row["싱글"] = False
            for c in range(1, 7):
                row[f"C{c}"] = "➖"
        data["last_reset_check"] = now.isoformat()
        changed = True

    # 2. 생활(생기 10,500) 실시간 회복 계산
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
                row["생기수치"] = 10500
                changed = True
                row["생기상태"] = "🔥 10,500 풀충전!"
            else:
                row["생기수치"] = recovered
                rem_min = 3500 - elapsed_min
                rem_h = int(rem_min // 60)
                rem_m = int(rem_min % 60)
                done_str = done_time.strftime("%m/%d %H:%M")
                row["생기상태"] = f"⏳ {recovered:,} ({done_str} / {rem_h}h {rem_m}m 남음)"
        else:
            row["생기수치"] = 10500
            row["생기상태"] = "🔥 10,500 (수확 가능)"

        # 3. 카던 휴식게이지 자동 회복 (오전 6시 기준 하루 지날 때마다 +10점 = 0.5칸 회복)
        for c in range(1, 7):
            pts = row.get(f"CD{c}_pts", 100)
            if pts >= 0:
                upd_str = row.get(f"CD{c}_upd", now.isoformat())
                try:
                    upd_dt = datetime.fromisoformat(upd_str)
                except Exception:
                    upd_dt = now
                days_passed = (get_loa_day(now) - get_loa_day(upd_dt)).days
                if days_passed > 0:
                    new_pts = min(100, pts + days_passed * 10)
                    if new_pts != pts:
                        changed = True
                    row[f"CD{c}_pts"] = new_pts
                    row[f"CD{c}_upd"] = now.isoformat()
            
            new_disp = format_cd_display(row[f"CD{c}_pts"], row.get(f"CD{c}_run", ""), now)
            if row.get(f"CD{c}") != new_disp:
                row[f"CD{c}"] = new_disp

    if changed:
        save_data(data)
    return data

if "loa_data_v3" not in st.session_state:
    st.session_state.loa_data_v3 = load_data()

st.session_state.loa_data_v3 = process_auto_updates(st.session_state.loa_data_v3)
data = st.session_state.loa_data_v3

st.title("🎮 나만의 게임 숙제 & 수익 관리 매니저")
tab_loa, tab_maple, tab_gersang = st.tabs(["⚓ 로스트아크 (25서버)", "🍁 메이플스토리", "💰 천하제일상 거상"])

with tab_loa:
    render_game_timer("loa", "로스트아크", default_min=45)

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.8, 1.5, 1.8, 1])
    with col_f1:
        only_todo = st.checkbox("🔥 할 일 남음(생기 풀 / 보석배 미수령)만 보기", value=False)
    with col_f2:
        sort_urgent = st.checkbox("⚡ 생기 많이 찬 서버 맨 위로 정렬", value=False)
    with col_f3:
        reset_opt = st.radio(
            "주간 리셋 기준",
            ["목요일 06:00", "수요일 06:00"],
            index=0 if data.get("reset_day", "목요일 06:00") == "목요일 06:00" else 1,
            horizontal=True,
            label_visibility="collapsed"
        )
        if reset_opt != data.get("reset_day"):
            data["reset_day"] = reset_opt
            save_data(data)
            st.rerun()
    with col_f4:
        if st.button("🔄 생기/휴게 새로고침", use_container_width=True):
            st.session_state.loa_data_v3 = process_auto_updates(data)
            st.rerun()

    st.caption("💡 **카던 휴게 사용법:** 캐릭터별 `🌀1카~6카` 칸을 더블클릭해서 **`⚡오늘돌았음(-1칸)`**을 선택하면 자동으로 1칸이 까이고 오늘 날짜가 기록됩니다! (안 돌면 이틀마다 1칸씩 자동 회복)")

    display_cols = [
        "id", "계정명", "서버", "신뢰도", "생활완료", "생기상태",
        "보석배", "보석배시간", "낙원", "이벤", "싱글",
        "CD1", "CD2", "CD3", "CD4", "CD5", "CD6",
        "카던큐브", "보석메모", "C1", "C2", "C3", "C4", "C5", "C6"
    ]

    df = pd.DataFrame(data["rows"])
    for col in display_cols:
        if col not in df.columns:
            df[col] = False if col in ["생활완료", "보석배", "낙원", "이벤", "싱글"] else "➖"

    if only_todo:
        df = df[(~df["생활완료"]) | (~df["보석배"])]
    if sort_urgent:
        df = df.sort_values(by=["생활완료", "생기수치", "보석배"], ascending=[True, False, True])

    # 카던 드롭다운 옵션 구성 (현재 표시값 + 조작 메뉴)
    base_cd_actions = [
        "⚡오늘돌았음(-1칸)",
        "🔥5칸(풀)",
        "🟡4칸",
        "🟡3칸",
        "⚪2칸",
        "⚪1칸",
        "⚪0칸",
        "➖(제외)"
    ]
    all_cd_vals = set(base_cd_actions)
    for c in range(1, 7):
        all_cd_vals.update(df[f"CD{c}"].dropna().unique().tolist())
    cd_options = base_cd_actions + [x for x in sorted(all_cd_vals) if x not in base_cd_actions]

    column_config = {
        "id": None,
        "계정명": st.column_config.TextColumn("계정명", width="small"),
        "서버": st.column_config.TextColumn("서버", width="small"),
        "신뢰도": st.column_config.SelectboxColumn("🛡️신뢰도", options=TRUST_OPTIONS, width="small"),
        "생활완료": st.column_config.CheckboxColumn("🌿생활", width="small"),
        "생기상태": st.column_config.TextColumn("생기 현황 (10,500)", width="medium", disabled=True),
        "보석배": st.column_config.CheckboxColumn("🚢보석배", width="small"),
        "보석배시간": st.column_config.TextColumn("수령일시", width="small", disabled=True),
        "낙원": st.column_config.CheckboxColumn("🏝️낙원", width="small"),
        "이벤": st.column_config.CheckboxColumn("🎁이벤", width="small"),
        "싱글": st.column_config.CheckboxColumn("🪙싱글", width="small"),
        "카던큐브": st.column_config.TextColumn("🎫큐브티켓", width="small", help="보유 큐브 티켓 메모"),
        "보석메모": st.column_config.TextColumn("💎보석/수익 메모", width="medium", help="모인 보석이나 판매 일정 메모"),
    }
    
    for c in range(1, 7):
        column_config[f"CD{c}"] = st.column_config.SelectboxColumn(
            f"🌀{c}카", options=cd_options, width="small", help="카던 돌았을 때 '⚡오늘돌았음(-1칸)' 선택!"
        )
        column_config[f"C{c}"] = st.column_config.SelectboxColumn(
            f"⚔️{c}캐", options=RAID_OPTIONS, width="small"
        )

    edited_df = st.data_editor(
        df[display_cols],
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=880,
        key="loa_editor_v3"
    )

    now = datetime.now(KST)
    changed = False
    orig_map = {r["id"]: r for r in data["rows"]}

    for _, edit_row in edited_df.iterrows():
        rid = int(edit_row["id"])
        orig = orig_map[rid]

        for col in ["계정명", "서버", "신뢰도", "카던큐브", "보석메모", "C1", "C2", "C3", "C4", "C5", "C6"]:
            val = "" if pd.isna(edit_row[col]) else str(edit_row[col])
            if orig.get(col, "") != val:
                orig[col] = val
                changed = True

        # 카던 휴식게이지 조작 감지
        for c in range(1, 7):
            col_cd = f"CD{c}"
            new_val = "" if pd.isna(edit_row[col_cd]) else str(edit_row[col_cd])
            old_val = orig.get(col_cd, "")
            
            if new_val != old_val:
                if new_val == "⚡오늘돌았음(-1칸)":
                    cur_pts = orig.get(f"CD{c}_pts", 100)
                    if cur_pts < 0:
                        cur_pts = 100
                    # 오늘 돌았으므로 1칸(20점) 차감 + 오늘치 자연회복 없도록 기준일을 내일로 세팅
                    orig[f"CD{c}_pts"] = max(0, cur_pts - 20)
                    orig[f"CD{c}_run"] = now.isoformat()
                    orig[f"CD{c}_upd"] = (now + timedelta(days=1)).isoformat()
                elif new_val == "➖(제외)":
                    orig[f"CD{c}_pts"] = -1
                    orig[f"CD{c}_run"] = ""
                    orig[f"CD{c}_upd"] = now.isoformat()
                else:
                    # 수동으로 0칸~5칸 직접 지정한 경우
                    for b in range(6):
                        if f"{b}칸" in new_val:
                            orig[f"CD{c}_pts"] = b * 20
                            orig[f"CD{c}_upd"] = now.isoformat()
                            break
                orig[col_cd] = format_cd_display(orig[f"CD{c}_pts"], orig[f"CD{c}_run"], now)
                changed = True

        if orig["생활완료"] != bool(edit_row["생활완료"]):
            orig["생활완료"] = bool(edit_row["생활완료"])
            orig["생활기록시간"] = now.isoformat() if orig["생활완료"] else ""
            changed = True

        if orig["보석배"] != bool(edit_row["보석배"]):
            orig["보석배"] = bool(edit_row["보석배"])
            orig["보석배시간"] = now.strftime("%m/%d %H:%M") if orig["보석배"] else ""
            changed = True

        for k in ["낙원", "이벤", "싱글"]:
            if orig[k] != bool(edit_row[k]):
                orig[k] = bool(edit_row[k])
                changed = True

    if changed:
        st.session_state.loa_data_v3 = process_auto_updates(data)
        save_data(st.session_state.loa_data_v3)
        st.rerun()

with tab_maple:
    render_game_timer("maple", "메이플스토리", default_min=30)
    st.info("🍁 로스트아크 테스트 완료 후, 여기에 메이플스토리 맞춤형 대시보드가 들어갑니다.")

with tab_gersang:
    render_game_timer("gersang", "천하제일상 거상", default_min=60)
    st.info("💰 메이플스토리 세팅 후, 여기에 거상 맞춤형 대시보드가 들어갑니다.")
