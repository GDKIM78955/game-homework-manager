import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import math
from datetime import datetime, timedelta
import pytz
from github import Github

st.set_page_config(page_title="통합 게임 숙제 & 수익 매니저", page_icon="🎮", layout="wide")

KST = pytz.timezone('Asia/Seoul')
LOA_FILE = "loa_data_v3.json"
GERSANG_FILE = "gersang_data_v1.json"
MAPLE_FILE = "maple_data_v1.json"

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

def fmt_man(val, unit="전"):
    try:
        v = float(val)
    except Exception:
        return f"0만 {unit}"
    sign = "-" if v < 0 else ""
    v_abs = abs(v)
    eok = int(v_abs // 10000)
    man = v_abs % 10000
    if eok > 0:
        if man == 0:
            return f"{sign}{eok:,}억 {unit}"
        elif man.is_integer():
            return f"{sign}{eok:,}억 {int(man):,}만 {unit}"
        else:
            return f"{sign}{eok:,}억 {man:,.1f}만 {unit}"
    else:
        if man.is_integer():
            return f"{sign}{int(man):,}만 {unit}"
        return f"{sign}{man:,.1f}만 {unit}"

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

def get_last_weekly_reset(now, reset_weekday=3, reset_hour=6):
    days_since = (now.weekday() - reset_weekday) % 7
    candidate = (now - timedelta(days=days_since)).replace(hour=reset_hour, minute=0, second=0, microsecond=0)
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
    last_reset = get_last_weekly_reset(now, reset_weekday, 6)
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
# 💰 2. 거상 데이터 및 로직
# ==============================================================================
PROFIT_LINK_OPTS = [
    "합산 안 함 (2클라 자체 자금만)",
    "이번 달 장사 순수익 합산",
    "누적 전체 장사 순수익 합산"
]

def create_initial_gersang(today_str):
    return {
        "last_daily_date": today_str,
        "daily_tasks": {"quest": False, "factory": False, "hunt_goal": False},
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
# 🍁 3. 메이플스토리 `mesu.live` 공식 확률/천장/분위수 엔진 및 데이터 (단위: 만 메소)
# ==============================================================================
# [1] 레벨 구간별 1회 잠재능력 재설정 정가표 (71~110제 미카엘라의 새 안경 포함!)
MAPLE_CUBE_COST_TABLE = {
    "윗잠 (잠재능력)": {
        "71~110제 (미카엘라 새안경/하프이어링 등)": {"레어": 320.0, "에픽": 1280.0, "유니크": 3060.0, "레전드리": 3600.0},
        "120~150제 (이벤링/보장/루타비스)": {"레어": 360.0, "에픽": 1440.0, "유니크": 3400.0, "레전드리": 4000.0},
        "160제 (여명/앱솔랩스)": {"레어": 425.0, "에픽": 1700.0, "유니크": 3825.0, "레전드리": 4500.0},
        "200제 (아케인셰이드/칠흑)": {"레어": 450.0, "에픽": 1800.0, "유니크": 4250.0, "레전드리": 5000.0},
        "250제 (에테르넬/광휘)": {"레어": 500.0, "에픽": 2000.0, "유니크": 4675.0, "레전드리": 5500.0},
    },
    "아랫잠 (에디셔널)": {
        "71~110제 (미카엘라 새안경/하프이어링 등)": {"레어": 1000.0, "에픽": 2800.0, "유니크": 6800.0, "레전드리": 8000.0},
        "120~150제 (이벤링/보장/루타비스)": {"레어": 1100.0, "에픽": 3080.0, "유니크": 7480.0, "레전드리": 8800.0},
        "160제 (여명/앱솔랩스)": {"레어": 1150.0, "에픽": 3220.0, "유니크": 7820.0, "레전드리": 9200.0},
        "200제 (아케인셰이드/칠흑)": {"레어": 1300.0, "에픽": 3640.0, "유니크": 8840.0, "레전드리": 10400.0},
        "250제 (에테르넬/광휘)": {"레어": 1450.0, "에픽": 4060.0, "유니크": 9860.0, "레전드리": 11600.0},
    }
}

# [2] `mesu.live` 동일 기준: 넥슨 공식 등업 확률(p) + 확정 등급업 천장 횟수(pity)
MAPLE_TIERUP_SPEC = {
    "윗잠 (잠재능력)": {
        "레어->에픽": {"p": 0.150000, "pity": 10},
        "에픽->유니크": {"p": 0.035000, "pity": 42},
        "유니크->레전드리": {"p": 0.014000, "pity": 107}
    },
    "아랫잠 (에디셔널)": {
        "레어->에픽": {"p": 0.047619, "pity": 31},
        "에픽->유니크": {"p": 0.019608, "pity": 76},
        "유니크->레전드리": {"p": 0.007000, "pity": 214}
    }
}

# [3] `mesu.live` 동일 기준: 주요 부위/옵션별 공식 결합 확률 (Prime Line 100% / 20% / 1% 결합 확률 % 적용)
MAPLE_MESU_OPTIONS = {
    "[레전드리/장신구] 드랍 or 메획 1줄 이상 (20%+)": {"prob_pct": 15.8200, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/장신구] 드랍+메획 총합 2줄 이상 (드메 2줄 핵심!)": {"prob_pct": 1.3960, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/장신구] 드랍 or 메획 1줄 + 주스탯 2줄": {"prob_pct": 1.1200, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/장신구] 드랍+메획 총합 3줄 (극옵 드메 3줄)": {"prob_pct": 0.0385, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/방어구·장신구] 주스탯 21% 이상 (올스탯 포함)": {"prob_pct": 6.4500, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/방어구·장신구] 주스탯 24% 이상 (정옵 2줄+)": {"prob_pct": 3.1800, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/방어구·장신구] 주스탯 27% 이상 (준3줄)": {"prob_pct": 1.5400, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/방어구·장신구] 주스탯 30% 이상 (3줄 정옵)": {"prob_pct": 0.5780, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/방어구·장신구] 주스탯 33% 이상 (극옵 3줄)": {"prob_pct": 0.2190, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/장갑] 크리티컬 데미지 1줄(8%) + 주스탯 1줄+": {"prob_pct": 5.6200, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/장갑] 크리티컬 데미지 2줄 (16% 이상)": {"prob_pct": 0.7420, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/모자] 쿨타임 감소 -2초 이상 (주스탯 무관)": {"prob_pct": 6.8500, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/모자] 쿨타임 감소 -2초 + 주스탯 1줄+": {"prob_pct": 2.9500, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/모자] 쿨타임 감소 -3초 이상": {"prob_pct": 1.4800, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/모자] 쿨타임 감소 -4초 이상": {"prob_pct": 0.3520, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/무보엠] 보공/방무/공마 유효 2줄": {"prob_pct": 8.3300, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/무보엠] 보공/공마 유효 3줄 (방무 제외)": {"prob_pct": 0.9120, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/무보엠] 공격력/마력 21% 이상 (2줄+)": {"prob_pct": 3.5800, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[레전드리/무보엠] 공격력/마력 30% 이상 (3줄)": {"prob_pct": 0.2640, "tier": "레전드리", "cube": "윗잠 (잠재능력)"},
    "[유니크/방어구·장신구] 주스탯 15% ~ 18% (유니크 2줄)": {"prob_pct": 6.6700, "tier": "유니크", "cube": "윗잠 (잠재능력)"},
    "[에픽/방어구·장신구] 주스탯 9% ~ 12% (에픽 2줄 토드용)": {"prob_pct": 10.2000, "tier": "에픽", "cube": "윗잠 (잠재능력)"},
    "[아랫잠/에픽] 공/마 +10 또는 주스탯 4%+ (에디 유효 1.5~2줄)": {"prob_pct": 5.5500, "tier": "에픽", "cube": "아랫잠 (에디셔널)"},
    "[아랫잠/유니크] 에디 주스탯 2줄 or 공/마 +2줄": {"prob_pct": 2.2200, "tier": "유니크", "cube": "아랫잠 (에디셔널)"},
    "[아랫잠/레전드리] 에디 주스탯 2.5~3줄 (렙당스탯/공마 포함)": {"prob_pct": 0.7690, "tier": "레전드리", "cube": "아랫잠 (에디셔널)"},
    "[아랫잠/무보엠] 에디 공격력/마력 21% 이상 (2줄)": {"prob_pct": 1.8180, "tier": "레전드리", "cube": "아랫잠 (에디셔널)"},
    "🔗 mesu.live 세부 조합 확률(%) 또는 평균 횟수 직접 입력": {"prob_pct": None, "tier": "레전드리", "cube": "윗잠 (잠재능력)"}
}

TIER_ORDER = ["레어", "에픽", "유니크", "레전드리"]

# 절단 기하분포(천장 반영) 기반 등급업 기대 횟수 및 분위수(50%, 85%, 95%) 산출 함수
def calc_mesu_tierup(cube_type, lv_bracket, start_tier, target_tier, is_miracle=False):
    s_idx = TIER_ORDER.index(start_tier)
    t_idx = TIER_ORDER.index(target_tier)
    if s_idx >= t_idx:
        return {"mean_cost": 0.0, "mean_tries": 0.0, "p50_cost": 0.0, "p85_cost": 0.0, "p95_cost": 0.0, "ceil_cost": 0.0}

    mean_cost, mean_tries = 0.0, 0.0
    p50_cost, p85_cost, p95_cost, ceil_cost = 0.0, 0.0, 0.0, 0.0

    for idx in range(s_idx, t_idx):
        cur_t = TIER_ORDER[idx]
        nxt_t = TIER_ORDER[idx + 1]
        spec = MAPLE_TIERUP_SPEC[cube_type][f"{cur_t}->{nxt_t}"]
        p = min(1.0, spec["p"] * (2.0 if is_miracle else 1.0))
        N = spec["pity"]
        unit_c = MAPLE_CUBE_COST_TABLE[cube_type][lv_bracket][cur_t]

        # 천장 N회가 반영된 절단 기하분포 공식: E[X] = (1 - (1-p)^N) / p
        exp_t = (1.0 - ((1.0 - p) ** N)) / p if p < 1.0 else 1.0
        
        def quantile_t(q):
            if p >= 1.0:
                return 1
            raw_k = math.ceil(math.log(1.0 - q) / math.log(1.0 - p))
            return min(N, max(1, raw_k))

        mean_tries += exp_t
        mean_cost += exp_t * unit_c
        p50_cost += quantile_t(0.50) * unit_c
        p85_cost += quantile_t(0.85) * unit_c
        p95_cost += quantile_t(0.95) * unit_c
        ceil_cost += N * unit_c

    return {
        "mean_cost": mean_cost,
        "mean_tries": mean_tries,
        "p50_cost": p50_cost,
        "p85_cost": p85_cost,
        "p95_cost": p95_cost,
        "ceil_cost": ceil_cost
    }

# 옵션 뽑기 기하분포(기댓값 / 50% 중앙값 / 85% 안전선 / 95% 억까선) 산출 함수
def calc_mesu_option_stats(prob_pct, unit_cost):
    p = max(0.000001, min(1.0, prob_pct / 100.0))
    mean_tries = 1.0 / p
    
    def q_tries(q):
        if p >= 1.0:
            return 1
        return max(1, math.ceil(math.log(1.0 - q) / math.log(1.0 - p)))

    t50 = q_tries(0.50)
    t85 = q_tries(0.85)
    t95 = q_tries(0.95)

    return {
        "prob_pct": prob_pct,
        "mean_tries": mean_tries,
        "mean_cost": mean_tries * unit_cost,
        "t50": t50, "p50_cost": t50 * unit_cost,
        "t85": t85, "p85_cost": t85 * unit_cost,
        "t95": t95, "p95_cost": t95 * unit_cost,
    }

def create_initial_maple(now_str, today_str):
    return {
        "last_weekly_reset": now_str,
        "last_daily_date": today_str,
        "fee_rate": 0.03,
        "accounts": [
            {"id": 1, "명의명": "1번 본계정 (루나 / 유니온 8500 / Lv.285)", "결정석완료": False, "결정석수익": 15000.0, "일일메소완료": False, "전문기술피로도": False, "메모": "본캐 주간보스 1캐릭 몰아주기"},
            {"id": 2, "명의명": "2번 부계정 A (루나 / 유니온 2500 / Lv.284)", "결정석완료": False, "결정석수익": 12000.0, "일일메소완료": False, "전문기술피로도": False, "메모": "부계정 보스 & 피로도"},
            {"id": 3, "명의명": "3번 부계정 B (루나 / 유니온 3000 / Lv.284)", "결정석완료": False, "결정석수익": 12000.0, "일일메소완료": False, "전문기술피로도": False, "메모": "부계정 보스 & 피로도"},
        ],
        "hunting_cfg": {
            "pure_meso_hr": 5500.0,
            "frag_price": 650.0,
            "frags_per_hr": 15.0,
            "extra_drops_hr": 300.0,
            "consumable_hr": 400.0
        },
        "alchemy_cfg": {
            "oil_price": 45.0,
            "crystal_price": 80.0,
            "exp_recipe_price": 1500.0,
            "drop_recipe_price": 1200.0,
            "crafts_per_recipe": 30.0,
            "bottle_etc_price": 15.0
        },
        "biz_methods": [
            {"id": 1, "활성": True, "돈벌이명": "🧪 연금술: 경험 축적의 비약(경축비) 제작", "원가(만)": 815.0, "판매가(만)": 950.0, "시간당횟수": 30.0, "메모": "왼쪽 원가 계산기에서 자동 연동 가능"},
            {"id": 2, "활성": True, "돈벌이명": "🧪 연금술: 재물 획득의 비약(재획비) 제작", "원가(만)": 680.0, "판매가(만)": 820.0, "시간당횟수": 30.0, "메모": "왼쪽 원가 계산기에서 자동 연동 가능"},
            {"id": 3, "활성": True, "돈벌이명": "👓 미카엘라의 새 안경(90제) 제작/합성/드메 장사", "원가(만)": 1500.0, "판매가(만)": 3500.0, "시간당횟수": 10.0, "메모": "90제 드메템 스테디셀러"},
            {"id": 4, "활성": True, "돈벌이명": "🔨 에픽 2줄 토드 장사 (160/200제)", "원가(만)": 8000.0, "판매가(만)": 12500.0, "시간당횟수": 4.0, "메모": "토드용 베이스 매입 후 재판매"},
        ],
        "meso_market_cfg": {
            "shift_pct": 0.0,
            "band_threshold": 5.0,
            "current_watch_rate": 2400.0
        },
        "meso_rate_logs": [
            {"id": 1, "날짜": today_str, "시세(1억당메포)": 2400.0, "메모": "초기 기준 시세 기록"}
        ],
        "meso_market": [],
        "saved_evals": [],
        "maple_trades": []
    }

def ensure_maple_schema(data):
    now = datetime.now(KST)
    now_str = now.isoformat()
    today_str = now.strftime("%Y-%m-%d")
    if not isinstance(data, dict) or "accounts" not in data:
        return create_initial_maple(now_str, today_str)

    data.setdefault("last_weekly_reset", now_str)
    data.setdefault("last_daily_date", today_str)
    data.setdefault("fee_rate", 0.03)
    data.setdefault("saved_evals", [])
    data.setdefault("maple_trades", [])
    data.setdefault("meso_market", [])
    data.setdefault("meso_rate_logs", [])

    mm_cfg = data.setdefault("meso_market_cfg", {})
    mm_cfg.setdefault("shift_pct", 0.0)
    mm_cfg.setdefault("band_threshold", 5.0)
    mm_cfg.setdefault("current_watch_rate", 2400.0)

    last_w_reset = get_last_weekly_reset(now, reset_weekday=3, reset_hour=0)
    try:
        last_w_check = datetime.fromisoformat(data["last_weekly_reset"])
        if last_w_check.tzinfo is None:
            last_w_check = KST.localize(last_w_check)
    except Exception:
        last_w_check = now

    changed = False
    if last_w_check < last_w_reset:
        for acc in data.get("accounts", []):
            acc["결정석완료"] = False
        data["last_weekly_reset"] = now_str
        changed = True

    if data["last_daily_date"] != today_str:
        for acc in data.get("accounts", []):
            acc["일일메소완료"] = False
            acc["전문기술피로도"] = False
        data["last_daily_date"] = today_str
        changed = True

    h_cfg = data.setdefault("hunting_cfg", {})
    h_cfg.setdefault("pure_meso_hr", 5500.0)
    h_cfg.setdefault("frag_price", 650.0)
    h_cfg.setdefault("frags_per_hr", 15.0)
    h_cfg.setdefault("extra_drops_hr", 300.0)
    h_cfg.setdefault("consumable_hr", 400.0)

    alc_cfg = data.setdefault("alchemy_cfg", {})
    alc_cfg.setdefault("oil_price", 45.0)
    alc_cfg.setdefault("crystal_price", 80.0)
    alc_cfg.setdefault("exp_recipe_price", 1500.0)
    alc_cfg.setdefault("drop_recipe_price", 1200.0)
    alc_cfg.setdefault("crafts_per_recipe", 30.0)
    alc_cfg.setdefault("bottle_etc_price", 15.0)

    data.setdefault("biz_methods", [])
    if changed:
        save_json_local(MAPLE_FILE, data)
    return data

def load_maple_data():
    now = datetime.now(KST)
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(MAPLE_FILE)
            return ensure_maple_schema(json.loads(contents.decoded_content.decode("utf-8")))
        except Exception:
            return create_initial_maple(now.isoformat(), now.strftime("%Y-%m-%d"))
    else:
        try:
            with open(MAPLE_FILE, "r", encoding="utf-8") as f:
                return ensure_maple_schema(json.load(f))
        except Exception:
            return create_initial_maple(now.isoformat(), now.strftime("%Y-%m-%d"))


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

if "maple_data" not in st.session_state:
    st.session_state.maple_data = load_maple_data()
if "mp_dirty" not in st.session_state:
    st.session_state.mp_dirty = False
if "mp_editor_ver" not in st.session_state:
    st.session_state.mp_editor_ver = 0

st.session_state.loa_data_v3 = process_loa_updates(st.session_state.loa_data_v3)
loa_data = st.session_state.loa_data_v3
gs_data = ensure_gersang_schema(st.session_state.gersang_data)
mp_data = ensure_maple_schema(st.session_state.maple_data)

st.title("🎮 나만의 게임 숙제 & 수익 관리 매니저")
tab_loa, tab_gersang, tab_maple = st.tabs([
    "⚓ 로스트아크 (25서버)",
    "💰 천하제일상 거상 (2클라+장사)",
    "🍁 메이플스토리 (3명의+mesu판독기+연금술+메소마켓)"
])

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
# 탭 2: 천하제일상 거상 화면 (무삭제 풀버전)
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
            m2.metric("🔥 앞으로 더 필요한 금액", fmt_man(shortfall), "목표 달성!" if shortfall == 0 else f"가용 자금 {fmt_man(effective_money)} 반영")

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
                    st.dataframe(pd.DataFrame(m_rows)[["월(YYYY-MM)", "판매 건수", "순수익 환산", "수익률", "총 매입원가(만)", "총 매출(만)"]], use_container_width=True, hide_index=True)

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
                            "id": new_id, "item_name": in_item.strip(), "buy_price": float(in_price),
                            "qty": int(in_qty), "buy_date": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                            "status": "보유중", "sell_price": 0.0, "sell_date": "", "net_profit": 0.0
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
                    st.caption(f"💡 **[{in_item.strip()}] 내 과거 족보:** 평균 매입가 **{fmt_man(avg_b)}** | 최고 비싸게 산 금액 **{fmt_man(max_b)}** | 최저 매입가 **{fmt_man(min_b)}** (누적 {tot_q}개 거래)")

            st.divider()

            st.markdown("##### 📦 2. 현재 보유 매물장 (더블클릭해 이름/산 가격/수량 바로 수정 가능!)")
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
                    if bp > item_stats[nm]["max"]: item_stats[nm]["max"] = bp

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
                        "id": t["id"], "아이템명": nm, "산가격(만)": bp, "보유수량": q,
                        "내평균가(만)": round(avg_p, 1), "내최고가(만)": max_p,
                        "손익분기(2%)": f"{breakeven:,}만 (5%:{rec_5:,}만)", "판수량": q,
                        "판매가입력(만)": bp if float(t.get("sell_price", 0)) == 0 else float(t["sell_price"]),
                        "판매완료": False, "삭제": False
                    })

                hold_df = pd.DataFrame(hold_rows)
                edited_hold = st.data_editor(
                    hold_df,
                    column_config={
                        "id": None,
                        "아이템명": st.column_config.TextColumn("✏️아이템명", width="small"),
                        "산가격(만)": st.column_config.NumberColumn("✏️산 가격(만)", width="small", min_value=0.0, step=100.0, format="%d만"),
                        "보유수량": st.column_config.NumberColumn("✏️보유수량", width="small", min_value=1, step=1),
                        "내평균가(만)": st.column_config.NumberColumn("내 평단가", width="small", format="%d만", disabled=True),
                        "내최고가(만)": st.column_config.NumberColumn("최고매입가", width="small", format="%d만", disabled=True),
                        "손익분기(2%)": st.column_config.TextColumn("2%본전(5%추천)", width="medium", disabled=True),
                        "판수량": st.column_config.NumberColumn("✏️판 수량", width="small", min_value=1, step=1),
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
                    if not orig_t: continue
                    if bool(erow["삭제"]):
                        trades.remove(orig_t)
                        hold_changed = True
                        continue

                    new_nm = str(erow["아이템명"]).strip() if not pd.isna(erow["아이템명"]) else orig_t["item_name"]
                    new_bp = float(erow["산가격(만)"]) if not pd.isna(erow["산가격(만)"]) else float(orig_t["buy_price"])
                    new_bq = max(1, int(erow["보유수량"])) if not pd.isna(erow["보유수량"]) else int(orig_t.get("qty", 1))
                    if new_nm != orig_t["item_name"] or new_bp != float(orig_t["buy_price"]) or new_bq != int(orig_t.get("qty", 1)):
                        orig_t["item_name"] = new_nm
                        orig_t["buy_price"] = new_bp
                        orig_t["qty"] = new_bq
                        hold_changed = True

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
                                "id": new_id, "item_name": orig_t["item_name"], "buy_price": bp, "qty": sell_q,
                                "buy_date": orig_t.get("buy_date", ""), "status": "판매완료", "sell_price": sp,
                                "sell_date": now_str_sell, "net_profit": net
                            })
                        else:
                            orig_t["sell_price"] = sp
                            orig_t["sell_date"] = now_str_sell
                            orig_t["net_profit"] = net
                            orig_t["status"] = "판매완료"
                        hold_changed = True

                if hold_changed:
                    save_json_local(GERSANG_FILE, gs_data)
                    st.session_state.gs_dirty = True
                    st.session_state.gs_editor_ver += 1
                    st.rerun()

            st.divider()

            with st.expander("📖 3. 나의 매입 족보 & 과거 기록 수정/복구", expanded=False):
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
                            "아이템명": nm, "누적매입": f"{jb['총 매입수량']}개",
                            "내 평균매입가": f"{int(avg_buy):,}만 ({fmt_man(avg_buy)})",
                            "최고비싸게산값": f"{int(jb['최고 매입가']):,}만",
                            "최저매입가": f"{int(jb['최저 매입가']):,}만",
                            "2%본전판매가": f"{be_price:,}만", "평균판매가": avg_sell_str,
                            "누적순수익": fmt_man(jb["누적 순수익"]), "최근매입일": jb["최근 거래일"]
                        })

                    search_kw = st.text_input("🔍 족보/과거기록 아이템 이름 검색", key="gs_jokbo_search")
                    jokbo_df = pd.DataFrame(jokbo_rows)
                    if search_kw.strip():
                        jokbo_df = jokbo_df[jokbo_df["아이템명"].str.contains(search_kw.strip(), case=False, na=False)]
                    st.dataframe(jokbo_df, use_container_width=True, hide_index=True)

                    hist_rows = []
                    for t in sorted(trades, key=lambda x: x.get("id", 0), reverse=True):
                        if search_kw.strip() and search_kw.strip().lower() not in t["item_name"].lower():
                            continue
                        hist_rows.append({
                            "id": t["id"], "상태": "🟢판매완료" if t.get("status") == "판매완료" else "📦보유중",
                            "아이템명": t["item_name"], "수량": int(t.get("qty", 1)),
                            "산가격(만)": float(t["buy_price"]), "판가격(만)": float(t.get("sell_price", 0.0)),
                            "순수익": fmt_man(t.get("net_profit", 0)) if t.get("status") == "판매완료" else "-",
                            "매입일시": t.get("buy_date", ""), "보유중복구": False, "삭제": False
                        })
                    if hist_rows:
                        edited_hist = st.data_editor(
                            pd.DataFrame(hist_rows),
                            column_config={
                                "id": None,
                                "상태": st.column_config.TextColumn("상태", width="small", disabled=True),
                                "아이템명": st.column_config.TextColumn("✏️아이템명", width="small"),
                                "수량": st.column_config.NumberColumn("✏️수량", width="small", min_value=1, step=1),
                                "산가격(만)": st.column_config.NumberColumn("✏️산 가격(만)", width="small", min_value=0.0, step=100.0, format="%d만"),
                                "판가격(만)": st.column_config.NumberColumn("✏️판 가격(만)", width="small", min_value=0.0, step=100.0, format="%d만"),
                                "순수익": st.column_config.TextColumn("순수익(2%제외)", width="small", disabled=True),
                                "매입일시": st.column_config.TextColumn("매입일시", width="small", disabled=True),
                                "보유중복구": st.column_config.CheckboxColumn("↩️보유중복구", width="small"),
                                "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small")
                            },
                            use_container_width=True, hide_index=True,
                            key=f"gs_hist_editor_{st.session_state.gs_editor_ver}"
                        )
                        trade_map = {t["id"]: t for t in trades}
                        hist_changed = False
                        for _, hrow in edited_hist.iterrows():
                            tid = int(hrow["id"])
                            orig_t = trade_map.get(tid)
                            if not orig_t: continue
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
# 탭 3: 🍁 메이플스토리 화면 (`mesu.live` 공식 확률/천장/분위수 엔진 + 가이드북 + 메소마켓 %보정 + 족보)
# ==============================================================================
with tab_maple:
    render_game_timer("maple", "메이플스토리", default_min=30)

    with st.container(border=True):
        mp_top1, mp_top2, mp_top3 = st.columns([2.2, 2.0, 1.5])
        with mp_top1:
            st.markdown("**🍁 루나 서버 3명의 통합 관리** (주간보스: 목요일 00시 리셋 / 일일사냥·피로도: 매일 00시 리셋)")
        with mp_top2:
            fee_choice = st.radio(
                "경매장 수수료율 설정",
                ["MVP 실버 이상 (3%)", "일반 유저 (5%)"],
                index=0 if float(mp_data.get("fee_rate", 0.03)) == 0.03 else 1,
                horizontal=True, label_visibility="collapsed"
            )
            new_fee = 0.03 if "3%" in fee_choice else 0.05
            if new_fee != float(mp_data.get("fee_rate", 0.03)):
                mp_data["fee_rate"] = new_fee
                save_json_local(MAPLE_FILE, mp_data)
                st.session_state.mp_dirty = True
                st.rerun()
        with mp_top3:
            mp_btn_label = "💾 메이플 깃허브 백업 (미저장*)" if st.session_state.mp_dirty else "💾 메이플 깃허브 백업 (완료)"
            mp_btn_type = "primary" if st.session_state.mp_dirty else "secondary"
            if st.button(mp_btn_label, type=mp_btn_type, use_container_width=True, key="save_mp_gh"):
                if save_json_github(MAPLE_FILE, mp_data, "Update Maple data"):
                    st.session_state.mp_dirty = False
                    st.toast("✅ 메이플스토리 데이터가 깃허브에 영구 저장되었습니다!")
                    st.rerun()

    # 1. 3개 명의 주간/일일 관리 표
    acc_df = pd.DataFrame(mp_data["accounts"])
    edited_acc = st.data_editor(
        acc_df[["id", "명의명", "결정석완료", "결정석수익", "일일메소완료", "전문기술피로도", "메모"]],
        column_config={
            "id": None,
            "명의명": st.column_config.TextColumn("✏️ 명의(계정) 구분", width="medium"),
            "결정석완료": st.column_config.CheckboxColumn("💎 주간 결정석(1캐릭) 완료", width="small"),
            "결정석수익": st.column_config.NumberColumn("✏️ 주간 보스 수익(만 메소)", width="small", min_value=0.0, step=500.0, format="%d만"),
            "일일메소완료": st.column_config.CheckboxColumn("🪙 오늘 사냥 메소제한 완료", width="small"),
            "전문기술피로도": st.column_config.CheckboxColumn("🧪 오늘 제작/채집 피로도 소모", width="small"),
            "메모": st.column_config.TextColumn("✏️ 메모", width="medium")
        },
        use_container_width=True, hide_index=True,
        key=f"mp_acc_editor_{st.session_state.mp_editor_ver}"
    )

    acc_changed = False
    for idx, r in edited_acc.iterrows():
        orig_a = mp_data["accounts"][idx]
        if (str(r["명의명"]) != orig_a["명의명"] or bool(r["결정석완료"]) != orig_a["결정석완료"] or
            float(r["결정석수익"]) != float(orig_a["결정석수익"]) or bool(r["일일메소완료"]) != orig_a["일일메소완료"] or
            bool(r["전문기술피로도"]) != orig_a["전문기술피로도"] or str(r["메모"]) != orig_a["메모"]):
            orig_a["명의명"] = str(r["명의명"])
            orig_a["결정석완료"] = bool(r["결정석완료"])
            orig_a["결정석수익"] = float(r["결정석수익"])
            orig_a["일일메소완료"] = bool(r["일일메소완료"])
            orig_a["전문기술피로도"] = bool(r["전문기술피로도"])
            orig_a["메모"] = str(r["메모"])
            acc_changed = True
    if acc_changed:
        save_json_local(MAPLE_FILE, mp_data)
        st.session_state.mp_dirty = True
        st.rerun()

    tot_boss_done = sum(float(a["결정석수익"]) for a in mp_data["accounts"] if a["결정석완료"])
    tot_boss_all = sum(float(a["결정석수익"]) for a in mp_data["accounts"])
    st.caption(f"💎 **이번 주 3명의 결정석 정산 현황:** 완료 **{fmt_man(tot_boss_done, '메소')}** / 전체 예상 **{fmt_man(tot_boss_all, '메소')}** | 모든 금액 단위는 **`만 메소`**입니다.")

    mp_sub1, mp_sub2, mp_sub3, mp_sub4 = st.tabs([
        "🏆 1. 사냥 vs 장사 시급 판독기 & 🧪 비약 원가 계산기",
        "🎲 2. mesu.live 공식 확률/천장 직작 판독기 & 📚 AI 산출 가이드북",
        "💱 3. 메소마켓 (시세 일지 & 외부요인 % 보정 & AI 매매 추천)",
        "📖 4. 메이플 장사 가계부 & 시세 족보 (월별 달력)"
    ])

    fee_mult = 1.0 - float(mp_data.get("fee_rate", 0.03))
    fee_pct_str = "3%" if float(mp_data.get("fee_rate", 0.03)) == 0.03 else "5%"

    # --------------------------------------------------------------------------
    # 🏆 [서브탭 1] 사냥 시급 판독기 + 연금술 비약 원가 계산기
    # --------------------------------------------------------------------------
    with mp_sub1:
        col_m1, col_m2 = st.columns([1.05, 1.35], gap="large")

        with col_m1:
            with st.container(border=True):
                st.subheader("⚔️ 오늘의 재획(사냥) 시급 계산")
                hc = mp_data["hunting_cfg"]
                h1, h2 = st.columns(2)
                with h1:
                    frag_p = st.number_input("💎 솔 에르다 조각 시세 (만 메소)", min_value=0.0, value=float(hc["frag_price"]), step=10.0, format="%.0f")
                    pure_m = st.number_input("🪙 1시간 순메소 획득량 (만 메소)", min_value=0.0, value=float(hc["pure_meso_hr"]), step=100.0, format="%.0f")
                with h2:
                    frag_cnt = st.number_input("📦 1시간 평균 조각 획득량 (개)", min_value=0.0, value=float(hc["frags_per_hr"]), step=1.0, format="%.1f")
                    extra_d = st.number_input("🎁 시간당 기타 드랍 수익 (만 메소)", min_value=0.0, value=float(hc["extra_drops_hr"]), step=50.0, format="%.0f")
                cons_c = st.number_input("🧪 1시간 도핑 원가 (재획/경축/익골 등, 만 메소)", min_value=0.0, value=float(hc["consumable_hr"]), step=50.0, format="%.0f")

                if (frag_p != hc["frag_price"] or pure_m != hc["pure_meso_hr"] or
                    frag_cnt != hc["frags_per_hr"] or extra_d != hc["extra_drops_hr"] or cons_c != hc["consumable_hr"]):
                    hc["frag_price"] = frag_p; hc["pure_meso_hr"] = pure_m; hc["frags_per_hr"] = frag_cnt
                    hc["extra_drops_hr"] = extra_d; hc["consumable_hr"] = cons_c
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True

                frag_net_hr = (frag_p * frag_cnt) * fee_mult
                extra_net_hr = extra_d * fee_mult
                hunt_hourly_net = pure_m + frag_net_hr + extra_net_hr - cons_c

                st.divider()
                st.metric("🔥 오늘 내 사냥(재획) 순수 시급", fmt_man(hunt_hourly_net, "메소"), f"1소재(30분): {fmt_man(hunt_hourly_net/2, '메소')}")

            with st.container(border=True):
                st.subheader("🧪 연금술 비약(경축비/재획비) 재료 & 레시피 원가 계산기")
                st.caption("인게임 경매장의 재료 시세와 비싼 제작 레시피 가격을 입력하면 1회 제작당 정확한 총원가를 계산해 오른쪽 시급 표에 바로 넣어줍니다!")
                alc = mp_data["alchemy_cfg"]

                ac1, ac2 = st.columns(2)
                with ac1:
                    oil_p = st.number_input("🌿 쥬니퍼베리 씨앗 오일 1개 (만)", min_value=0.0, value=float(alc["oil_price"]), step=1.0, format="%.1f")
                    xtal_p = st.number_input("💎 최상급 아이템 결정 1개 (만)", min_value=0.0, value=float(alc["crystal_price"]), step=1.0, format="%.1f")
                    bottle_p = st.number_input("🧴 최고급 빈병/마법의가루 등 부재료 (만)", min_value=0.0, value=float(alc["bottle_etc_price"]), step=1.0, format="%.1f")
                with ac2:
                    exp_rec_p = st.number_input("📜 경축비 레시피 1장 구매가 (만)", min_value=0.0, value=float(alc["exp_recipe_price"]), step=50.0, format="%.0f")
                    drop_rec_p = st.number_input("📜 재획비 레시피 1장 구매가 (만)", min_value=0.0, value=float(alc["drop_recipe_price"]), step=50.0, format="%.0f")
                    rec_uses = st.number_input("🔄 레시피 1장(유효기간 1일)당 총 제작 횟수", min_value=1.0, value=float(alc["crafts_per_recipe"]), step=5.0, format="%.0f")

                if (oil_p != alc["oil_price"] or xtal_p != alc["crystal_price"] or bottle_p != alc["bottle_etc_price"] or
                    exp_rec_p != alc["exp_recipe_price"] or drop_rec_p != alc["drop_recipe_price"] or rec_uses != alc["crafts_per_recipe"]):
                    alc["oil_price"] = oil_p; alc["crystal_price"] = xtal_p; alc["bottle_etc_price"] = bottle_p
                    alc["exp_recipe_price"] = exp_rec_p; alc["drop_recipe_price"] = drop_rec_p; alc["crafts_per_recipe"] = rec_uses
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True

                exp_unit_cost = round((oil_p * 6.0) + (xtal_p * 6.0) + bottle_p + (exp_rec_p / rec_uses), 1)
                drop_unit_cost = round((oil_p * 5.0) + (xtal_p * 5.0) + bottle_p + (drop_rec_p / rec_uses), 1)

                st.info(
                    f"📌 **1회 제작당 총 원가 (레시피 할부 원가 포함):**\n"
                    f"- 🧪 **경축비 1회 제작 원가:** **`{exp_unit_cost:,}만 메소`** (오일6+결정6+부재료 + 레시피 1회분 `{exp_rec_p/rec_uses:.1f}만`)\n"
                    f"- 🧪 **재획비 1회 제작 원가:** **`{drop_unit_cost:,}만 메소`** (오일5+결정5+부재료 + 레시피 1회분 `{drop_rec_p/rec_uses:.1f}만`)"
                )

                if st.button("⬆️ 이 계산된 원가를 오른쪽 장사 비교표에 자동 반영하기", use_container_width=True):
                    for b in mp_data["biz_methods"]:
                        if "경축비" in b["돈벌이명"]:
                            b["원가(만)"] = exp_unit_cost
                        elif "재획비" in b["돈벌이명"]:
                            b["원가(만)"] = drop_unit_cost
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.session_state.mp_editor_ver += 1
                    st.toast("✅ 경축비/재획비 원가가 오른쪽 비교표에 즉시 반영되었습니다!")
                    st.rerun()

        with col_m2:
            with st.container(border=True):
                st.subheader("🧪 당일 시세 장사/제작 종목별 시급 비교표")
                st.caption(f"재료 원가와 오늘 경매장 판매가를 입력하면 **수수료({fee_pct_str})를 뺀 건당 마진과 환산 시급**이 자동 계산됩니다! (하단 `+`로 종목 자유 추가)")

                biz_list = mp_data["biz_methods"]
                biz_rows = []
                for b in biz_list:
                    cost = float(b.get("원가(만)", 0))
                    sell = float(b.get("판매가(만)", 0))
                    freq = float(b.get("시간당횟수", 1))
                    unit_margin = round(sell * fee_mult - cost, 1)
                    hr_profit = round(unit_margin * freq, 1)
                    biz_rows.append({
                        "활성": bool(b.get("활성", True)), "돈벌이명": str(b.get("돈벌이명", "")),
                        "원가(만)": cost, "판매가(만)": sell, "시간당횟수": freq,
                        "건당순수익(만)": unit_margin, "환산시급(만)": hr_profit, "메모": str(b.get("메모", ""))
                    })

                edited_biz = st.data_editor(
                    pd.DataFrame(biz_rows) if biz_rows else pd.DataFrame(columns=["활성", "돈벌이명", "원가(만)", "판매가(만)", "시간당횟수", "건당순수익(만)", "환산시급(만)", "메모"]),
                    column_config={
                        "활성": st.column_config.CheckboxColumn("✅비교", width="small", default=True),
                        "돈벌이명": st.column_config.TextColumn("✏️ 종목명", width="medium", required=True),
                        "원가(만)": st.column_config.NumberColumn("✏️ 총 재료원가(만)", width="small", format="%.1f만"),
                        "판매가(만)": st.column_config.NumberColumn("✏️ 오늘 판매가(만)", width="small", format="%.1f만"),
                        "시간당횟수": st.column_config.NumberColumn("✏️ 시간당 횟수", width="small", format="%.1f회"),
                        "건당순수익(만)": st.column_config.NumberColumn(f"1회 마진({fee_pct_str}제외)", width="small", format="%.1f만", disabled=True),
                        "환산시급(만)": st.column_config.NumberColumn("🔥 환산 시급", width="small", format="%d만", disabled=True),
                        "메모": st.column_config.TextColumn("✏️ 메모", width="small")
                    },
                    num_rows="dynamic", use_container_width=True, hide_index=True,
                    key=f"mp_biz_editor_{st.session_state.mp_editor_ver}"
                )

                new_biz = []
                for idx, r in edited_biz.iterrows():
                    if pd.isna(r["돈벌이명"]) or str(r["돈벌이명"]).strip() == "": continue
                    new_biz.append({
                        "id": idx + 1, "활성": True if pd.isna(r["활성"]) else bool(r["활성"]),
                        "돈벌이명": str(r["돈벌이명"]), "원가(만)": float(r["원가(만)"]) if not pd.isna(r["원가(만)"]) else 0.0,
                        "판매가(만)": float(r["판매가(만)"]) if not pd.isna(r["판매가(만)"]) else 0.0,
                        "시간당횟수": float(r["시간당횟수"]) if not pd.isna(r["시간당횟수"]) else 1.0,
                        "메모": str(r["메모"]) if not pd.isna(r["메모"]) else ""
                    })
                if new_biz != mp_data["biz_methods"]:
                    mp_data["biz_methods"] = new_biz
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.rerun()

                candidates = [{"종목": "⚔️ 사냥 (재획 & 조각 파밍)", "시급": hunt_hourly_net}]
                for b in mp_data["biz_methods"]:
                    if b.get("활성", True):
                        um = float(b["판매가(만)"]) * fee_mult - float(b["원가(만)"])
                        candidates.append({"종목": b["돈벌이명"], "시급": um * float(b["시간당횟수"])})
                best = sorted(candidates, key=lambda x: x["시급"], reverse=True)[0]
                st.divider()
                if best["시급"] > hunt_hourly_net:
                    diff_m = best["시급"] - hunt_hourly_net
                    st.success(
                        f"🏆 **오늘의 AI 효율 판독 결과:** 지금 시세 기준으로는 사냥보다 **`[{best['종목']}]`**을(를) 돌리는 것이 시간당 **`+{fmt_man(diff_m, '메소')}`** 더 이득입니다! "
                        f"(1위 시급: **{fmt_man(best['시급'], '메소')}** vs 사냥 시급: **{fmt_man(hunt_hourly_net, '메소')}**)"
                    )
                else:
                    st.info(
                        f"🏆 **오늘의 AI 효율 판독 결과:** 오늘 시세에서는 제작/장사보다 **`[⚔️ 사냥(재획 & 조각 파밍)]`**을 도는 것이 시급 **`{fmt_man(hunt_hourly_net, '메소')}`**로 가장 효율적입니다!"
                    )

    # --------------------------------------------------------------------------
    # 🎲 [서브탭 2] `mesu.live` 공식 확률/천장/분위수 엔진 직작 판독기 & 📚 AI 가이드북
    # --------------------------------------------------------------------------
    with mp_sub2:
        st.markdown("#### 🎲 `mesu.live` 공식 확률·천장·분위수(50%/85%/95%) 이식 직작 판독기 & ✨ 미라클 데이 계산기")
        st.caption(
            "`mesu.live/calc/potential`과 동일한 **넥슨 공식 결합 확률(Prime Line 100%/20%/1%) + 등급업 천장(Guarantee) 절단 분포 + 50%/85%/95% 분위수 수식**이 적용되었습니다! "
            "(71~110제 미카엘라의 새 안경 3,600만 메소부터 250제 에테르넬까지 완벽 지원)"
        )

        e_col1, e_col2 = st.columns([1.15, 1.25], gap="large")

        with e_col1:
            with st.container(border=True):
                st.markdown("##### 📝 1. 판독할 아이템 & 목표 스탯(옵션) 선택")
                eval_item_name = st.text_input("아이템 이름", value="미카엘라의 새 안경 (90제) / 데이브레이크 펜던트")

                opt_preset = st.selectbox("🎯 목표 스탯(옵션) 선택 (mesu.live 공식 결합 확률 내장)", list(MAPLE_MESU_OPTIONS.keys()), index=1, key="mp_op")
                preset_info = MAPLE_MESU_OPTIONS[opt_preset]

                default_cube_idx = 0 if preset_info["cube"].startswith("윗잠") else 1
                c_e1, c_e2 = st.columns(2)
                with c_e1:
                    cube_type = st.selectbox("잠재능력 구분", list(MAPLE_CUBE_COST_TABLE.keys()), index=default_cube_idx, key="mp_ct")
                with c_e2:
                    lv_bracket = st.selectbox("착용 레벨 구간 (71~110제 미카엘라 포함!)", list(MAPLE_CUBE_COST_TABLE[cube_type].keys()), index=0, key="mp_lb")

                default_target_idx = TIER_ORDER.index(preset_info["tier"])
                c_e3, c_e4 = st.columns(2)
                with c_e3:
                    start_tier = st.selectbox("현재 시작 등급 (베이스 등급)", TIER_ORDER, index=1, key="mp_st")
                with c_e4:
                    target_tier = st.selectbox("목표 달성 등급", TIER_ORDER, index=default_target_idx, key="mp_tt")

                default_unit_cost = MAPLE_CUBE_COST_TABLE[cube_type][lv_bracket][target_tier]
                default_prob_pct = preset_info["prob_pct"] if preset_info["prob_pct"] is not None else 1.5000

                u_c1, u_c2 = st.columns(2)
                with u_c1:
                    roll_unit_cost = st.number_input(
                        f"💎 [{target_tier}] 1회 재설정 비용 (만 메소)",
                        min_value=10.0, value=float(default_unit_cost), step=100.0, format="%.0f",
                        help="인게임 최신 정가가 자동 입력됩니다. (90제 미카엘라 레전드리 = 3,600만 / 120제 = 4,000만)"
                    )
                with u_c2:
                    prob_pct_input = st.number_input(
                        "🎲 옵션 등장 공식 확률 (%)",
                        min_value=0.0001, max_value=100.0, value=float(default_prob_pct), step=0.1000, format="%.4f",
                        help="mesu.live에서 계산된 세부 옵션의 확률(%)을 그대로 입력하셔도 100% 동일하게 계산됩니다!"
                    )

                st.caption(f"👉 확률 **`{prob_pct_input:.4f}%`** 기준 평균 시도 횟수: **`{100.0/prob_pct_input:.1f}회`** | [🌐 mesu.live/calc/potential 바로 열기](https://mesu.live/calc/potential)")

                st.divider()
                st.markdown("##### 💰 2. 현재 경매장 가격 입력 (단위: 만 메소)")
                p_e1, p_e2 = st.columns(2)
                with p_e1:
                    base_item_price = st.number_input("🛒 노작(또는 시작 등급 베이스) 매입가 (만 메소)", min_value=0.0, value=1500.0, step=500.0, format="%.0f")
                    st.caption(f"환산: **{fmt_man(base_item_price, '메소')}**")
                with p_e2:
                    auction_finished_price = st.number_input("🏷️ 해당 스탯 완제품 현재 경매장 가격 (만 메소)", min_value=0.0, value=350000.0, step=5000.0, format="%.0f")
                    st.caption(f"환산: **{fmt_man(auction_finished_price, '메소')}**")

        with e_col2:
            with st.container(border=True):
                st.markdown("##### 📊 3. `mesu.live` 방식 4대 분포 산출 & 직작/장사 판정 결과")

                # 1) 옵션 통계 (기댓값 / 50% 중앙값 / 85% 안전선 / 95% 억까선)
                opt_st = calc_mesu_option_stats(prob_pct_input, roll_unit_cost)

                # 2) 등급업 통계 (천장 반영: 평일 vs 미라클 데이)
                tu_norm = calc_mesu_tierup(cube_type, lv_bracket, start_tier, target_tier, is_miracle=False)
                tu_mira = calc_mesu_tierup(cube_type, lv_bracket, start_tier, target_tier, is_miracle=True)

                # 3) 총 직작 기대 원가 (노작가 + 등업 기댓값 + 옵션 기댓값)
                total_craft_normal = base_item_price + tu_norm["mean_cost"] + opt_st["mean_cost"]
                total_craft_miracle = base_item_price + tu_mira["mean_cost"] + opt_st["mean_cost"]

                # 분위수별 총 직작 비용 (미라클 데이 기준 vs 평일 기준)
                dist_rows = [
                    {
                        "분포 구간 (mesu.live 기준)": "🎯 평균 기댓값 (Mean)",
                        "옵션 시도 횟수": f"평균 {opt_st['mean_tries']:.1f}회",
                        "평일 총 직작비": fmt_man(total_craft_normal, "메소"),
                        "✨미라클 총 직작비": fmt_man(total_craft_miracle, "메소")
                    },
                    {
                        "분포 구간 (mesu.live 기준)": "🍀 상위 50% 중앙값 (절반의 유저 달성)",
                        "옵션 시도 횟수": f"{opt_st['t50']:,}회 이내",
                        "평일 총 직작비": fmt_man(base_item_price + tu_norm["p50_cost"] + opt_st["p50_cost"], "메소"),
                        "✨미라클 총 직작비": fmt_man(base_item_price + tu_mira["p50_cost"] + opt_st["p50_cost"], "메소")
                    },
                    {
                        "분포 구간 (mesu.live 기준)": "🛡️ 상위 85% 안전선 (일반적 억까 상한)",
                        "옵션 시도 횟수": f"{opt_st['t85']:,}회 이내",
                        "평일 총 직작비": fmt_man(base_item_price + tu_norm["p85_cost"] + opt_st["p85_cost"], "메소"),
                        "✨미라클 총 직작비": fmt_man(base_item_price + tu_mira["p85_cost"] + opt_st["p85_cost"], "메소")
                    },
                    {
                        "분포 구간 (mesu.live 기준)": "⚠️ 상위 95% 억까 방지선 (하위 5% 불운)",
                        "옵션 시도 횟수": f"{opt_st['t95']:,}회 이내",
                        "평일 총 직작비": fmt_man(base_item_price + tu_norm["p95_cost"] + opt_st["p95_cost"], "메소"),
                        "✨미라클 총 직작비": fmt_man(base_item_price + tu_mira["p95_cost"] + opt_st["p95_cost"], "메소")
                    }
                ]

                r_c1, r_c2 = st.columns(2)
                r_c1.metric(
                    "📅 평일 직작 평균 기댓값",
                    fmt_man(total_craft_normal, "메소"),
                    f"등업(천장반영) {fmt_man(tu_norm['mean_cost'], '메소')} + 옵션 {fmt_man(opt_st['mean_cost'], '메소')}"
                )
                r_c2.metric(
                    "✨ 미라클 데이 직작 평균 기댓값",
                    fmt_man(total_craft_miracle, "메소"),
                    f"평일 대비 등업비 -{fmt_man(tu_norm['mean_cost'] - tu_mira['mean_cost'], '메소')} 절약!"
                )

                st.dataframe(pd.DataFrame(dist_rows), use_container_width=True, hide_index=True)

                net_sell_revenue = auction_finished_price * fee_mult
                flip_profit_normal = net_sell_revenue - total_craft_normal
                flip_profit_miracle = net_sell_revenue - total_craft_miracle
                self_use_diff_miracle = auction_finished_price - total_craft_miracle

                st.markdown(f"###### ⚖️ 판정 1: 만들어서 경매장에 `{fmt_man(auction_finished_price, '메소')}`에 팔 때 (장사꾼 관점)")
                if flip_profit_miracle > 0 and flip_profit_normal > 0:
                    st.success(
                        f"🟢 **[장사 강력 추천 - 만들만함!]** 평일에 만들어 팔아도 평균 **`+{fmt_man(flip_profit_normal, '메소')}`** 이득이며, "
                        f"**✨미라클 데이**에 제작해 팔면 평균 **`+{fmt_man(flip_profit_miracle, '메소')}`**의 순수익(수수료 {fee_pct_str} 제외)이 남습니다!"
                    )
                elif flip_profit_miracle > 0 and flip_profit_normal <= 0:
                    st.warning(
                        f"🟡 **[미라클 데이 전용 장사템!]** 평일에 만들면 평균 **`{fmt_man(flip_profit_normal, '메소')}` 적자**지만, "
                        f"**✨미라클 데이(등업 2배)**에 만들어서 팔면 평균 **`+{fmt_man(flip_profit_miracle, '메소')}` 흑자**로 전환됩니다! 미라클 데이에만 제작하세요."
                    )
                else:
                    st.error(
                        f"🔴 **[제작 장사 금지 - 적자 확정!]** 미라클 데이에 만들어도 평균 **`{fmt_man(flip_profit_miracle, '메소')}` 손해**입니다! "
                        f"(현재 경매장 완제품 가격 `{fmt_man(auction_finished_price, '메소')}`이 제작 기댓값보다 훨씬 저렴합니다.)"
                    )

                st.markdown("###### 🛒 판정 2: 내가 직접 쓰거나 사재기할 때 (직작 vs 경매장 완제품 구매)")
                if self_use_diff_miracle < 0:
                    st.info(
                        f"💡 **경매장 매물 구매 추천:** 미라클 데이 직작 원가(`{fmt_man(total_craft_miracle, '메소')}`)보다 경매장 가격(`{fmt_man(auction_finished_price, '메소')}`)이 "
                        f"**`{fmt_man(abs(self_use_diff_miracle), '메소')}` 더 쌉니다!** 직접 돌리지 마시고 경매장 매물을 사는 게 이득입니다."
                    )
                else:
                    st.info(
                        f"💡 **직작 우위:** 경매장 가격에 거품이 끼어 있습니다. 미라클 데이에 직접 만들면 경매장 구매가보다 평균 **`{fmt_man(self_use_diff_miracle, '메소')}`** 아낄 수 있습니다."
                    )

                if st.button("📌 이 판독 결과를 아래 비교 리스트에 저장해 두기", use_container_width=True):
                    mp_data["saved_evals"].append({
                        "아이템명": eval_item_name,
                        "부위/레벨": f"{cube_type[:2]} / {lv_bracket[:7]}",
                        "목표옵션": opt_preset,
                        "확률(%)": f"{prob_pct_input:.3f}%",
                        "노작가": fmt_man(base_item_price, "메소"),
                        "경매장완제가": fmt_man(auction_finished_price, "메소"),
                        "평일기대원가": fmt_man(total_craft_normal, "메소"),
                        "미라클기대원가": fmt_man(total_craft_miracle, "메소"),
                        "미라클장사마진": f"+{fmt_man(flip_profit_miracle, '메소')}" if flip_profit_miracle >= 0 else fmt_man(flip_profit_miracle, "메소"),
                        "판정": "🟢장사추천" if flip_profit_miracle > 0 else "🔴적자(완제구매)"
                    })
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.rerun()

        if mp_data.get("saved_evals"):
            with st.expander("📋 내가 저장해 둔 경매장 매물 vs 미라클 직작 비교 리스트", expanded=True):
                st.dataframe(pd.DataFrame(mp_data["saved_evals"]), use_container_width=True, hide_index=True)
                if st.button("🗑️ 저장된 비교 리스트 비우기"):
                    mp_data["saved_evals"] = []
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True; st.rerun()

        st.divider()

        # 📚 [가이드북] AI 직작 기댓값 산출 기준 데이터 & 전체 레벨별/옵션별 표준 원가 가이드라인 총람!
        with st.expander("📚 [가이드북] mesu.live 기준 AI 직작 기댓값 산출 데이터 & 전체 레벨별/옵션별 표준 원가 가이드라인 보기 (클릭해 열기)", expanded=False):
            st.markdown("##### 📌 1. 레벨 구간별 1회 잠재능력 재설정 비용 정가표 (71~110제 미카엘라 포함)")
            cost_guide_rows = []
            for c_type, brackets in MAPLE_CUBE_COST_TABLE.items():
                for brk, tiers in brackets.items():
                    cost_guide_rows.append({
                        "구분": c_type,
                        "레벨 구간 (대표 아이템)": brk,
                        "레어 1회": fmt_man(tiers["레어"], "메소"),
                        "에픽 1회": fmt_man(tiers["에픽"], "메소"),
                        "유니크 1회": fmt_man(tiers["유니크"], "메소"),
                        "레전드리 1회": fmt_man(tiers["레전드리"], "메소")
                    })
            st.dataframe(pd.DataFrame(cost_guide_rows), use_container_width=True, hide_index=True)

            st.markdown("##### 📌 2. 레벨 구간별 등급업(천장 시스템 반영) 기댓값 비교표 (`에픽 -> 레전드리` 및 `천장 확정 비용`)")
            tier_guide_rows = []
            for c_type, brackets in MAPLE_CUBE_COST_TABLE.items():
                for brk in brackets.keys():
                    ep_norm = calc_mesu_tierup(c_type, brk, "에픽", "레전드리", False)
                    ep_mira = calc_mesu_tierup(c_type, brk, "에픽", "레전드리", True)
                    tier_guide_rows.append({
                        "구분": c_type,
                        "레벨 구간": brk,
                        "에픽->레전 평균(평일)": fmt_man(ep_norm["mean_cost"], "메소"),
                        "에픽->레전 평균(✨미라클)": fmt_man(ep_mira["mean_cost"], "메소"),
                        "에픽->레전 50%중앙값(미라클)": fmt_man(ep_mira["p50_cost"], "메소"),
                        "에픽->레전 100%천장합계": fmt_man(ep_norm["ceil_cost"], "메소"),
                    })
            st.dataframe(pd.DataFrame(tier_guide_rows), use_container_width=True, hide_index=True)

            st.markdown("##### 📌 3. 25종 주요 스탯(옵션)별 공식 등장 확률(%) & 레벨 구간별 옵션 기대 비용 총람")
            st.caption("아래 표는 **해당 등급에서 순수하게 옵션을 띄우는 데 들어가는 평균 메소(50% 중앙값은 평균의 약 0.69배)**이며, 실제 직작 시에는 위 2번 표의 **등업 비용 + 노작 값**을 더한 금액이 총 제작 기댓값이 됩니다.")
            opt_guide_rows = []
            for opt_name, info in MAPLE_MESU_OPTIONS.items():
                if info["prob_pct"] is None:
                    continue
                p_pct = info["prob_pct"]
                c_key = info["cube"]
                t_key = info["tier"]
                tries = 100.0 / p_pct
                
                c_90 = tries * MAPLE_CUBE_COST_TABLE[c_key]["71~110제 (미카엘라 새안경/하프이어링 등)"][t_key]
                c_120 = tries * MAPLE_CUBE_COST_TABLE[c_key]["120~150제 (이벤링/보장/루타비스)"][t_key]
                c_160 = tries * MAPLE_CUBE_COST_TABLE[c_key]["160제 (여명/앱솔랩스)"][t_key]
                c_200 = tries * MAPLE_CUBE_COST_TABLE[c_key]["200제 (아케인셰이드/칠흑)"][t_key]
                c_250 = tries * MAPLE_CUBE_COST_TABLE[c_key]["250제 (에테르넬/광휘)"][t_key]

                opt_guide_rows.append({
                    "목표 옵션명": opt_name,
                    "구분/등급": f"{c_key[:2]} / {t_key}",
                    "공식 확률(%)": f"{p_pct:.4f}%",
                    "평균 시도": f"{tries:.1f}회",
                    "71~110제 (미카엘라)": fmt_man(c_90, "메소"),
                    "120~150제 (보장)": fmt_man(c_120, "메소"),
                    "160제 (여명/앱솔)": fmt_man(c_160, "메소"),
                    "200제 (아케인/칠흑)": fmt_man(c_200, "메소"),
                    "250제 (에테르넬)": fmt_man(c_250, "메소"),
                })
            st.dataframe(pd.DataFrame(opt_guide_rows), use_container_width=True, hide_index=True)

    # --------------------------------------------------------------------------
    # 💱 [서브탭 3] 메소마켓 (시세 일지 트래커 + 외부요인 % 일괄 보정 + AI 매수/매도 타이밍 판독기)
    # --------------------------------------------------------------------------
    with mp_sub3:
        st.markdown("#### 💱 메소마켓 시세 트래커 & 외부요인 `%` 보정 AI 매매 타이밍 판독기")
        st.caption(
            "거래를 직접 하지 않더라도 **평소 시세(1억 메소당 메포)만 꾸준히 기록**해 두세요! "
            "대규모 패치나 인플레이션 등 외부 요인으로 시세 레벨이 바뀌면 **`외부요인 보정 %`**만 조절해 과거 기준선 전체를 현재 가치로 자동 스케일링하고 매수/매도 타이밍을 판독합니다."
        )

        mm_cfg = mp_data["meso_market_cfg"]
        rate_logs = mp_data["meso_rate_logs"]

        col_mm_left, col_mm_right = st.columns([1.15, 1.25], gap="large")

        with col_mm_left:
            with st.container(border=True):
                st.markdown("##### 📝 1. 오늘 메소마켓 시세 기록하기 (단순 시세 관측 일지)")
                r_c1, r_c2, r_c3 = st.columns([1.2, 1.3, 1.5])
                with r_c1:
                    log_date = st.text_input("관측 날짜", value=datetime.now(KST).strftime("%Y-%m-%d %H:%M"), key="mm_log_dt")
                with r_c2:
                    log_rate = st.number_input("1억 메소당 메포 시세", min_value=500.0, value=float(mm_cfg.get("current_watch_rate", 2400.0)), step=20.0, format="%.0f", key="mm_log_rt")
                with r_c3:
                    log_memo = st.text_input("시세 메모 (선택)", placeholder="예: 썬데이, 방학패치 전, 사료배포", key="mm_log_mm")

                if st.button("➕ 오늘 시세 일지에 기록 저장", type="primary", use_container_width=True):
                    new_lid = max([x.get("id", 0) for x in rate_logs], default=0) + 1
                    rate_logs.append({
                        "id": new_lid,
                        "날짜": log_date,
                        "시세(1억당메포)": float(log_rate),
                        "메모": log_memo.strip()
                    })
                    mm_cfg["current_watch_rate"] = float(log_rate)
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.session_state.mp_editor_ver += 1
                    st.toast(f"✅ 메소마켓 시세(1억당 {int(log_rate):,} 메포)가 기록되었습니다!")
                    st.rerun()

                st.divider()
                st.markdown("##### ⚙️ 2. 외부 요인(인플레/패치/이벤트) 과거 기준선 `%` 일괄 보정")
                st.caption("예: 메소가 흔해져서 전체적으로 예전보다 1억당 메포 시세가 10% 떨어졌다면 `-10%`로 조절하세요. 과거에 기록했던 모든 평균/고점/저점 기준선이 `-10%`에 맞춰 자동 재계산됩니다!")

                s_c1, s_c2 = st.columns(2)
                with s_c1:
                    shift_pct = st.number_input(
                        "🎚️ 과거 기준선 일괄 변동률 (%)",
                        min_value=-80.0, max_value=200.0, value=float(mm_cfg.get("shift_pct", 0.0)), step=1.0, format="%.1f",
                        help="양수(+)면 과거 시세 기준선을 올리고, 음수(-)면 과거 시세 기준선을 낮춥니다."
                    )
                with s_c2:
                    band_th = st.number_input(
                        "🎯 매수/매도 추천 민감도 (±%)",
                        min_value=1.0, max_value=30.0, value=float(mm_cfg.get("band_threshold", 5.0)), step=0.5, format="%.1f",
                        help="보정된 평균 시세 대비 오늘 시세가 몇 % 이상 벌어졌을 때 추천 사인을 낼지 결정합니다."
                    )

                cur_watch = st.number_input(
                    "🔍 지금 당장 판독할 현재 인게임 메소마켓 시세 (1억당 메포)",
                    min_value=500.0, value=float(mm_cfg.get("current_watch_rate", 2400.0)), step=20.0, format="%.0f"
                )

                if (shift_pct != mm_cfg.get("shift_pct") or band_th != mm_cfg.get("band_threshold") or cur_watch != mm_cfg.get("current_watch_rate")):
                    mm_cfg["shift_pct"] = shift_pct
                    mm_cfg["band_threshold"] = band_th
                    mm_cfg["current_watch_rate"] = cur_watch
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True

        with col_mm_right:
            with st.container(border=True):
                st.markdown("##### 🤖 3. AI 메소마켓 매수/매도 타이밍 판독 결과")

                if not rate_logs:
                    st.info("왼쪽에서 시세 기록을 1개 이상 추가하시면 AI 기준선 분석이 시작됩니다.")
                else:
                    shift_mult = 1.0 + (shift_pct / 100.0)
                    raw_rates = [float(x["시세(1억당메포)"]) for x in rate_logs]
                    adj_rates = [r * shift_mult for r in raw_rates]

                    raw_avg = sum(raw_rates) / len(raw_rates)
                    adj_avg = sum(adj_rates) / len(adj_rates)
                    adj_max = max(adj_rates)
                    adj_min = min(adj_rates)

                    buy_mp_trigger = adj_avg * (1.0 + band_th / 100.0)
                    sell_mp_trigger = adj_avg * (1.0 - band_th / 100.0)
                    diff_pct_from_adj = ((cur_watch - adj_avg) / adj_avg) * 100.0 if adj_avg > 0 else 0.0

                    k_m1, k_m2, k_m3 = st.columns(3)
                    k_m1.metric("과거 원본 평균 시세", f"{raw_avg:,.0f} P", f"기록 {len(raw_rates)}건")
                    k_m2.metric(f"보정된 기준 평균 ({shift_pct:+.1f}%)", f"{adj_avg:,.0f} P", f"범위: {adj_min:,.0f}~{adj_max:,.0f}P")
                    k_m3.metric("오늘 시세 vs 보정 평균", f"{cur_watch:,.0f} P", f"{diff_pct_from_adj:+.1f}% 차이")

                    st.info(
                        f"🎯 **현재 외부요인({shift_pct:+.1f}%) 반영 AI 매매 가이드라인:**\n"
                        f"- 🔵 **메포 매수 추천선 (메소 팔아 메포 사기):** 1억당 **`{buy_mp_trigger:,.0f} 메포` 이상**일 때\n"
                        f"- ⚪ **관망(대기) 구간:** 1억당 **`{sell_mp_trigger:,.0f} ~ {buy_mp_trigger:,.0f} 메포`** 사이\n"
                        f"- 🔴 **메포 매도 추천선 (메포 팔아 메소 확보):** 1억당 **`{sell_mp_trigger:,.0f} 메포` 이하**일 때"
                    )

                    if cur_watch >= buy_mp_trigger:
                        st.success(
                            f"🔵 **[AI 강력 추천: 지금 메소를 팔아 '메이플포인트'를 매수하세요!]**\n\n"
                            f"현재 시세(`{cur_watch:,.0f} P`)가 보정된 과거 평균(`{adj_avg:,.0f} P`)보다 **`+{diff_pct_from_adj:.1f}%` 높은 고점**입니다! "
                            f"1억 메소로 평소보다 더 많은 메포를 살 수 있는 최적의 타이밍입니다."
                        )
                    elif cur_watch <= sell_mp_trigger:
                        st.error(
                            f"🔴 **[AI 강력 추천: 지금 보유한 '메이플포인트'를 팔아 메소를 확보하세요!]**\n\n"
                            f"현재 시세(`{cur_watch:,.0f} P`)가 보정된 과거 평균(`{adj_avg:,.0f} P`)보다 **`{diff_pct_from_adj:.1f}%` 낮은 저점(메포 가치 폭등)**입니다! "
                            f"지금 메포를 팔면 가장 적은 메포로 1억 메소를 바꿀 수 있는 최고 효율 구간입니다."
                        )
                    else:
                        st.warning(
                            f"🟡 **[AI 판정: 중립 / 관망 구간입니다]**\n\n"
                            f"현재 시세(`{cur_watch:,.0f} P`)가 보정 평균(`{adj_avg:,.0f} P`) 근처(`{diff_pct_from_adj:+.1f}%`)에서 움직이고 있습니다. "
                            f"급한 환전이 아니라면 `{buy_mp_trigger:,.0f} P` 이상 오르거나 `{sell_mp_trigger:,.0f} P` 이하로 내릴 때까지 기다리세요."
                        )

        st.divider()
        sub_c1, sub_c2 = st.columns(2, gap="large")

        with sub_c1:
            st.markdown("##### 📊 꾸준히 기록한 메소마켓 시세 일지 (과거 데이터 & 보정치 자동 표시)")
            if rate_logs:
                shift_mult = 1.0 + ( float(mm_cfg.get("shift_pct", 0.0)) / 100.0 )
                log_rows = []
                for x in sorted(rate_logs, key=lambda i: i.get("id", 0), reverse=True):
                    r_val = float(x.get("시세(1억당메포)", 2400.0))
                    log_rows.append({
                        "id": x["id"],
                        "날짜": str(x.get("날짜", "")),
                        "시세(1억당메포)": r_val,
                        "보정환산시세": round(r_val * shift_mult, 0),
                        "메모": str(x.get("메모", "")),
                        "삭제": False
                    })
                edited_logs = st.data_editor(
                    pd.DataFrame(log_rows),
                    column_config={
                        "id": None,
                        "날짜": st.column_config.TextColumn("✏️ 날짜", width="small"),
                        "시세(1억당메포)": st.column_config.NumberColumn("✏️ 기록 시세", format="%d P"),
                        "보정환산시세": st.column_config.NumberColumn(f"보정 시세({mm_cfg.get('shift_pct',0):+.1f}%)", format="%d P", disabled=True),
                        "메모": st.column_config.TextColumn("✏️ 메모", width="medium"),
                        "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small")
                    },
                    use_container_width=True, hide_index=True,
                    key=f"mm_rate_log_ed_{st.session_state.mp_editor_ver}"
                )
                l_map = {x["id"]: x for x in rate_logs}
                l_chg = False
                for _, r in edited_logs.iterrows():
                    orig_l = l_map.get(int(r["id"]))
                    if not orig_l: continue
                    if bool(r["삭제"]):
                        rate_logs.remove(orig_l); l_chg = True; continue
                    if (str(r["날짜"]) != orig_l["날짜"] or float(r["시세(1억당메포)"]) != float(orig_l["시세(1억당메포)"]) or str(r["메모"]) != orig_l.get("메모", "")):
                        orig_l["날짜"] = str(r["날짜"])
                        orig_l["시세(1억당메포)"] = float(r["시세(1억당메포)"])
                        orig_l["메모"] = str(r["메모"])
                        l_chg = True
                if l_chg:
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True; st.session_state.mp_editor_ver += 1; st.rerun()

        with sub_c2:
            st.markdown("##### 🧾 내 실제 메소마켓 매수/매도 체결 장부 (선택 사용)")
            mm_list = mp_data["meso_market"]
            t_c1, t_c2, t_c3, t_c4 = st.columns([1.5, 1.2, 1.2, 1.1])
            with t_c1:
                mm_action = st.selectbox("체결 구분", ["🔵 메포 매수", "🔴 메포 매도"], label_visibility="collapsed")
            with t_c2:
                mm_rate = st.number_input("체결 시세(P)", min_value=500.0, value=float(mm_cfg.get("current_watch_rate", 2400.0)), step=20.0, format="%.0f", label_visibility="collapsed")
            with t_c3:
                mm_eok = st.number_input("억 메소", min_value=0.1, value=10.0, step=1.0, format="%.1f", label_visibility="collapsed")
            with t_c4:
                if st.button("➕ 체결 등록", use_container_width=True):
                    new_mm_id = max([x.get("id", 0) for x in mm_list], default=0) + 1
                    mm_list.append({
                        "id": new_mm_id, "날짜": datetime.now(KST).strftime("%m/%d %H:%M"),
                        "구분": mm_action, "환율(1억당메포)": float(mm_rate),
                        "메소(억)": float(mm_eok), "총메이플포인트": int(mm_rate * mm_eok), "삭제": False
                    })
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True; st.rerun()

            if mm_list:
                mm_df = pd.DataFrame(mm_list)
                for col in ["id", "날짜", "구분", "환율(1억당메포)", "메소(억)", "총메이플포인트", "삭제"]:
                    if col not in mm_df.columns:
                        mm_df[col] = False if col == "삭제" else 0
                edited_mm = st.data_editor(
                    mm_df[["id", "날짜", "구분", "환율(1억당메포)", "메소(억)", "총메이플포인트", "삭제"]],
                    column_config={
                        "id": None,
                        "날짜": st.column_config.TextColumn("일시", width="small"),
                        "구분": st.column_config.TextColumn("구분", width="small"),
                        "환율(1억당메포)": st.column_config.NumberColumn("✏️ 체결시세", format="%d P"),
                        "메소(억)": st.column_config.NumberColumn("✏️ 규모(억)", format="%.1f억"),
                        "총메이플포인트": st.column_config.NumberColumn("총 메포", format="%d P", disabled=True),
                        "삭제": st.column_config.CheckboxColumn("🗑️", width="small")
                    },
                    use_container_width=True, hide_index=True, key=f"mp_mm_ed_{st.session_state.mp_editor_ver}"
                )
                mm_map = {x["id"]: x for x in mm_list}
                mm_chg = False
                for _, r in edited_mm.iterrows():
                    orig_m = mm_map.get(int(r["id"]))
                    if not orig_m: continue
                    if bool(r["삭제"]):
                        mm_list.remove(orig_m); mm_chg = True; continue
                    if float(r["환율(1억당메포)"]) != float(orig_m["환율(1억당메포)"]) or float(r["메소(억)"]) != float(orig_m["메소(억)"]):
                        orig_m["환율(1억당메포)"] = float(r["환율(1억당메포)"])
                        orig_m["메소(억)"] = float(r["메소(억)"])
                        orig_m["총메이플포인트"] = int(orig_m["환율(1억당메포)"] * orig_m["메소(억)"])
                        mm_chg = True
                if mm_chg:
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True; st.session_state.mp_editor_ver += 1; st.rerun()

    # --------------------------------------------------------------------------
    # 📖 [서브탭 4] 메이플 장사 가계부 & 시세 족보
    # --------------------------------------------------------------------------
    with mp_sub4:
        mp_trades = mp_data["maple_trades"]
        now_kst = datetime.now(KST)
        cur_ym = now_kst.strftime("%Y-%m")

        mp_holding = [t for t in mp_trades if t.get("status") == "보유중"]
        mp_sold = [t for t in mp_trades if t.get("status") == "판매완료"]

        mp_tied = sum(float(t.get("buy_price", 0)) * int(t.get("qty", 1)) for t in mp_holding)
        mp_month_profit = sum(float(t.get("net_profit", 0)) for t in mp_sold if str(t.get("sell_date", "")).startswith(cur_ym))
        mp_total_profit = sum(float(t.get("net_profit", 0)) for t in mp_sold)

        mk1, mk2, mk3 = st.columns(3)
        mk1.metric(f"📅 이번 달({cur_ym}) 메이플 장사 순수익", fmt_man(mp_month_profit, "메소"), f"경매장 수수료 {fee_pct_str} 공제 후")
        mk2.metric("🔒 현재 옥션/인벤 묶인 재고 자금", fmt_man(mp_tied, "메소"), f"보유 매물 {len(mp_holding)}건")
        mk3.metric("👑 누적 총 메이플 장사 순수익", fmt_man(mp_total_profit, "메소"), f"누적 판매 {len(mp_sold)}건")

        if mp_sold:
            mp_monthly_map = {}
            for t in mp_sold:
                ym = str(t.get("sell_date", "기타"))[:7]
                if ym not in mp_monthly_map:
                    mp_monthly_map[ym] = {"월(YYYY-MM)": ym, "판매 건수": 0, "총 매출(만)": 0.0, "총 매입원가(만)": 0.0, "순수익(만)": 0.0}
                qty = int(t.get("qty", 1))
                mp_monthly_map[ym]["판매 건수"] += 1
                mp_monthly_map[ym]["총 매출(만)"] += float(t.get("sell_price", 0)) * qty
                mp_monthly_map[ym]["총 매입원가(만)"] += float(t.get("buy_price", 0)) * qty
                mp_monthly_map[ym]["순수익(만)"] += float(t.get("net_profit", 0))
            
            mp_m_rows = sorted(mp_monthly_map.values(), key=lambda x: x["월(YYYY-MM)"], reverse=True)
            for mr in mp_m_rows:
                mr["순수익 환산"] = fmt_man(mr["순수익(만)"], "메소")
                mr["수익률"] = f"{(mr['순수익(만)'] / mr['총 매입원가(만)'] * 100):.1f}%" if mr["총 매입원가(만)"] > 0 else "0%"
            
            with st.expander("🗓️ 메이플 월별 장사 수익 달력 상세 보기", expanded=True):
                st.dataframe(pd.DataFrame(mp_m_rows)[["월(YYYY-MM)", "판매 건수", "순수익 환산", "수익률", "총 매입원가(만)", "총 매출(만)"]], use_container_width=True, hide_index=True)

        st.divider()

        st.markdown("##### 📥 1. 메이플 장사 물건 매입(또는 제작 원가) 등록하기")
        mb_c1, mb_c2, mb_c3, mb_c4 = st.columns([2, 1.5, 1, 1.2])
        with mb_c1:
            mp_in_item = st.text_input("아이템 이름", placeholder="예: 미카엘라의 새 안경(드메2줄), 경축비", key="mp_in_item")
        with mb_c2:
            mp_in_price = st.number_input("개당 산 가격/제작원가 (만 메소)", min_value=0.0, value=10000.0, step=500.0, format="%.0f", key="mp_in_price")
        with mb_c3:
            mp_in_qty = st.number_input("수량 (개)", min_value=1, value=1, step=1, key="mp_in_qty")
        with mb_c4:
            st.write("")
            if st.button("➕ 메이플 장부에 추가", type="primary", use_container_width=True):
                if mp_in_item.strip():
                    new_id = max([t.get("id", 0) for t in mp_trades], default=0) + 1
                    mp_trades.append({
                        "id": new_id, "item_name": mp_in_item.strip(), "buy_price": float(mp_in_price),
                        "qty": int(mp_in_qty), "buy_date": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
                        "status": "보유중", "sell_price": 0.0, "sell_date": "", "net_profit": 0.0
                    })
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.session_state.mp_editor_ver += 1
                    st.toast(f"✅ [{mp_in_item.strip()}] {fmt_man(mp_in_price, '메소')} × {mp_in_qty}개 등록 완료!")
                    st.rerun()
                else:
                    st.warning("아이템 이름을 입력해 주세요!")

        if mp_in_item.strip():
            same_mp_hist = [t for t in mp_trades if t.get("item_name") == mp_in_item.strip()]
            if same_mp_hist:
                tot_q = sum(int(t.get("qty", 1)) for t in same_mp_hist)
                avg_b = sum(float(t.get("buy_price", 0)) * int(t.get("qty", 1)) for t in same_mp_hist) / tot_q
                max_b = max(float(t.get("buy_price", 0)) for t in same_mp_hist)
                min_b = min(float(t.get("buy_price", 0)) for t in same_mp_hist)
                st.caption(f"💡 **[{mp_in_item.strip()}] 내 과거 족보:** 평균 매입가 **{fmt_man(avg_b, '메소')}** | 최고 매입가 **{fmt_man(max_b, '메소')}** | 최저 매입가 **{fmt_man(min_b, '메소')}** (누적 {tot_q}개 거래)")

        st.divider()

        st.markdown(f"##### 📦 2. 현재 보유 매물장 & 재판매 이득/손실 실시간 판독 (수수료 {fee_pct_str} 자동 반영)")
        if not mp_holding:
            st.info("현재 보유 중인 메이플 장사 매물이 없습니다.")
        else:
            mp_item_stats = {}
            for t in mp_trades:
                nm = t["item_name"]
                mp_item_stats.setdefault(nm, {"q": 0, "sum": 0.0, "max": 0.0})
                q = int(t.get("qty", 1))
                bp = float(t.get("buy_price", 0))
                mp_item_stats[nm]["q"] += q
                mp_item_stats[nm]["sum"] += bp * q
                if bp > mp_item_stats[nm]["max"]: mp_item_stats[nm]["max"] = bp

            mp_hold_rows = []
            for t in mp_holding:
                nm = t["item_name"]
                bp = float(t["buy_price"])
                q = int(t.get("qty", 1))
                avg_p = mp_item_stats[nm]["sum"] / mp_item_stats[nm]["q"]
                max_p = mp_item_stats[nm]["max"]
                breakeven = math.ceil(bp / fee_mult)
                cur_sp = bp if float(t.get("sell_price", 0)) == 0 else float(t["sell_price"])
                est_net = round((cur_sp * fee_mult - bp) * q, 1)
                judge_str = f"🟢+{fmt_man(est_net, '메소')} 이득" if est_net > 0 else (f"🔴{fmt_man(est_net, '메소')} 손실" if est_net < 0 else "⚪본전")

                mp_hold_rows.append({
                    "id": t["id"], "아이템명": nm, "산가격(만)": bp, "보유수량": q,
                    "내평균가(만)": round(avg_p, 1), "내최고가(만)": max_p,
                    "본전판매가": f"{breakeven:,}만", "판수량": q,
                    "판매가입력(만)": cur_sp, "예상손익판정": judge_str,
                    "판매완료": False, "삭제": False
                })

            edited_mp_hold = st.data_editor(
                pd.DataFrame(mp_hold_rows),
                column_config={
                    "id": None,
                    "아이템명": st.column_config.TextColumn("✏️아이템명", width="small"),
                    "산가격(만)": st.column_config.NumberColumn("✏️산 가격(만)", width="small", min_value=0.0, step=500.0, format="%d만"),
                    "보유수량": st.column_config.NumberColumn("✏️보유수량", width="small", min_value=1, step=1),
                    "내평균가(만)": st.column_config.NumberColumn("내 평단가", width="small", format="%d만", disabled=True),
                    "내최고가(만)": st.column_config.NumberColumn("최고매입가", width="small", format="%d만", disabled=True),
                    "본전판매가": st.column_config.TextColumn(f"{fee_pct_str}수수료 본전가", width="small", disabled=True),
                    "판수량": st.column_config.NumberColumn("✏️판 수량", width="small", min_value=1, step=1),
                    "판매가입력(만)": st.column_config.NumberColumn("✏️개당 판매예정가(만)", width="small", min_value=0.0, step=500.0, format="%d만"),
                    "예상손익판정": st.column_config.TextColumn("재판매 이득/손실 판정", width="medium", disabled=True),
                    "판매완료": st.column_config.CheckboxColumn("💰판매완료", width="small"),
                    "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small")
                },
                use_container_width=True, hide_index=True,
                key=f"mp_hold_editor_{st.session_state.mp_editor_ver}"
            )

            mp_trade_map = {t["id"]: t for t in mp_trades}
            mp_hold_changed = False
            for _, erow in edited_mp_hold.iterrows():
                tid = int(erow["id"])
                orig_t = mp_trade_map.get(tid)
                if not orig_t: continue
                if bool(erow["삭제"]):
                    mp_trades.remove(orig_t)
                    mp_hold_changed = True
                    continue

                new_nm = str(erow["아이템명"]).strip() if not pd.isna(erow["아이템명"]) else orig_t["item_name"]
                new_bp = float(erow["산가격(만)"]) if not pd.isna(erow["산가격(만)"]) else float(orig_t["buy_price"])
                new_bq = max(1, int(erow["보유수량"])) if not pd.isna(erow["보유수량"]) else int(orig_t.get("qty", 1))
                new_sp = float(erow["판매가입력(만)"]) if not pd.isna(erow["판매가입력(만)"]) else float(orig_t.get("sell_price", 0.0))

                if (new_nm != orig_t["item_name"] or new_bp != float(orig_t["buy_price"]) or
                    new_bq != int(orig_t.get("qty", 1)) or new_sp != float(orig_t.get("sell_price", 0.0))):
                    orig_t["item_name"] = new_nm
                    orig_t["buy_price"] = new_bp
                    orig_t["qty"] = new_bq
                    orig_t["sell_price"] = new_sp
                    mp_hold_changed = True

                if bool(erow["판매완료"]):
                    sp = float(erow["판매가입력(만)"])
                    bp = float(orig_t["buy_price"])
                    cur_q = int(orig_t.get("qty", 1))
                    sell_q = max(1, min(cur_q, int(erow["판수량"])))
                    net = round((sp * fee_mult - bp) * sell_q, 1)
                    now_str_sell = datetime.now(KST).strftime("%Y-%m-%d %H:%M")

                    if sell_q < cur_q:
                        orig_t["qty"] = cur_q - sell_q
                        new_id = max([t.get("id", 0) for t in mp_trades], default=0) + 1
                        mp_trades.append({
                            "id": new_id, "item_name": orig_t["item_name"], "buy_price": bp, "qty": sell_q,
                            "buy_date": orig_t.get("buy_date", ""), "status": "판매완료", "sell_price": sp,
                            "sell_date": now_str_sell, "net_profit": net
                        })
                    else:
                        orig_t["sell_price"] = sp
                        orig_t["sell_date"] = now_str_sell
                        orig_t["net_profit"] = net
                        orig_t["status"] = "판매완료"
                    mp_hold_changed = True

            if mp_hold_changed:
                save_json_local(MAPLE_FILE, mp_data)
                st.session_state.mp_dirty = True
                st.session_state.mp_editor_ver += 1
                st.rerun()

        st.divider()

        with st.expander("📖 3. 메이플 매입 족보 & 과거 거래 영수증 (수정/복구 가능)", expanded=False):
            if not mp_trades:
                st.caption("아직 등록된 메이플 장사 내역이 없습니다.")
            else:
                mp_jokbo_map = {}
                for t in mp_trades:
                    nm = t["item_name"]
                    mp_jokbo_map.setdefault(nm, {
                        "아이템명": nm, "총 매입수량": 0, "매입합계": 0.0,
                        "최고 매입가": 0.0, "최저 매입가": float('inf'),
                        "판매수량": 0, "판매합계": 0.0, "누적 순수익": 0.0, "최근 거래일": ""
                    })
                    jb = mp_jokbo_map[nm]
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

                mp_jokbo_rows = []
                for nm, jb in sorted(mp_jokbo_map.items()):
                    avg_buy = jb["매입합계"] / jb["총 매입수량"]
                    be_price = math.ceil(avg_buy / fee_mult)
                    avg_sell_str = f"{int(jb['판매합계']/jb['판매수량']):,}만" if jb["판매수량"] > 0 else "판매전"
                    mp_jokbo_rows.append({
                        "아이템명": nm, "누적매입": f"{jb['총 매입수량']}개",
                        "내 평균매입가": f"{int(avg_buy):,}만 ({fmt_man(avg_buy, '메소')})",
                        "최고비싸게산값": f"{int(jb['최고 매입가']):,}만",
                        "최저매입가": f"{int(jb['최저 매입가']):,}만",
                        f"{fee_pct_str}본전판매가": f"{be_price:,}만",
                        "평균판매가": avg_sell_str,
                        "누적순수익": fmt_man(jb["누적 순수익"], "메소"),
                        "최근매입일": jb["최근 거래일"]
                    })

                mp_search_kw = st.text_input("🔍 메이플 족보/과거기록 아이템 검색", key="mp_jokbo_search")
                mp_jokbo_df = pd.DataFrame(mp_jokbo_rows)
                if mp_search_kw.strip():
                    mp_jokbo_df = mp_jokbo_df[mp_jokbo_df["아이템명"].str.contains(mp_search_kw.strip(), case=False, na=False)]
                st.dataframe(mp_jokbo_df, use_container_width=True, hide_index=True)

                mp_hist_rows = []
                for t in sorted(mp_trades, key=lambda x: x.get("id", 0), reverse=True):
                    if mp_search_kw.strip() and mp_search_kw.strip().lower() not in t["item_name"].lower():
                        continue
                    mp_hist_rows.append({
                        "id": t["id"], "상태": "🟢판매완료" if t.get("status") == "판매완료" else "📦보유중",
                        "아이템명": t["item_name"], "수량": int(t.get("qty", 1)),
                        "산가격(만)": float(t["buy_price"]), "판가격(만)": float(t.get("sell_price", 0.0)),
                        "순수익": fmt_man(t.get("net_profit", 0), "메소") if t.get("status") == "판매완료" else "-",
                        "매입일시": t.get("buy_date", ""), "보유중복구": False, "삭제": False
                    })
                if mp_hist_rows:
                    edited_mp_hist = st.data_editor(
                        pd.DataFrame(mp_hist_rows),
                        column_config={
                            "id": None,
                            "상태": st.column_config.TextColumn("상태", width="small", disabled=True),
                            "아이템명": st.column_config.TextColumn("✏️아이템명", width="small"),
                            "수량": st.column_config.NumberColumn("✏️수량", width="small", min_value=1, step=1),
                            "산가격(만)": st.column_config.NumberColumn("✏️산 가격(만)", width="small", min_value=0.0, step=500.0, format="%d만"),
                            "판가격(만)": st.column_config.NumberColumn("✏️판 가격(만)", width="small", min_value=0.0, step=500.0, format="%d만"),
                            "순수익": st.column_config.TextColumn(f"순수익({fee_pct_str}제외)", width="small", disabled=True),
                            "매입일시": st.column_config.TextColumn("매입일시", width="small", disabled=True),
                            "보유중복구": st.column_config.CheckboxColumn("↩️보유중복구", width="small"),
                            "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small")
                        },
                        use_container_width=True, hide_index=True,
                        key=f"mp_hist_editor_{st.session_state.mp_editor_ver}"
                    )
                    mp_trade_map = {t["id"]: t for t in mp_trades}
                    mp_hist_changed = False
                    for _, hrow in edited_mp_hist.iterrows():
                        tid = int(hrow["id"])
                        orig_t = mp_trade_map.get(tid)
                        if not orig_t: continue
                        if bool(hrow["삭제"]):
                            mp_trades.remove(orig_t)
                            mp_hist_changed = True
                            continue
                        if bool(hrow["보유중복구"]) and orig_t.get("status") == "판매완료":
                            orig_t["status"] = "보유중"
                            orig_t["sell_price"] = 0.0
                            orig_t["sell_date"] = ""
                            orig_t["net_profit"] = 0.0
                            mp_hist_changed = True
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
                                orig_t["net_profit"] = round((h_sp * fee_mult - h_bp) * h_q, 1)
                            mp_hist_changed = True
                    if mp_hist_changed:
                        save_json_local(MAPLE_FILE, mp_data)
                        st.session_state.mp_dirty = True
                        st.session_state.mp_editor_ver += 1
                        st.rerun()
