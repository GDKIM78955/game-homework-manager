import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import math
from datetime import datetime, timedelta
import pytz
from github import Github

st.set_page_config(page_title="통합 게임 숙제 & 타임 매니저", page_icon="🎮", layout="wide")

KST = pytz.timezone('Asia/Seoul')
LOA_FILE = "loa_data_v3.json"
GERSANG_FILE = "gersang_data_v1.json"

# 로아 25개 서버 초기 세팅
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

RAID_OPTIONS = ["➖", "1/3", "2/3", "✅3/3", "🔧계승중", "✅계승완료"]
TRUST_OPTIONS = ["🟡작업중", "🟢안전", "🔴부족"]

# 💰 거상 '만 전' 단위를 보기 쉽게 '억/만 전'으로 변환해 주는 함수
def fmt_man(val):
    try:
        v = float(val)
    except Exception:
        return "0만 전"
    sign = "-" if v < 0 else ""
    v_abs = abs(v)
    eok = int(v_abs // 10000)
    man = v_abs % 10000
    if eok > 0:
        if man == 0:
            return f"{sign}{eok:,}억 전"
        elif man.is_integer():
            return f"{sign}{eok:,}억 {int(man):,}만 전"
        else:
            return f"{sign}{eok:,}억 {man:,.1f}만 전"
    else:
        if man.is_integer():
            return f"{sign}{int(man):,}만 전"
        return f"{sign}{man:,.1f}만 전"

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
        with c3:
            st.write("")
            if st.button("⏹️ 정지/초기화", key=f"stop_{game_key}", use_container_width=True):
                st.session_state[run_key] = False
                st.session_state[end_key] = None
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

# 공통 로컬/깃허브 파일 입출력 함수
def save_json_local(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_json_github(filename, data, commit_msg):
    save_json_local(filename, data)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            try:
                contents = repo.get_contents(filename)
                repo.update_file(contents.path, commit_msg, json_str, contents.sha)
            except Exception:
                repo.create_file(filename, commit_msg, json_str)
            return True
        except Exception as e:
            st.error(f"GitHub 저장 오류: {e}")
            return False
    return False

# ==============================================================================
# ⚓ 1. 로스트아크 데이터 및 로직
# ==============================================================================
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

def format_cd_display(pts, run_str, now):
    if pts < 0:
        return "➖(제외)"
    bars = pts // 20
    half = ".5" if (pts % 20 >= 10) else ""
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

def create_initial_loa(now_str):
    now = datetime.fromisoformat(now_str)
    rows = []
    for idx, (acc, srv) in enumerate(DEFAULT_SERVERS):
        row = {
            "id": idx, "계정명": acc, "서버": srv, "신뢰도": "🟡작업중",
            "생활완료": False, "생활기록시간": "", "생기수치": 10500, "생기상태": "🔥 10,500 (수확 가능)",
            "보석배": False, "보석배시간": "", "낙원": False, "이벤": False, "싱글": False,
            "카던큐브": "", "보석메모": "",
        }
        for c in range(1, 7):
            row[f"LV{c}"] = ""
            row[f"CD{c}_pts"] = 100
            row[f"CD{c}_upd"] = now_str
            row[f"CD{c}_run"] = ""
            row[f"CD{c}"] = format_cd_display(100, "", now)
            row[f"C{c}"] = "➖"
        rows.append(row)
    return {"last_reset_check": now_str, "reset_day": "목요일 06:00", "rows": rows}

def ensure_loa_schema(data):
    now = datetime.now(KST)
    now_str = now.isoformat()
    if not isinstance(data, dict) or "rows" not in data:
        return create_initial_loa(now_str)
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
            row.setdefault(f"LV{c}", "")
            row.setdefault(f"CD{c}_pts", 100)
            row.setdefault(f"CD{c}_upd", now_str)
            row.setdefault(f"CD{c}_run", "")
            row.setdefault(f"CD{c}", format_cd_display(row[f"CD{c}_pts"], row[f"CD{c}_run"], now))
            row.setdefault(f"C{c}", "➖")
    return data

def load_loa_data():
    now = datetime.now(KST)
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(LOA_FILE)
            return ensure_loa_schema(json.loads(contents.decoded_content.decode("utf-8")))
        except Exception:
            return create_initial_loa(now.isoformat())
    else:
        try:
            with open(LOA_FILE, "r", encoding="utf-8") as f:
                return ensure_loa_schema(json.load(f))
        except Exception:
            return create_initial_loa(now.isoformat())

def process_loa_updates(data):
    data = ensure_loa_schema(data)
    now = datetime.now(KST)
    changed = False
    reset_weekday = 3 if data.get("reset_day", "목요일 06:00").startswith("목") else 2
    last_reset = get_last_weekly_reset(now, reset_weekday)
    last_check = datetime.fromisoformat(data["last_reset_check"])
    if last_check.tzinfo is None:
        last_check = KST.localize(last_check)

    if last_check < last_reset:
        for row in data["rows"]:
            row["보석배"] = False
            row["보석배시간"] = ""
            row["낙원"] = False
            row["이벤"] = False
            row["싱글"] = False
            for c in range(1, 7):
                if row.get(f"C{c}") in ["1/3", "2/3", "✅3/3"]:
                    row[f"C{c}"] = "➖"
        data["last_reset_check"] = now.isoformat()
        changed = True

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
        save_json_local(LOA_FILE, data)
    return data


# ==============================================================================
# 💰 2. 거상 데이터 및 로직 (단위: 만 전)
# ==============================================================================
PROFIT_LINK_OPTS = [
    "합산 안 함 (2클라 자체 자금만)",
    "이번 달 장사 순수익 합산",
    "누적 전체 장사 순수익 합산"
]

def create_initial_gersang(today_str):
    return {
        "last_daily_date": today_str,
        "daily_tasks": {
            "quest": False,
            "factory": False,
            "hunt_goal": False
        },
        "client2_farm": {
            "current_money": 0.0,
            "profit_link_mode": PROFIT_LINK_OPTS[0],
            "drop_item_name": "주력 드랍템",
            "drop_item_price": 10.0,
            "drops_per_hour": 30.0,
            "extra_hourly_man": 500.0,
            "daily_hours": 2.0,
            "targets": [
                {"id": 1, "포함": True, "아이템명": "다음 단계 목표템 1 (클릭해 수정)", "목표가": 50000.0, "구매완료": False, "메모": "예: 5억 전"},
                {"id": 2, "포함": True, "아이템명": "다음 단계 목표템 2 (클릭해 수정)", "목표가": 30000.0, "구매완료": False, "메모": "예: 3억 전"},
            ]
        },
        "client1_trades": []
    }

def ensure_gersang_schema(data):
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    if not isinstance(data, dict):
        return create_initial_gersang(today_str)
    data.setdefault("last_daily_date", today_str)
    data.setdefault("daily_tasks", {"quest": False, "factory": False, "hunt_goal": False})
    
    if data["last_daily_date"] != today_str:
        for k in data["daily_tasks"]:
            data["daily_tasks"][k] = False
        data["last_daily_date"] = today_str
        save_json_local(GERSANG_FILE, data)

    c2 = data.setdefault("client2_farm", {})
    c2.setdefault("current_money", 0.0)
    c2.setdefault("profit_link_mode", PROFIT_LINK_OPTS[0])
    if c2["profit_link_mode"] not in PROFIT_LINK_OPTS:
        c2["profit_link_mode"] = PROFIT_LINK_OPTS[0]
    c2.setdefault("drop_item_name", "주력 드랍템")
    c2.setdefault("drop_item_price", 10.0)
    c2.setdefault("drops_per_hour", 30.0)
    c2.setdefault("extra_hourly_man", 500.0)
    c2.setdefault("daily_hours", 2.0)
    c2.setdefault("targets", [])
    for idx, t in enumerate(c2["targets"]):
        t.setdefault("id", idx + 1)
        t.setdefault("포함", True)
        t.setdefault("아이템명", "목표 아이템")
        t.setdefault("목표가", 10000.0)
        t.setdefault("구매완료", False)
        t.setdefault("메모", "")
    data.setdefault("client1_trades", [])
    return data

def load_gersang_data():
    today_str = datetime.now(KST).strftime("%Y-%m-%d")
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(GERSANG_FILE)
            return ensure_gersang_schema(json.loads(contents.decoded_content.decode("utf-8")))
        except Exception:
            return create_initial_gersang(today_str)
    else:
        try:
            with open(GERSANG_FILE, "r", encoding="utf-8") as f:
                return ensure_gersang_schema(json.load(f))
        except Exception:
            return create_initial_gersang(today_str)


# ==============================================================================
# 세션 초기화
# ==============================================================================
if "loa_data_v3" not in st.session_state:
    st.session_state.loa_data_v3 = load_loa_data()
if "editor_ver" not in st.session_state:
    st.session_state.editor_ver = 0
if "dirty" not in st.session_state:
    st.session_state.dirty = False

if "gersang_data" not in st.session_state:
    st.session_state.gersang_data = load_gersang_data()
if "gs_dirty" not in st.session_state:
    st.session_state.gs_dirty = False
if "gs_editor_ver" not in st.session_state:
    st.session_state.gs_editor_ver = 0

st.session_state.loa_data_v3 = process_loa_updates(st.session_state.loa_data_v3)
loa_data = st.session_state.loa_data_v3
gs_data = ensure_gersang_schema(st.session_state.gersang_data)

st.title("🎮 나만의 게임 숙제 & 수익 관리 매니저")
tab_loa, tab_gersang, tab_maple = st.tabs(["⚓ 로스트아크 (25서버)", "💰 천하제일상 거상 (2클라+장사)", "🍁 메이플스토리"])

# ==============================================================================
# 탭 1: 로스트아크 화면
# ==============================================================================
with tab_loa:
    render_game_timer("loa", "로스트아크", default_min=45)

    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([1.6, 1.3, 1.5, 1.1, 1.3])
    with col_f1:
        only_todo = st.checkbox("🔥 할 일 남음(생기 풀/보석배)만 보기", value=False)
    with col_f2:
        sort_urgent = st.checkbox("⚡ 생기 많은 순 정렬", value=False)
    with col_f3:
        reset_opt = st.radio(
            "주간 리셋 기준",
            ["목요일 06:00", "수요일 06:00"],
            index=0 if loa_data.get("reset_day", "목요일 06:00") == "목요일 06:00" else 1,
            horizontal=True,
            label_visibility="collapsed"
        )
        if reset_opt != loa_data.get("reset_day"):
            loa_data["reset_day"] = reset_opt
            save_json_local(LOA_FILE, loa_data)
            st.session_state.dirty = True
    with col_f4:
        if st.button("🔄 시간 새로고침", use_container_width=True):
            st.session_state.loa_data_v3 = process_loa_updates(loa_data)
            st.session_state.editor_ver += 1
            st.rerun()
    with col_f5:
        btn_label = "💾 깃허브 백업 저장 (미저장*)" if st.session_state.dirty else "💾 깃허브 백업 저장 (완료)"
        btn_type = "primary" if st.session_state.dirty else "secondary"
        if st.button(btn_label, type=btn_type, use_container_width=True, key="save_loa_gh"):
            if save_json_github(LOA_FILE, loa_data, "Update LOA v3 data"):
                st.session_state.dirty = False
                st.toast("✅ 로스트아크 데이터가 깃허브에 영구 저장되었습니다!")
                st.rerun()

    col_v1, col_v2, col_v3, col_v4 = st.columns([1.2, 1.2, 1.2, 2.4])
    with col_v1:
        show_lv = st.checkbox("📊 캐릭터별 템렙 보이기", value=True)
    with col_v2:
        show_cd = st.checkbox("🌀 카던 휴게 보이기", value=True)
    with col_v3:
        show_raid = st.checkbox("⚔️ 레이드/계승 보이기", value=True)
    with col_v4:
        group_by_char = st.checkbox("👥 캐릭터별로 묶어서 배열 (1렙-1카-1캐 순서)", value=True)

    display_cols = [
        "id", "계정명", "서버", "신뢰도", "생활완료", "생기상태",
        "보석배", "보석배시간", "낙원", "이벤", "싱글"
    ]
    if group_by_char:
        for c in range(1, 7):
            if show_lv: display_cols.append(f"LV{c}")
            if show_cd: display_cols.append(f"CD{c}")
            if show_raid: display_cols.append(f"C{c}")
    else:
        if show_lv: display_cols.extend([f"LV{c}" for c in range(1, 7)])
        if show_cd: display_cols.extend([f"CD{c}" for c in range(1, 7)])
        if show_raid: display_cols.extend([f"C{c}" for c in range(1, 7)])
    display_cols.extend(["카던큐브", "보석메모"])

    df = pd.DataFrame(loa_data["rows"])
    for col in display_cols:
        if col not in df.columns:
            df[col] = False if col in ["생활완료", "보석배", "낙원", "이벤", "싱글"] else ""

    if only_todo:
        df = df[(~df["생활완료"]) | (~df["보석배"])]
    if sort_urgent:
        df = df.sort_values(by=["생활완료", "생기수치", "보석배"], ascending=[True, False, True])

    base_cd_actions = [
        "⚡오늘돌았음(-1칸)",
        "🔄5칸(풀)로 설정/복구",
        "🔄4칸으로 설정",
        "🔄3칸으로 설정",
        "🔄2칸으로 설정",
        "🔄1칸으로 설정",
        "🔄0칸으로 설정",
        "➖(제외)"
    ]
    all_cd_vals = set(base_cd_actions)
    for c in range(1, 7):
        if f"CD{c}" in df.columns:
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
        "카던큐브": st.column_config.TextColumn("🎫큐브티켓", width="small"),
        "보석메모": st.column_config.TextColumn("💎보석/수익 메모", width="medium"),
    }
    for c in range(1, 7):
        column_config[f"LV{c}"] = st.column_config.TextColumn(f"📊{c}렙", width="small")
        column_config[f"CD{c}"] = st.column_config.SelectboxColumn(f"🌀{c}카", options=cd_options, width="small")
        column_config[f"C{c}"] = st.column_config.SelectboxColumn(f"⚔️{c}캐", options=RAID_OPTIONS, width="small")

    editor_key = f"loa_editor_v5_{st.session_state.editor_ver}"
    edited_df = st.data_editor(
        df[display_cols],
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=880,
        key=editor_key
    )

    now = datetime.now(KST)
    changed = False
    need_table_refresh = False
    orig_map = {r["id"]: r for r in loa_data["rows"]}

    for _, edit_row in edited_df.iterrows():
        rid = int(edit_row["id"])
        orig = orig_map[rid]
        text_cols = ["계정명", "서버", "신뢰도", "카던큐브", "보석메모"] + [f"LV{c}" for c in range(1, 7)] + [f"C{c}" for c in range(1, 7)]
        for col in text_cols:
            if col in edit_row:
                val = "" if pd.isna(edit_row[col]) else str(edit_row[col])
                if orig.get(col, "") != val:
                    orig[col] = val
                    changed = True

        for c in range(1, 7):
            col_cd = f"CD{c}"
            if col_cd in edit_row:
                new_val = "" if pd.isna(edit_row[col_cd]) else str(edit_row[col_cd])
                old_val = orig.get(col_cd, "")
                if new_val != old_val:
                    if new_val == "⚡오늘돌았음(-1칸)":
                        cur_pts = orig.get(f"CD{c}_pts", 100)
                        if cur_pts < 0: cur_pts = 100
                        orig[f"CD{c}_pts"] = max(0, cur_pts - 20)
                        orig[f"CD{c}_run"] = now.isoformat()
                        orig[f"CD{c}_upd"] = (now + timedelta(days=1)).isoformat()
                        orig[col_cd] = format_cd_display(orig[f"CD{c}_pts"], orig[f"CD{c}_run"], now)
                        changed = True
                        need_table_refresh = True
                    elif new_val == "➖(제외)":
                        orig[f"CD{c}_pts"] = -1
                        orig[f"CD{c}_run"] = ""
                        orig[f"CD{c}_upd"] = now.isoformat()
                        orig[col_cd] = "➖(제외)"
                        changed = True
                    elif new_val.startswith("🔄"):
                        for b in range(6):
                            if f"{b}칸" in new_val:
                                orig[f"CD{c}_pts"] = b * 20
                                orig[f"CD{c}_run"] = ""
                                orig[f"CD{c}_upd"] = now.isoformat()
                                break
                        orig[col_cd] = format_cd_display(orig[f"CD{c}_pts"], orig[f"CD{c}_run"], now)
                        changed = True
                        need_table_refresh = True

        if orig["생활완료"] != bool(edit_row["생활완료"]):
            orig["생활완료"] = bool(edit_row["생활완료"])
            orig["생활기록시간"] = now.isoformat() if orig["생활완료"] else ""
            changed = True
            need_table_refresh = True

        if orig["보석배"] != bool(edit_row["보석배"]):
            orig["보석배"] = bool(edit_row["보석배"])
            orig["보석배시간"] = now.strftime("%m/%d %H:%M") if orig["보석배"] else ""
            changed = True
            need_table_refresh = True

        for k in ["낙원", "이벤", "싱글"]:
            if orig[k] != bool(edit_row[k]):
                orig[k] = bool(edit_row[k])
                changed = True

    if changed:
        st.session_state.loa_data_v3 = process_loa_updates(loa_data)
        save_json_local(LOA_FILE, st.session_state.loa_data_v3)
        st.session_state.dirty = True
        if need_table_refresh:
            st.session_state.editor_ver += 1
            st.rerun()


# ==============================================================================
# 탭 2: 천하제일상 거상 화면 (2클라 반자사 목표 계산기 + 1클라 장사 가계부/족보)
# ==============================================================================
with tab_gersang:
    render_game_timer("gersang", "천하제일상 거상", default_min=60)

    trades = gs_data["client1_trades"]
    now_kst = datetime.now(KST)
    cur_ym = now_kst.strftime("%Y-%m")

    holding_list = [t for t in trades if t.get("status") == "보유중"]
    sold_list = [t for t in trades if t.get("status") == "판매완료"]

    tied_capital = sum(float(t.get("buy_price", 0)) * int(t.get("qty", 1)) for t in holding_list)
    this_month_profit = sum(float(t.get("net_profit", 0)) for t in sold_list if str(t.get("sell_date", "")).startswith(cur_ym))
    total_profit = sum(float(t.get("net_profit", 0)) for t in sold_list)

    with st.container(border=True):
        d_col1, d_col2, d_col3, d_col4, d_col5 = st.columns([1.3, 1.3, 1.3, 1.3, 1.5])
        with d_col1:
            st.markdown("**🌅 거상 일일 루틴 (00시 리셋)**")
        with d_col2:
            q_val = st.checkbox("📜 일일 퀘스트 완료", value=gs_data["daily_tasks"].get("quest", False))
        with d_col3:
            f_val = st.checkbox("🏭 생산시설 작업량 채우기", value=gs_data["daily_tasks"].get("factory", False))
        with d_col4:
            h_val = st.checkbox("🏹 오늘치 반자사 목표 달성", value=gs_data["daily_tasks"].get("hunt_goal", False))
        with d_col5:
            gs_btn_label = "💾 거상 깃허브 백업 (미저장*)" if st.session_state.gs_dirty else "💾 거상 깃허브 백업 (완료)"
            gs_btn_type = "primary" if st.session_state.gs_dirty else "secondary"
            if st.button(gs_btn_label, type=gs_btn_type, use_container_width=True, key="save_gs_gh"):
                if save_json_github(GERSANG_FILE, gs_data, "Update Gersang data"):
                    st.session_state.gs_dirty = False
                    st.toast("✅ 거상 데이터가 깃허브에 영구 저장되었습니다!")
                    st.rerun()

        if (q_val != gs_data["daily_tasks"].get("quest") or
            f_val != gs_data["daily_tasks"].get("factory") or
            h_val != gs_data["daily_tasks"].get("hunt_goal")):
            gs_data["daily_tasks"]["quest"] = q_val
            gs_data["daily_tasks"]["factory"] = f_val
            gs_data["daily_tasks"]["hunt_goal"] = h_val
            save_json_local(GERSANG_FILE, gs_data)
            st.session_state.gs_dirty = True

    st.caption("💡 모든 금액 입력 기준은 **`만 전`**입니다. (예: `10000` 입력 시 자동으로 **`1억 전`**으로 계산 및 표시됩니다!)")

    col_left, col_right = st.columns([1.05, 1.45], gap="large")

    # --------------------------------------------------------------------------
    # 🏹 [왼쪽] 2클라 (기마궁수 반자사) 다음 단계 목표 계산기
    # --------------------------------------------------------------------------
    with col_left:
        with st.container(border=True):
            st.subheader("🏹 2클라 (기마궁수) 스펙업 & 파밍 계산기")
            c2 = gs_data["client2_farm"]

            st.markdown("##### ⚙️ 1. 현재 자금 및 사냥터 드랍템 설정")
            f_c1, f_c2 = st.columns(2)
            with f_c1:
                cur_money = st.number_input("💰 2클라 자체 보유 자금 (만 전)", min_value=0.0, value=float(c2["current_money"]), step=1000.0, format="%.0f")
                st.caption(f"👉 환산: **{fmt_man(cur_money)}**")
            with f_c2:
                daily_hrs = st.number_input("⏰ 하루 평균 반자사 시간 (시간)", min_value=0.5, max_value=24.0, value=float(c2["daily_hours"]), step=0.5)

            link_mode = st.selectbox(
                "🤝 1클라 장사 순수익을 2클라 목표 자금에 보태기",
                options=PROFIT_LINK_OPTS,
                index=PROFIT_LINK_OPTS.index(c2.get("profit_link_mode", PROFIT_LINK_OPTS[0]))
            )
            bonus_profit = 0.0
            if link_mode == PROFIT_LINK_OPTS[1]:
                bonus_profit = max(0.0, this_month_profit)
                st.caption(f"✨ 이번 달 장사 순수익 **+{fmt_man(bonus_profit)}**이 목표 자금에 자동 합산됩니다!")
            elif link_mode == PROFIT_LINK_OPTS[2]:
                bonus_profit = max(0.0, total_profit)
                st.caption(f"✨ 누적 전체 장사 순수익 **+{fmt_man(bonus_profit)}**이 목표 자금에 자동 합산됩니다!")

            f_c3, f_c4, f_c5 = st.columns(3)
            with f_c3:
                drop_name = st.text_input("🎁 주력 드랍템 이름", value=str(c2["drop_item_name"]))
            with f_c4:
                drop_price = st.number_input("💎 드랍템 개당 가격 (만 전)", min_value=0.1, value=float(c2["drop_item_price"]), step=1.0, format="%.1f")
            with f_c5:
                drops_hr = st.number_input("📦 시간당 획득 개수 (개)", min_value=0.0, value=float(c2["drops_per_hour"]), step=1.0, format="%.1f")

            extra_hr = st.number_input("🪙 시간당 추가 상재/부수입 (만 전, 없으면 0)", min_value=0.0, value=float(c2["extra_hourly_man"]), step=50.0, format="%.0f")

            if (cur_money != c2["current_money"] or daily_hrs != c2["daily_hours"] or
                link_mode != c2.get("profit_link_mode") or
                drop_name != c2["drop_item_name"] or drop_price != c2["drop_item_price"] or
                drops_hr != c2["drops_per_hour"] or extra_hr != c2["extra_hourly_man"]):
                c2["current_money"] = cur_money
                c2["daily_hours"] = daily_hrs
                c2["profit_link_mode"] = link_mode
                c2["drop_item_name"] = drop_name
                c2["drop_item_price"] = drop_price
                c2["drops_per_hour"] = drops_hr
                c2["extra_hourly_man"] = extra_hr
                save_json_local(GERSANG_FILE, gs_data)
                st.session_state.gs_dirty = True

            st.divider()

            st.markdown("##### 🎯 2. 다음 단계를 위해 구해야 할 목표 템 목록")
            st.caption("표 하단의 `+` 버튼을 눌러 목표 템을 추가하거나, 이름을 더블클릭해 수정하세요.")

            target_df = pd.DataFrame(c2["targets"])
            if target_df.empty:
                target_df = pd.DataFrame(columns=["id", "포함", "아이템명", "목표가", "구매완료", "메모"])

            edited_targets = st.data_editor(
                target_df[["포함", "아이템명", "목표가", "구매완료", "메모"]],
                column_config={
                    "포함": st.column_config.CheckboxColumn("🎯목표포함", width="small", default=True),
                    "아이템명": st.column_config.TextColumn("구할 아이템 이름", width="medium", required=True),
                    "목표가": st.column_config.NumberColumn("예상 가격(만 전)", width="small", min_value=0.0, step=100.0, format="%d만", default=10000.0),
                    "구매완료": st.column_config.CheckboxColumn("✅구입완료", width="small", default=False),
                    "메모": st.column_config.TextColumn("메모", width="small", default=""),
                },
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key=f"gs_target_editor_{st.session_state.gs_editor_ver}"
            )

            new_targets = []
            for idx, r in edited_targets.iterrows():
                if pd.isna(r["아이템명"]) or str(r["아이템명"]).strip() == "":
                    continue
                new_targets.append({
                    "id": idx + 1,
                    "포함": True if pd.isna(r["포함"]) else bool(r["포함"]),
                    "아이템명": str(r["아이템명"]),
                    "목표가": 0.0 if pd.isna(r["목표가"]) else float(r["목표가"]),
                    "구매완료": False if pd.isna(r["구매완료"]) else bool(r["구매완료"]),
                    "메모": "" if pd.isna(r["메모"]) else str(r["메모"])
                })
            if new_targets != c2["targets"]:
                c2["targets"] = new_targets
                save_json_local(GERSANG_FILE, gs_data)
                st.session_state.gs_dirty = True

            active_targets = [t for t in c2["targets"] if t["포함"] and not t["구매완료"]]
            total_goal = sum(t["목표가"] for t in active_targets)
            effective_money = cur_money + bonus_profit
            shortfall = max(0.0, total_goal - effective_money)
            hourly_income = (drop_price * drops_hr) + extra_hr
            daily_income = hourly_income * daily_hrs

            st.divider()
            st.markdown("##### 📊 3. 목표 달성 자동 계산 결과")
            
            m1, m2 = st.columns(2)
            m1.metric("🎯 남은 목표 총액", fmt_man(total_goal), f"선택된 미구입 템 {len(active_targets)}개")
            m2.metric(
                "🔥 앞으로 더 필요한 금액",
                fmt_man(shortfall),
                "목표 달성!" if shortfall == 0 else f"가용 자금 {fmt_man(effective_money)} 반영"
            )

            if total_goal > 0:
                prog = min(1.0, effective_money / total_goal)
                st.progress(prog, text=f"목표 달성률: {prog*100:.1f}% ({fmt_man(effective_money)} / {fmt_man(total_goal)})")

            if shortfall > 0:
                items_needed = math.ceil(shortfall / drop_price) if drop_price > 0 else 0
                hours_needed = shortfall / hourly_income if hourly_income > 0 else 0
                days_needed = shortfall / daily_income if daily_income > 0 else 0

                st.info(
                    f"🏹 **[{drop_name}] 단독 파밍 기준:** 앞으로 약 **`{items_needed:,}개`** 더 캐면 목표 금액 달성!\n\n"
                    f"⏱️ **현재 반자사 속도 기준 (시간당 {fmt_man(hourly_income)} / 하루 {fmt_man(daily_income)}):**\n"
                    f"👉 총 **`{hours_needed:.1f}시간`** 사냥 필요 (하루 {daily_hrs}시간 기준 약 **`{days_needed:.1f}일`** 소요 예상)"
                )
            elif total_goal > 0:
                st.success("🎉 현재 가용 자금(장사 수익 포함)으로 목표 아이템을 전부 구매할 수 있습니다!")

    # --------------------------------------------------------------------------
    # 💰 [오른쪽] 1클라 장사 가계부 (직접 수정/복구/분할매도 완벽 지원!)
    # --------------------------------------------------------------------------
    with col_right:
        with st.container(border=True):
            st.subheader("💰 1클라 장사 가계부 & 시세 족보 (수수료 2% 자동 반영)")

            k1, k2, k3 = st.columns(3)
            k1.metric(f"📅 이번 달({cur_ym}) 순수익", fmt_man(this_month_profit), "수수료 2% 공제 후")
            k2.metric("🔒 현재 묶인 재고 자금", fmt_man(tied_capital), f"보유 매물 {len(holding_list)}건")
            k3.metric("👑 누적 총 장사 순수익", fmt_man(total_profit), f"누적 판매 {len(sold_list)}건")

            if sold_list:
                monthly_map = {}
                for t in sold_list:
                    ym = str(t.get("sell_date", "기타"))[:7]
                    if ym not in monthly_map:
                        monthly_map[ym] = {"월(YYYY-MM)": ym, "판매 건수": 0, "총 매출(만)": 0.0, "총 매입원가(만)": 0.0, "순수익(만)": 0.0}
                    qty = int(t.get("qty", 1))
                    monthly_map[ym]["판매 건수"] += 1
                    monthly_map[ym]["총 매출(만)"] += float(t.get("sell_price", 0)) * qty
                    monthly_map[ym]["총 매입원가(만)"] += float(t.get("buy_price", 0)) * qty
                    monthly_map[ym]["순수익(만)"] += float(t.get("net_profit", 0))
                
                m_rows = sorted(monthly_map.values(), key=lambda x: x["월(YYYY-MM)"], reverse=True)
                for mr in m_rows:
                    mr["순수익 환산"] = fmt_man(mr["순수익(만)"])
                    mr["수익률"] = f"{(mr['순수익(만)'] / mr['총 매입원가(만)'] * 100):.1f}%" if mr["총 매입원가(만)"] > 0 else "0%"
                
                with st.expander("🗓️ 월별 장사 수익 달력 상세 보기 (클릭해서 열기/닫기)", expanded=True):
                    st.dataframe(
                        pd.DataFrame(m_rows)[["월(YYYY-MM)", "판매 건수", "순수익 환산", "수익률", "총 매입원가(만)", "총 매출(만)"]],
                        use_container_width=True,
                        hide_index=True
                    )

            st.divider()

            st.markdown("##### 📥 1. 물건 구매(매입) 등록하기")
            b_c1, b_c2, b_c3, b_c4 = st.columns([2, 1.5, 1, 1.2])
            with b_c1:
                in_item = st.text_input("아이템 이름", placeholder="예: 기린의뿔, 각성석", key="gs_in_item")
            with b_c2:
                in_price = st.number_input("개당 산 가격 (만 전)", min_value=0.0, value=1000.0, step=100.0, format="%.0f", key="gs_in_price")
            with b_c3:
                in_qty = st.number_input("수량 (개)", min_value=1, value=1, step=1, key="gs_in_qty")
            with b_c4:
                st.write("")
                if st.button("➕ 매입 장부에 추가", type="primary", use_container_width=True):
                    if in_item.strip():
                        new_id = max([t.get("id", 0) for t in trades], default=0) + 1
                        trades.append({
                            "id": new_id,
                            "item_name": in_item.strip(),
                            "buy_price": float(in_price),
                            "qty": int(in_qty),
                            "buy_date": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                            "status": "보유중",
                            "sell_price": 0.0,
                            "sell_date": "",
                            "net_profit": 0.0
                        })
                        save_json_local(GERSANG_FILE, gs_data)
                        st.session_state.gs_dirty = True
                        st.session_state.gs_editor_ver += 1
                        st.toast(f"✅ [{in_item.strip()}] {fmt_man(in_price)} × {in_qty}개 매입 등록 완료!")
                        st.rerun()
                    else:
                        st.warning("아이템 이름을 입력해 주세요!")

            if in_item.strip():
                same_hist = [t for t in trades if t.get("item_name") == in_item.strip()]
                if same_hist:
                    tot_q = sum(int(t.get("qty", 1)) for t in same_hist)
                    avg_b = sum(float(t.get("buy_price", 0)) * int(t.get("qty", 1)) for t in same_hist) / tot_q
                    max_b = max(float(t.get("buy_price", 0)) for t in same_hist)
                    min_b = min(float(t.get("buy_price", 0)) for t in same_hist)
                    st.caption(
                        f"💡 **[{in_item.strip()}] 내 과거 족보:** 평균 매입가 **{fmt_man(avg_b)}** | "
                        f"최고 비싸게 산 금액 **{fmt_man(max_b)}** | 최저 매입가 **{fmt_man(min_b)}** (누적 {tot_q}개 거래)"
                    )

            st.divider()

            # ✨ 업그레이드: 보유 매물장에서 아이템명, 산 가격, 보유수량을 더블클릭해 직접 수정 가능!
            st.markdown("##### 📦 2. 현재 보유 매물장 (잘못 적은 이름/산 가격/보유수량도 더블클릭해 바로 수정 가능!)")
            if not holding_list:
                st.info("현재 보유 중인 장사 매물이 없습니다. 위에서 구매한 물건을 등록해 보세요!")
            else:
                item_stats = {}
                for t in trades:
                    nm = t["item_name"]
                    item_stats.setdefault(nm, {"q": 0, "sum": 0.0, "max": 0.0})
                    q = int(t.get("qty", 1))
                    bp = float(t.get("buy_price", 0))
                    item_stats[nm]["q"] += q
                    item_stats[nm]["sum"] += bp * q
                    if bp > item_stats[nm]["max"]:
                        item_stats[nm]["max"] = bp

                hold_rows = []
                for t in holding_list:
                    nm = t["item_name"]
                    bp = float(t["buy_price"])
                    q = int(t.get("qty", 1))
                    avg_p = item_stats[nm]["sum"] / item_stats[nm]["q"]
                    max_p = item_stats[nm]["max"]
                    breakeven = math.ceil(bp / 0.98)
                    rec_5 = math.ceil((bp * 1.05) / 0.98)

                    hold_rows.append({
                        "id": t["id"],
                        "아이템명": nm,
                        "산가격(만)": bp,
                        "보유수량": q,
                        "내평균가(만)": round(avg_p, 1),
                        "내최고가(만)": max_p,
                        "손익분기(2%)": f"{breakeven:,}만 (5%:{rec_5:,}만)",
                        "판수량": q,
                        "판매가입력(만)": bp if float(t.get("sell_price", 0)) == 0 else float(t["sell_price"]),
                        "판매완료": False,
                        "삭제": False
                    })

                hold_df = pd.DataFrame(hold_rows)
                edited_hold = st.data_editor(
                    hold_df,
                    column_config={
                        "id": None,
                        "아이템명": st.column_config.TextColumn("✏️아이템명", width="small", help="오타가 났다면 더블클릭해서 바로 수정하세요!"),
                        "산가격(만)": st.column_config.NumberColumn("✏️산 가격(만)", width="small", min_value=0.0, step=100.0, format="%d만", help="산 가격을 잘못 적었다면 더블클릭해서 바로 고치세요!"),
                        "보유수량": st.column_config.NumberColumn("✏️보유수량", width="small", min_value=1, step=1, help="수량을 잘못 등록했다면 더블클릭해서 바로 고치세요!"),
                        "내평균가(만)": st.column_config.NumberColumn("내 평단가", width="small", format="%d만", disabled=True),
                        "내최고가(만)": st.column_config.NumberColumn("최고매입가", width="small", format="%d만", disabled=True),
                        "손익분기(2%)": st.column_config.TextColumn("2%본전(5%추천)", width="medium", disabled=True),
                        "판수량": st.column_config.NumberColumn("✏️판 수량", width="small", min_value=1, step=1, help="일부만 팔렸다면 팔린 개수만 입력하세요!"),
                        "판매가입력(만)": st.column_config.NumberColumn("✏️개당 판매가(만)", width="small", min_value=0.0, step=100.0, format="%d만"),
                        "판매완료": st.column_config.CheckboxColumn("💰판매완료", width="small"),
                        "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small")
                    },
                    use_container_width=True,
                    hide_index=True,
                    key=f"gs_hold_editor_{st.session_state.gs_editor_ver}"
                )

                trade_map = {t["id"]: t for t in trades}
                hold_changed = False
                for _, erow in edited_hold.iterrows():
                    tid = int(erow["id"])
                    orig_t = trade_map.get(tid)
                    if not orig_t:
                        continue
                    if bool(erow["삭제"]):
                        trades.remove(orig_t)
                        hold_changed = True
                        st.toast(f"🗑️ [{orig_t['item_name']}] 기록을 삭제했습니다.")
                        continue

                    # 1. 아이템명 / 산 가격 / 보유수량 직접 수정 감지
                    new_nm = str(erow["아이템명"]).strip() if not pd.isna(erow["아이템명"]) else orig_t["item_name"]
                    new_bp = float(erow["산가격(만)"]) if not pd.isna(erow["산가격(만)"]) else float(orig_t["buy_price"])
                    new_bq = max(1, int(erow["보유수량"])) if not pd.isna(erow["보유수량"]) else int(orig_t.get("qty", 1))

                    if new_nm != orig_t["item_name"] or new_bp != float(orig_t["buy_price"]) or new_bq != int(orig_t.get("qty", 1)):
                        orig_t["item_name"] = new_nm
                        orig_t["buy_price"] = new_bp
                        orig_t["qty"] = new_bq
                        hold_changed = True

                    # 2. 판매완료 처리 감지
                    if bool(erow["판매완료"]):
                        sp = float(erow["판매가입력(만)"])
                        bp = float(orig_t["buy_price"])
                        cur_q = int(orig_t.get("qty", 1))
                        sell_q = max(1, min(cur_q, int(erow["판수량"])))
                        net = round((sp * 0.98 - bp) * sell_q, 1)
                        now_str_sell = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

                        if sell_q < cur_q:
                            orig_t["qty"] = cur_q - sell_q
                            new_id = max([t.get("id", 0) for t in trades], default=0) + 1
                            trades.append({
                                "id": new_id,
                                "item_name": orig_t["item_name"],
                                "buy_price": bp,
                                "qty": sell_q,
                                "buy_date": orig_t.get("buy_date", ""),
                                "status": "판매완료",
                                "sell_price": sp,
                                "sell_date": now_str_sell,
                                "net_profit": net
                            })
                            st.toast(f"📦 [{orig_t['item_name']}] {sell_q}개 부분 판매 완료! (순수익: {fmt_man(net)} / 남은 수량: {cur_q - sell_q}개)")
                        else:
                            orig_t["sell_price"] = sp
                            orig_t["sell_date"] = now_str_sell
                            orig_t["net_profit"] = net
                            orig_t["status"] = "판매완료"
                            st.toast(f"🎉 [{orig_t['item_name']}] {sell_q}개 전량 판매 완료! (순수익: {fmt_man(net)})")
                        hold_changed = True

                if hold_changed:
                    save_json_local(GERSANG_FILE, gs_data)
                    st.session_state.gs_dirty = True
                    st.session_state.gs_editor_ver += 1
                    st.rerun()

            st.divider()

            with st.expander("📖 3. 나의 매입 족보 & 과거 기록 수정/복구 (그동안 샀던 물건 평균가/최고가 및 영수증 관리)", expanded=False):
                if not trades:
                    st.caption("아직 등록된 거래 내역이 없습니다.")
                else:
                    jokbo_map = {}
                    for t in trades:
                        nm = t["item_name"]
                        jokbo_map.setdefault(nm, {
                            "아이템명": nm, "총 매입수량": 0, "매입합계": 0.0,
                            "최고 매입가": 0.0, "최저 매입가": float('inf'),
                            "판매수량": 0, "판매합계": 0.0, "누적 순수익": 0.0, "최근 거래일": ""
                        })
                        jb = jokbo_map[nm]
                        q = int(t.get("qty", 1))
                        bp = float(t.get("buy_price", 0))
                        jb["총 매입수량"] += q
                        jb["매입합계"] += bp * q
                        if bp > jb["최고 매입가"]: jb["최고 매입가"] = bp
                        if bp < jb["최저 매입가"]: jb["최저 매입가"] = bp
                        if str(t.get("buy_date", "")) > jb["최근 거래일"]:
                            jb["최근 거래일"] = str(t.get("buy_date", ""))[:10]
                        if t.get("status") == "판매완료":
                            jb["판매수량"] += q
                            jb["판매합계"] += float(t.get("sell_price", 0)) * q
                            jb["누적 순수익"] += float(t.get("net_profit", 0))

                    jokbo_rows = []
                    for nm, jb in sorted(jokbo_map.items()):
                        avg_buy = jb["매입합계"] / jb["총 매입수량"]
                        be_price = math.ceil(avg_buy / 0.98)
                        avg_sell_str = f"{int(jb['판매합계']/jb['판매수량']):,}만" if jb["판매수량"] > 0 else "판매전"
                        jokbo_rows.append({
                            "아이템명": nm,
                            "누적매입": f"{jb['총 매입수량']}개",
                            "내 평균매입가": f"{int(avg_buy):,}만 ({fmt_man(avg_buy)})",
                            "최고비싸게산값": f"{int(jb['최고 매입가']):,}만",
                            "최저매입가": f"{int(jb['최저 매입가']):,}만",
                            "2%본전판매가": f"{be_price:,}만",
                            "평균판매가": avg_sell_str,
                            "누적순수익": fmt_man(jb["누적 순수익"]),
                            "최근매입일": jb["최근 거래일"]
                        })

                    st.markdown("###### 📊 아이템별 시세 족보 요약표")
                    search_kw = st.text_input("🔍 족보/과거기록 아이템 이름 검색 (비워두면 전체 보기)", key="gs_jokbo_search")
                    
                    jokbo_df = pd.DataFrame(jokbo_rows)
                    if search_kw.strip():
                        jokbo_df = jokbo_df[jokbo_df["아이템명"].str.contains(search_kw.strip(), case=False, na=False)]
                    st.dataframe(jokbo_df, use_container_width=True, hide_index=True)

                    st.markdown("###### 📜 과거 개별 구매/판매 영수증 전체 기록 (여기서도 가격/수량 수정 및 보유중 복구 가능!)")
                    hist_rows = []
                    for t in sorted(trades, key=lambda x: x.get("id", 0), reverse=True):
                        if search_kw.strip() and search_kw.strip().lower() not in t["item_name"].lower():
                            continue
                        hist_rows.append({
                            "id": t["id"],
                            "상태": "🟢판매완료" if t.get("status") == "판매완료" else "📦보유중",
                            "아이템명": t["item_name"],
                            "수량": int(t.get("qty", 1)),
                            "산가격(만)": float(t["buy_price"]),
                            "판가격(만)": float(t.get("sell_price", 0.0)),
                            "순수익": fmt_man(t.get("net_profit", 0)) if t.get("status") == "판매완료" else "-",
                            "매입일시": t.get("buy_date", ""),
                            "보유중복구": False,
                            "삭제": False
                        })
                    
                    if hist_rows:
                        hist_df = pd.DataFrame(hist_rows)
                        edited_hist = st.data_editor(
                            hist_df,
                            column_config={
                                "id": None,
                                "상태": st.column_config.TextColumn("상태", width="small", disabled=True),
                                "아이템명": st.column_config.TextColumn("✏️아이템명", width="small"),
                                "수량": st.column_config.NumberColumn("✏️수량", width="small", min_value=1, step=1),
                                "산가격(만)": st.column_config.NumberColumn("✏️산 가격(만)", width="small", min_value=0.0, step=100.0, format="%d만"),
                                "판가격(만)": st.column_config.NumberColumn("✏️판 가격(만)", width="small", min_value=0.0, step=100.0, format="%d만"),
                                "순수익": st.column_config.TextColumn("순수익(2%제외)", width="small", disabled=True),
                                "매입일시": st.column_config.TextColumn("매입일시", width="small", disabled=True),
                                "보유중복구": st.column_config.CheckboxColumn("↩️보유중복구", width="small", help="실수로 판매완료를 눌렀다면 체크해서 다시 보유 매물장으로 되돌립니다."),
                                "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small")
                            },
                            use_container_width=True,
                            hide_index=True,
                            key=f"gs_hist_editor_{st.session_state.gs_editor_ver}"
                        )

                        trade_map = {t["id"]: t for t in trades}
                        hist_changed = False
                        for _, hrow in edited_hist.iterrows():
                            tid = int(hrow["id"])
                            orig_t = trade_map.get(tid)
                            if not orig_t:
                                continue
                            if bool(hrow["삭제"]):
                                trades.remove(orig_t)
                                hist_changed = True
                                continue
                            if bool(hrow["보유중복구"]) and orig_t.get("status") == "판매완료":
                                orig_t["status"] = "보유중"
                                orig_t["sell_price"] = 0.0
                                orig_t["sell_date"] = ""
                                orig_t["net_profit"] = 0.0
                                hist_changed = True
                                continue

                            h_nm = str(hrow["아이템명"]).strip()
                            h_q = max(1, int(hrow["수량"]))
                            h_bp = float(hrow["산가격(만)"])
                            h_sp = float(hrow["판가격(만)"])

                            if (h_nm != orig_t["item_name"] or h_q != int(orig_t.get("qty", 1)) or
                                h_bp != float(orig_t["buy_price"]) or h_sp != float(orig_t.get("sell_price", 0.0))):
                                orig_t["item_name"] = h_nm
                                orig_t["qty"] = h_q
                                orig_t["buy_price"] = h_bp
                                orig_t["sell_price"] = h_sp
                                if orig_t.get("status") == "판매완료":
                                    orig_t["net_profit"] = round((h_sp * 0.98 - h_bp) * h_q, 1)
                                hist_changed = True

                        if hist_changed:
                            save_json_local(GERSANG_FILE, gs_data)
                            st.session_state.gs_dirty = True
                            st.session_state.gs_editor_ver += 1
                            st.rerun()


# ==============================================================================
# 탭 3: 메이플스토리 화면 (다음 단계 예정)
# ==============================================================================
with tab_maple:
    render_game_timer("maple", "메이플스토리", default_min=30)
    st.info("🍁 거상 테스트 완료 후, 마지막으로 메이플스토리 맞춤형 대시보드가 들어갑니다.")
