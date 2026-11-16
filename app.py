import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import math
from datetime import datetime, timedelta
import pytz
from github import Github

st.set_page_config(page_title="통합 게임 숙제 & 수익 매니저 Pro", page_icon="🎮", layout="wide")

KST = pytz.timezone('Asia/Seoul')
LOA_FILE = "loa_data_v3.json"
GERSANG_FILE = "gersang_data_v1.json"
MAPLE_FILE = "maple_data_v1.json"
COMMON_FILE = "common_krw_v1.json"

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
# 💵 0. 3개 게임 현금(원화) 시세 및 월간 쌀먹 통합 데이터
# ==============================================================================
def create_initial_common():
    return {
        "loa_krw_per_10k_gold": 3500.0,     # 로아 1만 골드당 현금 시세(원)
        "loa_hourly_gold": 15000.0,         # 로아 생활/카던/보석 1시간 평균 획득 골드
        "loa_monthly_gold_sold": 0.0,       # 이번 달 로아 보석/골드 판매 누적량(골드)
        "gs_krw_per_1eok": 1800.0,          # 거상 1억 전(10,000만)당 현금 시세(원)
        "mp_krw_per_1eok": 2200.0           # 메이플 1억 메소(10,000만)당 현금 시세(원)
    }

def load_common_data():
    default_d = create_initial_common()
    if "GITHUB_TOKEN" in st.secrets and "REPO_NAME" in st.secrets:
        try:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["REPO_NAME"])
            contents = repo.get_contents(COMMON_FILE)
            d = json.loads(contents.decoded_content.decode("utf-8"))
            for k, v in default_d.items():
                d.setdefault(k, v)
            return d
        except Exception:
            return default_d
    else:
        try:
            with open(COMMON_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                for k, v in default_d.items():
                    d.setdefault(k, v)
                return d
        except Exception:
            return default_d


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
        "jokbo_shift_pct": 0.0, # 거상 족보 시세 일괄 보정 %
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
    data.setdefault("jokbo_shift_pct", 0.0)
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
# 🍁 3. 메이플스토리 `mesu.live` 올인원(추옵+주흔작+스타포스+윗잠+아랫잠) 통합 엔진
# ==============================================================================
# [A] 잠재능력 1회 재설정 정가표 (단위: 만 메소)
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

# [B] 등급업 공식 확률(p) + 천장 횟수(pity)
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

# [C] 윗잠/아랫잠 분리 프리셋 (`mesu.live` 공식 결합 확률 %)
MAPLE_MAIN_POT_OPTIONS = {
    "[레전드리/장신구] 드랍 or 메획 1줄 이상 (20%+)": {"prob_pct": 15.8200, "tier": "레전드리"},
    "[레전드리/장신구] 드랍+메획 총합 2줄 이상 (드메 2줄 핵심!)": {"prob_pct": 1.3960, "tier": "레전드리"},
    "[레전드리/장신구] 드랍 or 메획 1줄 + 주스탯 2줄": {"prob_pct": 1.1200, "tier": "레전드리"},
    "[레전드리/장신구] 드랍+메획 총합 3줄 (극옵 드메 3줄)": {"prob_pct": 0.0385, "tier": "레전드리"},
    "[레전드리/방어구·장신구] 주스탯 21% 이상 (올스탯 포함)": {"prob_pct": 6.4500, "tier": "레전드리"},
    "[레전드리/방어구·장신구] 주스탯 24% 이상 (정옵 2줄+)": {"prob_pct": 3.1800, "tier": "레전드리"},
    "[레전드리/방어구·장신구] 주스탯 27% 이상 (준3줄 국민옵)": {"prob_pct": 1.5400, "tier": "레전드리"},
    "[레전드리/방어구·장신구] 주스탯 30% 이상 (3줄 정옵)": {"prob_pct": 0.5780, "tier": "레전드리"},
    "[레전드리/방어구·장신구] 주스탯 33% 이상 (극옵 3줄)": {"prob_pct": 0.2190, "tier": "레전드리"},
    "[레전드리/장갑] 크리티컬 데미지 1줄(8%) + 주스탯 1줄+": {"prob_pct": 5.6200, "tier": "레전드리"},
    "[레전드리/장갑] 크리티컬 데미지 2줄 (16% 이상)": {"prob_pct": 0.7420, "tier": "레전드리"},
    "[레전드리/모자] 쿨타임 감소 -2초 이상 (주스탯 무관)": {"prob_pct": 6.8500, "tier": "레전드리"},
    "[레전드리/모자] 쿨타임 감소 -2초 + 주스탯 1줄+": {"prob_pct": 2.9500, "tier": "레전드리"},
    "[레전드리/모자] 쿨타임 감소 -3초 이상": {"prob_pct": 1.4800, "tier": "레전드리"},
    "[레전드리/모자] 쿨타임 감소 -4초 이상": {"prob_pct": 0.3520, "tier": "레전드리"},
    "[레전드리/무보엠] 보공/방무/공마 유효 2줄": {"prob_pct": 8.3300, "tier": "레전드리"},
    "[레전드리/무보엠] 보공/공마 유효 3줄 (방무 제외)": {"prob_pct": 0.9120, "tier": "레전드리"},
    "[레전드리/무보엠] 공격력/마력 21% 이상 (2줄+)": {"prob_pct": 3.5800, "tier": "레전드리"},
    "[레전드리/무보엠] 공격력/마력 30% 이상 (3줄)": {"prob_pct": 0.2640, "tier": "레전드리"},
    "[유니크/방어구·장신구] 주스탯 15% ~ 18% (유니크 2줄)": {"prob_pct": 6.6700, "tier": "유니크"},
    "[에픽/방어구·장신구] 주스탯 9% ~ 12% (에픽 2줄 토드용)": {"prob_pct": 10.2000, "tier": "에픽"},
    "🔗 mesu.live 세부 확률(%) 직접 입력": {"prob_pct": None, "tier": "레전드리"}
}

MAPLE_ADI_POT_OPTIONS = {
    "[아랫잠/레어] 공/마 +10 (에디 레어 1줄 가성비)": {"prob_pct": 6.2500, "tier": "레어"},
    "[아랫잠/에픽] 공/마 +10 또는 주스탯 4%+ (에디 에픽 1.5~2줄)": {"prob_pct": 5.5500, "tier": "에픽"},
    "[아랫잠/에픽] 공/마 +21 또는 주스탯 8%+ (에디 에픽 2줄 정옵)": {"prob_pct": 0.9200, "tier": "에픽"},
    "[아랫잠/유니크] 에디 주스탯 2줄 or 공/마 2줄 (유니크 국민옵)": {"prob_pct": 2.2200, "tier": "유니크"},
    "[아랫잠/레전드리] 에디 주스탯 2줄+ (정옵 2줄)": {"prob_pct": 2.1500, "tier": "레전드리"},
    "[아랫잠/레전드리] 에디 주스탯 2.5~3줄 (준종결/종결)": {"prob_pct": 0.7690, "tier": "레전드리"},
    "[아랫잠/무보엠] 에디 공격력/마력 12%~15% (유니크/레전 1줄+)": {"prob_pct": 6.8000, "tier": "레전드리"},
    "[아랫잠/무보엠] 에디 공격력/마력 21% 이상 (2줄)": {"prob_pct": 1.8180, "tier": "레전드리"},
    "🔗 mesu.live 아랫잠 세부 확률(%) 직접 입력": {"prob_pct": None, "tier": "레전드리"}
}

# [D] `mesu.live` 추가옵션(환생의 불꽃) 목표 급수별 평균 소모 개수 데이터
# (1급 = 주스탯1 / 공마1=4급 / 올스탯1%=10급 환산 기준)
MAPLE_FLAME_PRESETS = {
    "보스 장신구/방어구 (추옵 보정 O)": {
        "100급 이상 (가성비 부캐/드메용)": {"강환불": 8.0, "영환불": 3.5},
        "110급 이상 (준수한 가성비)": {"강환불": 22.0, "영환불": 8.5},
        "120급 이상 (국민 본캐급 추옵)": {"강환불": 68.0, "영환불": 24.0},
        "130급 이상 (고스펙 주력기)": {"강환불": 240.0, "영환불": 75.0},
        "140급 이상 (준종결 추옵)": {"강환불": 1050.0, "영환불": 290.0},
        "150급 이상 (초고스펙 종결)": {"강환불": 5800.0, "영환불": 1450.0},
    },
    "일반 장비 (미카엘라/일반장신구 - 추옵 보정 X)": {
        "60~70급 이상 (일반템 가성비)": {"강환불": 15.0, "영환불": 7.0},
        "80~90급 이상 (일반템 고추옵)": {"강환불": 65.0, "영환불": 28.0},
        "100급 이상 (일반템 극추옵)": {"강환불": 320.0, "영환불": 120.0},
    },
    "보스 무기 (아케인/해방무기 등)": {
        "2추옵 단독": {"강환불": 6.5, "영환불": 4.2},
        "1추옵 단독 (또는 2추+보공)": {"강환불": 33.0, "영환불": 10.5},
        "1추옵 + 보공/데미지 유효 (국민 무기 추옵)": {"강환불": 135.0, "영환불": 42.0},
        "1추옵 + 보공 + 데미지/주스탯 (종결급)": {"강환불": 680.0, "영환불": 195.0},
    }
}

# [E] `mesu.live` 스타포스 목표 별 개수별 표준 기대 비용 & 평균 파괴 횟수 (마르코프 체인 기준, 단위: 만 메소)
MAPLE_STARFORCE_TABLE = {
    "71~110제 (미카엘라 새안경/하프이어링 등)": {
        "10성 (가성비)": {"cost": 400.0, "booms": 0.0},
        "12성 (부캐/토드)": {"cost": 900.0, "booms": 0.0},
        "15성": {"cost": 3500.0, "booms": 0.0},
        "17성": {"cost": 7500.0, "booms": 0.0},
        "18성": {"cost": 16000.0, "booms": 0.15},
        "20성": {"cost": 55000.0, "booms": 0.85},
        "21성": {"cost": 85000.0, "booms": 1.40},
        "22성": {"cost": 165000.0, "booms": 2.90},
    },
    "120~150제 (이벤링/보장/루타비스)": {
        "10성 (가성비)": {"cost": 900.0, "booms": 0.0},
        "12성 (부캐/토드)": {"cost": 2200.0, "booms": 0.0},
        "15성": {"cost": 11500.0, "booms": 0.0},
        "17성 (국민 가성비)": {"cost": 26000.0, "booms": 0.0},
        "18성 (본캐 가성비)": {"cost": 58000.0, "booms": 0.25},
        "20성": {"cost": 195000.0, "booms": 1.15},
        "21성 (준종결)": {"cost": 295000.0, "booms": 1.85},
        "22성 (종결)": {"cost": 580000.0, "booms": 3.70},
    },
    "160제 (여명/앱솔랩스)": {
        "10성 (가성비)": {"cost": 1300.0, "booms": 0.0},
        "12성 (부캐/토드)": {"cost": 3100.0, "booms": 0.0},
        "15성": {"cost": 16500.0, "booms": 0.0},
        "17성 (국민 가성비)": {"cost": 37000.0, "booms": 0.0},
        "18성 (본캐 가성비)": {"cost": 82000.0, "booms": 0.25},
        "20성": {"cost": 275000.0, "booms": 1.15},
        "21성 (준종결)": {"cost": 415000.0, "booms": 1.85},
        "22성 (종결)": {"cost": 820000.0, "booms": 3.70},
    },
    "200제 (아케인셰이드/칠흑)": {
        "10성 (가성비)": {"cost": 2500.0, "booms": 0.0},
        "12성 (부캐/토드)": {"cost": 6000.0, "booms": 0.0},
        "15성": {"cost": 32000.0, "booms": 0.0},
        "17성 (국민 가성비)": {"cost": 72000.0, "booms": 0.0},
        "18성 (본캐 가성비)": {"cost": 160000.0, "booms": 0.25},
        "20성": {"cost": 540000.0, "booms": 1.15},
        "21성 (준종결)": {"cost": 810000.0, "booms": 1.85},
        "22성 (종결)": {"cost": 1600000.0, "booms": 3.70},
    },
    "250제 (에테르넬/광휘)": {
        "10성 (가성비)": {"cost": 4800.0, "booms": 0.0},
        "12성 (부캐/토드)": {"cost": 11500.0, "booms": 0.0},
        "15성": {"cost": 62000.0, "booms": 0.0},
        "17성 (국민 가성비)": {"cost": 140000.0, "booms": 0.0},
        "18성 (본캐 가성비)": {"cost": 310000.0, "booms": 0.25},
        "20성": {"cost": 1050000.0, "booms": 1.15},
        "21성 (준종결)": {"cost": 1580000.0, "booms": 1.85},
        "22성 (종결)": {"cost": 3100000.0, "booms": 3.70},
    }
}

STARFORCE_EVENTS = {
    "📅 노이벤트 (평일 기준)": {"cost_mult": 1.00, "boom_mult": 1.00},
    "🌟 5·10·15성 100% 성공 이벤트": {"cost_mult": 0.76, "boom_mult": 0.72},
    "💰 스타포스 비용 30% 할인 이벤트": {"cost_mult": 0.70, "boom_mult": 1.00},
    "⚡ 10성 이하 1+1 이벤트": {"cost_mult": 0.90, "boom_mult": 1.00},
    "✨ 샤이닝 스타포스 (5·10·15성 100% + 30% 할인)": {"cost_mult": 0.53, "boom_mult": 0.72},
}

TIER_ORDER = ["레어", "에픽", "유니크", "레전드리"]

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
        "mean_cost": mean_cost, "mean_tries": mean_tries,
        "p50_cost": p50_cost, "p85_cost": p85_cost,
        "p95_cost": p95_cost, "ceil_cost": ceil_cost
    }

def calc_mesu_option_stats(prob_pct, unit_cost):
    p = max(0.000001, min(1.0, prob_pct / 100.0))
    mean_tries = 1.0 / p
    
    def q_tries(q):
        if p >= 1.0:
            return 1
        return max(1, math.ceil(math.log(1.0 - q) / math.log(1.0 - p)))

    t50, t85, t95 = q_tries(0.50), q_tries(0.85), q_tries(0.95)
    return {
        "prob_pct": prob_pct, "mean_tries": mean_tries, "mean_cost": mean_tries * unit_cost,
        "t50": t50, "p50_cost": t50 * unit_cost,
        "t85": t85, "p85_cost": t85 * unit_cost,
        "t95": t95, "p95_cost": t95 * unit_cost,
    }

# 📜 주문의 흔적(%별) 완작 기댓값 산출 함수 (손재주100 + 길드스킬4% + 피버타임 + 이노센트/순백 복구 반영)
def calc_scroll_expected_cost(scroll_mode, slots, trace_per_try, trace_price_each, inno_cost, css_cost, is_fever=True):
    trace_try_cost_man = (trace_per_try * trace_price_each) / 10000.0
    if "100%" in scroll_mode:
        p = 1.0
    elif "70%" in scroll_mode:
        p = 0.99 if is_fever else 0.84
    elif "30%" in scroll_mode:
        p = 0.59 if is_fever else 0.44
    else: # 15% 작
        p = 0.39 if is_fever else 0.29

    if p >= 0.99:
        # 피버 70% 및 100% 작: 사실상 스트레이트 완작
        return round(slots * trace_try_cost_man + 150.0, 1), f"확률 {int(p*100)}% 스트레이트 완작"

    # 15% / 30% 작: 첫 4작에서 최소 기준 성공 시 순백(CSS)으로 밀고, 미달 시 이노센트로 초기화하는 표준 완작 알고리즘
    target_first4 = 2 if p < 0.45 else 3
    prob_pass_first4 = 0.0
    for k in range(target_first4, 5):
        prob_pass_first4 += math.comb(4, k) * (p ** k) * ((1.0 - p) ** (4 - k))
    prob_pass_first4 = max(0.05, prob_pass_first4)

    expected_inno_cycles = (1.0 / prob_pass_first4) - 1.0
    inno_stage_cost = expected_inno_cycles * (4 * trace_try_cost_man + inno_cost) + (4 * trace_try_cost_man)

    rem_slots = max(0, slots - target_first4)
    # 남은 슬롯 1개 성공당 평균 시도 횟수 = 1/p, 평균 실패 횟수(순백 소모) = (1-p)/p
    rem_tries = rem_slots / p
    rem_fails = rem_slots * ((1.0 - p) / p)
    finish_stage_cost = (rem_tries * trace_try_cost_man) + (rem_fails * css_cost) + 200.0 # 황망100% 등 기본값 포함

    total_scroll_man = round(inno_stage_cost + finish_stage_cost, 1)
    desc = f"실질확률 {int(p*100)}% | 평균 이노센트 {expected_inno_cycles:.1f}회 + 순백복구 {rem_fails:.1f}회"
    return total_scroll_man, desc

def create_initial_maple(now_str, today_str):
    return {
        "last_weekly_reset": now_str,
        "last_daily_date": today_str,
        "fee_rate": 0.03,
        "jokbo_shift_pct": 0.0, # 메이플 족보 시세 일괄 보정 %
        "accounts": [
            {"id": 1, "명의명": "1번 본계정 (루나 / 유니온 8500 / Lv.285)", "결정석완료": False, "결정석수익": 15000.0, "일일메소완료": False, "전문기술피로도": False, "메모": "본캐 주간보스 1캐릭 몰아주기"},
            {"id": 2, "명의명": "2번 부계정 A (루나 / 유니온 2500 / Lv.284)", "결정석완료": False, "결정석수익": 12000.0, "일일메소완료": False, "전문기술피로도": False, "메모": "부계정 보스 & 피로도"},
            {"id": 3, "명의명": "3번 부계정 B (루나 / 유니온 3000 / Lv.284)", "결정석완료": False, "결정석수익": 12000.0, "일일메소완료": False, "전문기술피로도": False, "메모": "부계정 보스 & 피로도"},
        ],
        "hunting_cfg": {
            "pure_meso_hr": 5500.0, "frag_price": 650.0,
            "frags_per_hr": 15.0, "extra_drops_hr": 300.0, "consumable_hr": 400.0
        },
        "alchemy_cfg": {
            "oil_price": 45.0, "crystal_price": 80.0,
            "exp_recipe_price": 1500.0, "drop_recipe_price": 1200.0,
            "crafts_per_recipe": 30.0, "bottle_etc_price": 15.0
        },
        "biz_methods": [
            {"id": 1, "활성": True, "돈벌이명": "🧪 연금술: 경험 축적의 비약(경축비) 제작", "원가(만)": 815.0, "판매가(만)": 950.0, "시간당횟수": 30.0, "메모": "왼쪽 원가 계산기에서 자동 연동"},
            {"id": 2, "활성": True, "돈벌이명": "🧪 연금술: 재물 획득의 비약(재획비) 제작", "원가(만)": 680.0, "판매가(만)": 820.0, "시간당횟수": 30.0, "메모": "왼쪽 원가 계산기에서 자동 연동"},
            {"id": 3, "활성": True, "돈벌이명": "👓 미카엘라의 새 안경(90제) 제작/합성/드메 장사", "원가(만)": 1500.0, "판매가(만)": 3500.0, "시간당횟수": 10.0, "메모": "90제 드메템 스테디셀러"},
            {"id": 4, "활성": True, "돈벌이명": "🔨 에픽 2줄 토드 장사 (160/200제)", "원가(만)": 8000.0, "판매가(만)": 12500.0, "시간당횟수": 4.0, "메모": "토드용 베이스 매입 후 재판매"},
        ],
        "meso_market_cfg": {
            "shift_pct": 0.0, "band_threshold": 5.0, "current_watch_rate": 2400.0
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
    data.setdefault("jokbo_shift_pct", 0.0)
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
# 세션 초기화 및 상단 3개 게임 통합 현금(₩) 정산 & 원클릭 마스터 백업 바
# ==============================================================================
if "common_data" not in st.session_state:
    st.session_state.common_data = load_common_data()
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
cm_data = st.session_state.common_data

# 상단 타이틀 & 마스터 백업 버튼
top_t1, top_t2 = st.columns([3.2, 1.3])
with top_t1:
    st.title("🎮 3대 게임 숙제 & 올인원 수익 관리 사령탑 Pro")
with top_t2:
    st.write("")
    any_dirty = st.session_state.dirty or st.session_state.gs_dirty or st.session_state.mp_dirty
    master_lbl = "💾 3개 게임 통합 깃허브 백업 (미저장 변경있음*)" if any_dirty else "💾 3개 게임 통합 깃허브 백업 (최신상태)"
    if st.button(master_lbl, type="primary" if any_dirty else "secondary", use_container_width=True):
        ok1 = save_json_github(LOA_FILE, loa_data, "Master Backup LOA")
        ok2 = save_json_github(GERSANG_FILE, gs_data, "Master Backup Gersang")
        ok3 = save_json_github(MAPLE_FILE, mp_data, "Master Backup Maple")
        ok4 = save_json_github(COMMON_FILE, cm_data, "Master Backup Common")
        if ok1 or ok2 or ok3 or ok4:
            st.session_state.dirty = False
            st.session_state.gs_dirty = False
            st.session_state.mp_dirty = False
            st.toast("✅ 로아·거상·메이플 모든 데이터가 한 번에 깃허브에 영구 백업되었습니다!")
            st.rerun()

# 💵 3개 게임 현금(원화 ₩) 시급 비교 & 월간 총 부수입 정산 대시보드 (접기/펼치기)
now_kst_all = datetime.now(KST)
cur_ym_all = now_kst_all.strftime("%Y-%m")

gs_month_man = sum(float(t.get("net_profit", 0)) for t in gs_data["client1_trades"] if t.get("status") == "판매완료" and str(t.get("sell_date", "")).startswith(cur_ym_all))
mp_month_man = sum(float(t.get("net_profit", 0)) for t in mp_data["maple_trades"] if t.get("status") == "판매완료" and str(t.get("sell_date", "")).startswith(cur_ym_all))
mp_boss_done_man = sum(float(a["결정석수익"]) for a in mp_data["accounts"] if a["결정석완료"])

with st.expander("💵 [통합 수익 사령탑] 3개 게임 실시간 현금 시급(원/시간) 비교 & 이번 달 총 부수입(₩) 정산판 (클릭해 열기/닫기)", expanded=False):
    krw_c1, krw_c2, krw_c3, krw_c4 = st.columns(4)
    with krw_c1:
        loa_rate = st.number_input("⚓ 로아 1만 골드당 현금 시세(원)", min_value=100.0, value=float(cm_data["loa_krw_per_10k_gold"]), step=100.0, format="%.0f")
        loa_hr_g = st.number_input("⚓ 로아 1시간 평균 획득 골드", min_value=0.0, value=float(cm_data["loa_hourly_gold"]), step=1000.0, format="%.0f")
    with krw_c2:
         loa_m_sold = st.number_input(f"⚓ 이번 달({cur_ym_all}) 로아 판매 골드 합계", min_value=0.0, value=float(cm_data["loa_monthly_gold_sold"]), step=10000.0, format="%.0f")
    with krw_c3:
        gs_rate = st.number_input("💰 거상 1억 전(10,000만)당 시세(원)", min_value=100.0, value=float(cm_data["gs_krw_per_1eok"]), step=50.0, format="%.0f")
    with krw_c4:
        mp_rate = st.number_input("🍁 메이플 1억 메소(10,000만)당 시세(원)", min_value=100.0, value=float(cm_data["mp_krw_per_1eok"]), step=50.0, format="%.0f")

    if (loa_rate != cm_data["loa_krw_per_10k_gold"] or loa_hr_g != cm_data["loa_hourly_gold"] or
        loa_m_sold != cm_data["loa_monthly_gold_sold"] or gs_rate != cm_data["gs_krw_per_1eok"] or mp_rate != cm_data["mp_krw_per_1eok"]):
        cm_data["loa_krw_per_10k_gold"] = loa_rate
        cm_data["loa_hourly_gold"] = loa_hr_g
        cm_data["loa_monthly_gold_sold"] = loa_m_sold
        cm_data["gs_krw_per_1eok"] = gs_rate
        cm_data["mp_krw_per_1eok"] = mp_rate
        save_json_local(COMMON_FILE, cm_data)

    # 각 게임 시간당 원화(₩) 시급 계산
    loa_hourly_krw = (loa_hr_g / 10000.0) * loa_rate
    gs_c2_cfg = gs_data["client2_farm"]
    gs_hourly_man = (float(gs_c2_cfg["drop_item_price"]) * float(gs_c2_cfg["drops_per_hour"])) + float(gs_c2_cfg["extra_hourly_man"])
    gs_hourly_krw = (gs_hourly_man / 10000.0) * gs_rate

    mp_hc = mp_data["hunting_cfg"]
    mp_fee_m = 1.0 - float(mp_data.get("fee_rate", 0.03))
    mp_hunt_hr_man = float(mp_hc["pure_meso_hr"]) + (float(mp_hc["frag_price"]) * float(mp_hc["frags_per_hr"]) * mp_fee_m) + (float(mp_hc["extra_drops_hr"]) * mp_fee_m) - float(mp_hc["consumable_hr"])
    mp_hourly_krw = (mp_hunt_hr_man / 10000.0) * mp_rate

    # 이번 달 원화(₩) 총수익 합산
    loa_m_krw = (loa_m_sold / 10000.0) * loa_rate
    gs_m_krw = (gs_month_man / 10000.0) * gs_rate
    mp_m_krw = ((mp_month_man + mp_boss_done_man) / 10000.0) * mp_rate
    total_month_krw = loa_m_krw + gs_m_krw + mp_m_krw

    st.divider()
    k_c1, k_c2, k_c3, k_c4 = st.columns(4)
    k_c1.metric("⚓ 로아 환산 시급 / 월수익", f"시급 {loa_hourly_krw:,.0f}원", f"이번 달: {loa_m_krw:,.0f}원")
    k_c2.metric("💰 거상 반자사 시급 / 월장사수익", f"시급 {gs_hourly_krw:,.0f}원", f"이번 달 장사: {gs_m_krw:,.0f}원")
    k_c3.metric("🍁 메이플 재획 시급 / 월수익(장사+주보)", f"시급 {mp_hourly_krw:,.0f}원", f"이번 달: {mp_m_krw:,.0f}원")
    k_c4.metric(f"👑 {cur_ym_all} 3대 게임 총 현금 가치", f"{total_month_krw:,.0f} 원", "로아+거상+메이플 통합 정산")

tab_loa, tab_gersang, tab_maple = st.tabs([
    "⚓ 로스트아크 (25서버)",
    "💰 천하제일상 거상 (2클라+장사+시세보정)",
    "🍁 메이플스토리 (3명의+올인원종합견적기+메소마켓)"
])

# ================= [여기까지가 파트 1입니다. 바로 아래 줄에 파트 2를 이어 붙여주세요!] =================
# ================= [파트 1 코드 바로 아래 줄에 여기서부터 이어서 붙여넣으세요!] =================

# ==============================================================================
# 탭 1: ⚓ 로스트아크 화면 (무삭제 풀버전)
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
# 탭 2: 💰 천하제일상 거상 화면 (2클라 반자사 + 1클라 장사 + 시세보정 % + CSV 다운로드)
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

            # ✨ 업그레이드: 족보 시세 변동 보정(%) 슬라이더 & 엑셀(CSV) 다운로드 탑재!
            with st.expander("📖 3. 나의 매입 족보 (시세 변동 `%` 보정 지원) & 과거 영수증 수정/복구/엑셀 다운로드", expanded=False):
                if not trades:
                    st.caption("아직 등록된 거래 내역이 없습니다.")
                else:
                    jb_c1, jb_c2, jb_c3 = st.columns([1.5, 1.5, 1.2])
                    with jb_c1:
                        search_kw = st.text_input("🔍 족보/과거기록 아이템 이름 검색", key="gs_jokbo_search")
                    with jb_c2:
                        gs_shift = st.number_input(
                            "🎚️ 거상 전체 시세 변동 보정 (%)",
                            min_value=-80.0, max_value=200.0, value=float(gs_data.get("jokbo_shift_pct", 0.0)), step=5.0, format="%.1f",
                            help="예: 인플레나 패치로 예전보다 템값이 전체적으로 +15% 올랐다면 15를 입력하세요. 내 과거 평단가와 본전 판매가를 +15% 보정해서 보여줍니다!"
                        )
                        if gs_shift != float(gs_data.get("jokbo_shift_pct", 0.0)):
                            gs_data["jokbo_shift_pct"] = gs_shift
                            save_json_local(GERSANG_FILE, gs_data)
                            st.session_state.gs_dirty = True
                    with jb_c3:
                        st.write("")
                        csv_gs = pd.DataFrame(trades).to_csv(index=False).encode("utf-8-sig")
                        st.download_button(
                            "📥 거상 전체 장부 엑셀(CSV) 다운로드",
                            data=csv_gs,
                            file_name=f"gersang_trades_{cur_ym}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )

                    gs_mult = 1.0 + (gs_shift / 100.0)
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
                        adj_avg_buy = avg_buy * gs_mult
                        adj_be_price = math.ceil(adj_avg_buy / 0.98)
                        avg_sell_str = f"{int(jb['판매합계']/jb['판매수량']):,}만" if jb["판매수량"] > 0 else "판매전"
                        jokbo_rows.append({
                            "아이템명": nm,
                            "누적매입": f"{jb['총 매입수량']}개",
                            "원본 평단가": f"{int(avg_buy):,}만",
                            f"보정 평단가({gs_shift:+.0f}%)": f"{int(adj_avg_buy):,}만 ({fmt_man(adj_avg_buy)})",
                            "최고비싸게산값": f"{int(jb['최고 매입가']):,}만",
                            "최저매입가": f"{int(jb['최저 매입가']):,}만",
                            "보정 2%본전가": f"{adj_be_price:,}만",
                            "평균판매가": avg_sell_str,
                            "누적순수익": fmt_man(jb["누적 순수익"]),
                        })

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

# ================= [여기까지가 파트 2입니다. 바로 아래 줄에 파트 3을 이어 붙여주세요!] =================
# ================= [파트 2 코드 바로 아래의 '파트 3' 구간만 이 코드로 덮어쓰세요!] =================

# ==============================================================================
# 탭 3: 🍁 메이플스토리 화면 (해방무기 프리셋 + 직작/장사 백과사전 탭 추가 완결판)
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

    mp_sub1, mp_sub2, mp_sub3, mp_sub4, mp_sub5 = st.tabs([
        "🏆 1. 사냥 vs 장사 시급 판독기 & 🧪 비약 원가",
        "🛠️ 2. 올인원 종합 견적기 (해방무기/방어구/장신구)",
        "💱 3. 메소마켓 (시세 일지 & % 보정 & AI 추천)",
        "📖 4. 메이플 장사 가계부 & 시세 족보",
        "📘 5. 직작 & 장사 백과사전 (추옵/작/용어 완벽 가이드)"
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
    # 🛠️ [서브탭 2] 올인원(추옵+주흔작%+스타포스+윗잠+아랫잠+보정%) 종합 견적 & 매물 판독기 (해방무기 프리셋 포함!)
    # --------------------------------------------------------------------------
    with mp_sub2:
        st.markdown("#### 🛠️ 올인원(`노작+가위+추옵+주흔작+스타포스+윗잠+아랫잠+시세보정%`) 완제품 종합 견적 & 경매장 매물 판독기")
        st.caption(
            "**장비 레벨 구간과 목표 옵션만 선택하면 `mesu.live` 공식 확률·1회 비용·주흔 소모량이 100% 자동으로 세팅됩니다!** "
            "(추옵이나 작 보는 법이 헷갈리시면 오른쪽 끝 **`📘 5. 직작 & 장사 백과사전`** 탭을 참고하세요!)"
        )

        AUTO_TRACE_SPEC = {
            "71~110제 (미카엘라 새안경/하프이어링 등)": {"장신구 (5~6작)": (5, 200), "방어구 (8~9작)": (8, 250), "무기 (9~10작)": (9, 350)},
            "120~150제 (이벤링/보장/루타비스)": {"장신구 (5~6작)": (6, 400), "방어구 (8~12작)": (8, 550), "무기 (9~10작)": (10, 900)},
            "160제 (여명/앱솔랩스)": {"장신구 (6~7작)": (6, 550), "방어구 (8~12작)": (9, 750), "무기 (9~10작)": (10, 1200)},
            "200제 (아케인셰이드/칠흑)": {"장신구 (6~7작)": (7, 800), "방어구 (8~12작)": (9, 1150), "무기 (9~10작)": (10, 1800)},
            "250제 (에테르넬/광휘)": {"장신구 (6~7작)": (7, 1100), "방어구 (8~12작)": (9, 1500), "무기 (9~10작)": (10, 2400)},
        }

        preset_keys = {
            "est_name": "데이브레이크 펜던트 / 미카엘라 새 안경 / 아케인 무기",
            "est_lv": "160제 (여명/앱솔랩스)", "est_base": 5000.0, "est_auc": 450000.0, "est_val_shift": 0.0,
            "est_use_scis": False, "est_use_flm": True, "est_fl_cat": "보스 장신구/방어구 (추옵 보정 O)",
            "est_use_scr": True, "est_use_sf": True, "est_use_main": True, "est_use_adi": True,
            "est_sf_goal": "18성 (본캐 가성비)",
            "est_main_start": "에픽", "est_main_opt": "[레전드리/방어구·장신구] 주스탯 27% 이상 (준3줄 국민옵)",
            "est_adi_start": "레어", "est_adi_opt": "[아랫잠/에픽] 공/마 +10 또는 주스탯 4%+ (에디 에픽 1.5~2줄)"
        }
        for pk, pv in preset_keys.items():
            if pk not in st.session_state:
                st.session_state[pk] = pv

        with st.container(border=True):
            st.markdown("##### ⚡ 원클릭 국민 세팅 프리셋 (장신구 · 방어구 · 제네시스 해방 무기 · 해방 전 아케인 무기)")
            pr1, pr2, pr3, pr4, pr5, pr6 = st.columns(6)
            with pr1:
                if st.button("👓 90제 미카엘라 드메2줄", use_container_width=True):
                    st.session_state.est_name = "미카엘라의 새 안경 (90제 드메2줄)"
                    st.session_state.est_lv = "71~110제 (미카엘라 새안경/하프이어링 등)"
                    st.session_state.est_base = 1500.0; st.session_state.est_auc = 320000.0; st.session_state.est_val_shift = 0.0
                    st.session_state.est_use_flm = False; st.session_state.est_use_scr = False; st.session_state.est_use_sf = False
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = False
                    st.session_state.est_main_start = "에픽"
                    st.session_state.est_main_opt = "[레전드리/장신구] 드랍+메획 총합 2줄 이상 (드메 2줄 핵심!)"
                    st.rerun()
            with pr2:
                if st.button("💍 17성 유니크 가성비", use_container_width=True):
                    st.session_state.est_name = "17성 유니크 가성비 방어구/장신구"
                    st.session_state.est_lv = "160제 (여명/앱솔랩스)"
                    st.session_state.est_base = 3000.0; st.session_state.est_auc = 95000.0; st.session_state.est_val_shift = 0.0
                    st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 장신구/방어구 (추옵 보정 O)"
                    st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                    st.session_state.est_sf_goal = "17성 (국민 가성비)"
                    st.session_state.est_main_start = "에픽"
                    st.session_state.est_main_opt = "[유니크/방어구·장신구] 주스탯 15% ~ 18% (유니크 2줄)"
                    st.session_state.est_adi_start = "레어"
                    st.session_state.est_adi_opt = "[아랫잠/에픽] 공/마 +10 또는 주스탯 4%+ (에디 에픽 1.5~2줄)"
                    st.rerun()
            with pr3:
                if st.button("🔥 18성 레전27% 국민템", use_container_width=True):
                    st.session_state.est_name = "18성 레전 27% 국민 본캐 템"
                    st.session_state.est_lv = "160제 (여명/앱솔랩스)"
                    st.session_state.est_base = 5000.0; st.session_state.est_auc = 480000.0; st.session_state.est_val_shift = 0.0
                    st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 장신구/방어구 (추옵 보정 O)"
                    st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                    st.session_state.est_sf_goal = "18성 (본캐 가성비)"
                    st.session_state.est_main_start = "에픽"
                    st.session_state.est_main_opt = "[레전드리/방어구·장신구] 주스탯 27% 이상 (준3줄 국민옵)"
                    st.session_state.est_adi_start = "레어"
                    st.session_state.est_adi_opt = "[아랫잠/유니크] 에디 주스탯 2줄 or 공/마 2줄 (유니크 국민옵)"
                    st.rerun()
            with pr4:
                if st.button("👑 22성 레전30% 종결템", use_container_width=True):
                    st.session_state.est_name = "22성 아케인/칠흑 종결 세팅"
                    st.session_state.est_lv = "200제 (아케인셰이드/칠흑)"
                    st.session_state.est_base = 35000.0; st.session_state.est_auc = 2800000.0; st.session_state.est_val_shift = 0.0
                    st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 장신구/방어구 (추옵 보정 O)"
                    st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                    st.session_state.est_sf_goal = "22성 (종결)"
                    st.session_state.est_main_start = "에픽"
                    st.session_state.est_main_opt = "[레전드리/방어구·장신구] 주스탯 30% 이상 (3줄 정옵)"
                    st.session_state.est_adi_start = "레어"
                    st.session_state.est_adi_opt = "[아랫잠/레전드리] 에디 주스탯 2.5~3줄 (준종결/종결)"
                    st.rerun()
            with pr5:
                if st.button("⚔️ 제네시스 해방무기 직작", use_container_width=True):
                    st.session_state.est_name = "제네시스 해방 무기 (22성·15%완작 기본 지급)"
                    st.session_state.est_lv = "200제 (아케인셰이드/칠흑)"
                    st.session_state.est_base = 0.0; st.session_state.est_auc = 0.0; st.session_state.est_val_shift = 0.0
                    st.session_state.est_use_scis = False
                    st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 무기 (아케인/해방무기 등)"
                    st.session_state.est_use_scr = False; st.session_state.est_use_sf = False # 15%완작 + 22성 공짜 지급!
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                    st.session_state.est_main_start = "유니크" # 해방 시 유니크 시작
                    st.session_state.est_main_opt = "[레전드리/무보엠] 보공/공마 유효 3줄 (방무 제외)"
                    st.session_state.est_adi_start = "에픽"   # 해방 시 에픽 시작
                    st.session_state.est_adi_opt = "[아랫잠/무보엠] 에디 공격력/마력 21% 이상 (2줄)"
                    st.rerun()
            with pr6:
                if st.button("🗡️ 해방전 18성 아케인무기", use_container_width=True):
                    st.session_state.est_name = "해방 전 거쳐가는 18성 아케인셰이드 무기 (중고 감가 -35% 반영)"
                    st.session_state.est_lv = "200제 (아케인셰이드/칠흑)"
                    st.session_state.est_base = 10000.0; st.session_state.est_auc = 350000.0; st.session_state.est_val_shift = -35.0
                    st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 무기 (아케인/해방무기 등)"
                    st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                    st.session_state.est_sf_goal = "18성 (본캐 가성비)"
                    st.session_state.est_main_start = "에픽"
                    st.session_state.est_main_opt = "[레전드리/무보엠] 보공/방무/공마 유효 2줄"
                    st.session_state.est_adi_start = "레어"
                    st.session_state.est_adi_opt = "[아랫잠/무보엠] 에디 공격력/마력 12%~15% (유니크/레전 1줄+)"
                    st.rerun()

        e_col1, e_col2 = st.columns([1.2, 1.2], gap="large")

        with e_col1:
            with st.container(border=True):
                st.markdown("##### 🛒 [기본 설정] 장비 레벨 · 노작가 · 경매장 완제품가 · 시세 보정(%)")
                eval_item_name = st.text_input("아이템 이름", value=st.session_state.est_name)
                st.session_state.est_name = eval_item_name
                lv_list = list(MAPLE_CUBE_COST_TABLE["윗잠 (잠재능력)"].keys())
                lv_idx = lv_list.index(st.session_state.est_lv) if st.session_state.est_lv in lv_list else 2
                lv_bracket = st.selectbox("착용 레벨 구간 선택 (선택 즉시 모든 파트의 비용/주흔/스타포스가 자동 변경됩니다!)", lv_list, index=lv_idx)
                st.session_state.est_lv = lv_bracket

                b_c1, b_c2 = st.columns(2)
                with b_c1:
                    base_item_price = st.number_input("🛒 노작(베이스) 1개 매입가 (만 메소, 해방무기는 0)", min_value=0.0, value=float(st.session_state.est_base), step=1000.0, format="%.0f")
                    st.session_state.est_base = base_item_price
                    st.caption(f"환산: **{fmt_man(base_item_price, '메소')}** (스타포스 파괴 시 스페어 비용 자동 연동)")
                with b_c2:
                    auction_finished_price = st.number_input("🏷️ 비교할 경매장 완제품 가격 (만 메소)", min_value=0.0, value=float(st.session_state.est_auc), step=10000.0, format="%.0f")
                    st.session_state.est_auc = auction_finished_price
                    st.caption(f"환산: **{fmt_man(auction_finished_price, '메소')}**")

                sc_c1, sc_c2 = st.columns(2)
                with sc_c1:
                    use_scissors = st.checkbox("✂️ 플래티넘 카르마의 가위 비용 포함", value=st.session_state.est_use_scis)
                    st.session_state.est_use_scis = use_scissors
                    cur_mp_rate = float(mp_data["meso_market_cfg"].get("current_watch_rate", 2400.0))
                    auto_scis_man = round((5900.0 / max(100.0, cur_mp_rate)) * 10000.0, 0)
                    if use_scissors:
                        scissors_cost = st.number_input("✂️ 가위 1회 메소 환산값 (만 메소)", min_value=0.0, value=float(auto_scis_man), step=500.0, format="%.0f")
                    else:
                        scissors_cost = 0.0
                with sc_c2:
                    market_valuation_shift = st.number_input(
                        "🎚️ 완제품 시장 시세 보정 / 중고 직작 감가율 (%)",
                        min_value=-70.0, max_value=100.0, value=float(st.session_state.est_val_shift), step=5.0, format="%.1f",
                        help="예: 해방 전 임시 아케인 무기처럼 중고 감가가 심한 품목은 -30% ~ -40%를 입력해 적정 중고가를 확인하세요!"
                    )
                    st.session_state.est_val_shift = market_valuation_shift

            # A단계: 추가옵션 (환생의 불꽃)
            with st.container(border=True):
                use_flame = st.checkbox("🔥 [파트 1] 추가옵션(환생의 불꽃) 견적 포함하기", value=st.session_state.est_use_flm)
                st.session_state.est_use_flm = use_flame
                flame_norm_cost = 0.0
                flame_desc = "미포함"
                if use_flame:
                    fl_cats = list(MAPLE_FLAME_PRESETS.keys())
                    default_fl_cat_idx = 1 if "71~110제" in lv_bracket else (fl_cats.index(st.session_state.est_fl_cat) if st.session_state.est_fl_cat in fl_cats else 0)
                    fl_c1, fl_c2 = st.columns(2)
                    with fl_c1:
                        fl_cat = st.selectbox("장비 추옵 분류 (무기는 '보스 무기' 선택!)", fl_cats, index=default_fl_cat_idx)
                        st.session_state.est_fl_cat = fl_cat
                        fl_target = st.selectbox("목표 추옵 급수/옵션 (공식 소모량 자동 적용)", list(MAPLE_FLAME_PRESETS[fl_cat].keys()), index=min(2, len(MAPLE_FLAME_PRESETS[fl_cat])-1))
                    with fl_c2:
                        fl_type = st.radio("사용할 환불 종류", ["강력한 환생의 불꽃(강환불)", "영원한 환생의 불꽃(영환불)"], horizontal=True)
                        is_eternal = "영환불" in fl_type
                        default_fl_price = 1800.0 if is_eternal else 450.0
                        fl_unit_price = st.number_input(
                            f"💎 {'영환불' if is_eternal else '강환불'} 1개 시세 (만 메소)",
                            min_value=1.0, value=default_fl_price, step=50.0, format="%.0f",
                            key=f"fl_p_{is_eternal}"
                        )
                    fl_tries = MAPLE_FLAME_PRESETS[fl_cat][fl_target]["영환불" if is_eternal else "강환불"]
                    flame_norm_cost = round(fl_tries * fl_unit_price, 1)
                    flame_desc = f"{fl_target[:12]} (자동: 평균 {fl_tries:.1f}개 × {int(fl_unit_price)}만)"
                    st.caption(f"👉 **자동 산출된 추옵 기대 원가: `{fmt_man(flame_norm_cost, '메소')}`** ({flame_desc})")

            # B단계: 주문서 작
            with st.container(border=True):
                use_scroll = st.checkbox("📜 [파트 2] 주문서 작(주흔 15%/30%/70%/100% · 악공 · 놀긍) 견적 포함하기", value=st.session_state.est_use_scr)
                st.session_state.est_use_scr = use_scroll
                scroll_norm_cost = 0.0
                scroll_event_cost = 0.0
                scroll_desc = "미포함 (또는 해방무기 기본 15% 완작 지급)"
                if use_scroll:
                    sc_c1, sc_c2 = st.columns([1.4, 1.0])
                    with sc_c1:
                        sc_mode = st.selectbox("작 종류 선택", [
                            "주문의 흔적 30% 완작 (방어구/장신구 본캐급)",
                            "주문의 흔적 15% 완작 (무기/고스펙 방어구)",
                            "주문의 흔적 70% 완작 (가성비/드메/부캐용)",
                            "주문의 흔적 100% 완작",
                            "✏️ 프악공 / 악공 / 매지컬 / 놀긍혼 완작 비용 직접 입력"
                        ])
                    with sc_c2:
                        part_type = st.selectbox("장비 부위 (주흔 개수 자동 세팅)", list(AUTO_TRACE_SPEC[lv_bracket].keys()))

                    if "직접 입력" in sc_mode:
                        scroll_norm_cost = st.number_input("직접 입력: 총 작 완성 예상 비용 (만 메소)", min_value=0.0, value=15000.0, step=1000.0, format="%.0f")
                        scroll_event_cost = scroll_norm_cost
                        scroll_desc = "사용자 직접 입력 작 비용"
                    else:
                        auto_slots, auto_trace_per = AUTO_TRACE_SPEC[lv_bracket][part_type]
                        trace_price = 2500.0
                        css_cost = 450.0
                        if st.checkbox("⚙️ 주흔 시세 / 슬롯 수 세부 조정하기 (기본값 자동 적용 중)", value=False):
                            s_c1, s_c2, s_c3, s_c4 = st.columns(4)
                            with s_c1:
                                auto_slots = st.number_input("총 작 횟수", min_value=1, max_value=15, value=int(auto_slots), step=1)
                            with s_c2:
                                auto_trace_per = st.number_input("1회 소모 주흔", min_value=50, max_value=3000, value=int(auto_trace_per), step=50)
                            with s_c3:
                                trace_price = st.number_input("주흔 1개(메소)", min_value=500.0, value=2500.0, step=100.0, format="%.0f")
                            with s_c4:
                                css_cost = st.number_input("순백1회(만)", min_value=50.0, value=450.0, step=50.0, format="%.0f")

                        scroll_norm_cost, _ = calc_scroll_expected_cost(sc_mode, auto_slots, auto_trace_per, trace_price, css_cost*2, css_cost, is_fever=False)
                        scroll_event_cost, scroll_desc = calc_scroll_expected_cost(sc_mode, auto_slots, auto_trace_per, trace_price, css_cost*2, css_cost, is_fever=True)
                        st.caption(
                            f"👉 **자동 세팅({lv_bracket[:6]} {part_type[:3]}: {auto_slots}작 / 1회당 주흔 {auto_trace_per:,}개)** | "
                            f"평일: **{fmt_man(scroll_norm_cost, '메소')}** / 🔥 **피버타임: `{fmt_man(scroll_event_cost, '메소')}`** ({scroll_desc})"
                        )

            # C단계: 스타포스
            with st.container(border=True):
                use_sf = st.checkbox("⭐ [파트 3] 스타포스 견적 포함하기 (레벨별 강화비 & 파괴 스페어 비용 자동 합산)", value=st.session_state.est_use_sf)
                st.session_state.est_use_sf = use_sf
                sf_norm_cost = 0.0
                sf_event_cost = 0.0
                sf_desc = "미포함 (또는 해방무기 기본 22성 지급)"
                if use_sf:
                    sf_goals = list(MAPLE_STARFORCE_TABLE[lv_bracket].keys())
                    sf_g_idx = sf_goals.index(st.session_state.est_sf_goal) if st.session_state.est_sf_goal in sf_goals else 3
                    sf_c1, sf_c2 = st.columns(2)
                    with sf_c1:
                        sf_target = st.selectbox("목표 스타포스 별 개수", sf_goals, index=sf_g_idx)
                        st.session_state.est_sf_goal = sf_target
                    with sf_c2:
                        sf_ev_name = st.selectbox("썬데이 스타포스 이벤트 기준", list(STARFORCE_EVENTS.keys()), index=1)

                    sf_base_info = MAPLE_STARFORCE_TABLE[lv_bracket][sf_target]
                    ev_mults = STARFORCE_EVENTS[sf_ev_name]

                    sf_norm_cost = sf_base_info["cost"] + (sf_base_info["booms"] * base_item_price)
                    ev_booms = sf_base_info["booms"] * ev_mults["boom_mult"]
                    sf_event_cost = (sf_base_info["cost"] * ev_mults["cost_mult"]) + (ev_booms * base_item_price)
                    sf_desc = f"{sf_target[:3]} (자동: 평균 파괴 {ev_booms:.2f}회 × 스페어 {fmt_man(base_item_price, '메소')})"
                    st.caption(f"👉 평일 스타포스: **{fmt_man(sf_norm_cost, '메소')}** / 🌟 **이벤트 적용 시: `{fmt_man(sf_event_cost, '메소')}`** ({sf_desc})")

            # D단계: 윗잠(잠재능력)
            with st.container(border=True):
                use_main_pot = st.checkbox("🎲 [파트 4] 윗잠(잠재능력) 견적 포함하기 (`mesu.live` 확률·레벨별 비용 100% 자동 적용)", value=st.session_state.est_use_main)
                st.session_state.est_use_main = use_main_pot
                main_norm_cost, main_mira_cost = 0.0, 0.0
                main_p50_mira, main_p85_mira, main_p95_mira = 0.0, 0.0, 0.0
                main_desc = "미포함"
                if use_main_pot:
                    m_opts = list(MAPLE_MAIN_POT_OPTIONS.keys())
                    m_idx = m_opts.index(st.session_state.est_main_opt) if st.session_state.est_main_opt in m_opts else 0
                    mc_top1, mc_top2 = st.columns([1.8, 1.0])
                    with mc_top1:
                        main_opt_sel = st.selectbox("윗잠 목표 옵션 선택 (선택 즉시 확률/등급 자동 세팅!)", m_opts, index=m_idx)
                        st.session_state.est_main_opt = main_opt_sel
                    m_info = MAPLE_MAIN_POT_OPTIONS[main_opt_sel]
                    with mc_top2:
                        m_st_idx = TIER_ORDER.index(st.session_state.est_main_start) if st.session_state.est_main_start in TIER_ORDER else 1
                        m_start_t = st.selectbox("윗잠 시작 등급 (해방무기는 유니크)", TIER_ORDER, index=m_st_idx)
                        st.session_state.est_main_start = m_start_t

                    m_targ_t = m_info["tier"]
                    m_unit_c = float(MAPLE_CUBE_COST_TABLE["윗잠 (잠재능력)"][lv_bracket][m_targ_t])
                    m_prob = float(m_info["prob_pct"]) if m_info["prob_pct"] is not None else 1.5000

                    if m_info["prob_pct"] is None or st.checkbox("✏️ 윗잠 확률/비용 수동 미세조정 (특수 옵션용)", value=False, key="m_manual_chk"):
                        mc_sub1, mc_sub2, mc_sub3 = st.columns(3)
                        with mc_sub1:
                            m_targ_t = st.selectbox("수동 목표등급", TIER_ORDER, index=TIER_ORDER.index(m_targ_t), key=f"m_tt_{main_opt_sel}")
                        with mc_sub2:
                            m_unit_c = st.number_input("수동 1회 비용(만)", value=float(MAPLE_CUBE_COST_TABLE["윗잠 (잠재능력)"][lv_bracket][m_targ_t]), step=100.0, format="%.0f", key=f"m_uc_{lv_bracket}_{m_targ_t}")
                        with mc_sub3:
                            m_prob = st.number_input("수동 확률(%)", value=m_prob, step=0.1, format="%.4f", key=f"m_pr_{main_opt_sel}")

                    m_tu_norm = calc_mesu_tierup("윗잠 (잠재능력)", lv_bracket, m_start_t, m_targ_t, False)
                    m_tu_mira = calc_mesu_tierup("윗잠 (잠재능력)", lv_bracket, m_start_t, m_targ_t, True)
                    m_opt_st = calc_mesu_option_stats(m_prob, m_unit_c)

                    main_norm_cost = m_tu_norm["mean_cost"] + m_opt_st["mean_cost"]
                    main_mira_cost = m_tu_mira["mean_cost"] + m_opt_st["mean_cost"]
                    main_p50_mira = m_tu_mira["p50_cost"] + m_opt_st["p50_cost"]
                    main_p85_mira = m_tu_mira["p85_cost"] + m_opt_st["p85_cost"]
                    main_p95_mira = m_tu_mira["p95_cost"] + m_opt_st["p95_cost"]
                    main_desc = f"{main_opt_sel[:18]} (자동: {m_prob:.3f}% / 평균 {m_opt_st['mean_tries']:.1f}회 / 1회 {int(m_unit_c):,}만)"
                    st.info(
                        f"✅ **윗잠 자동 적용됨:** `{m_start_t} ➔ {m_targ_t}` | 1회 비용 **`{fmt_man(m_unit_c, '메소')}`** | 공식 확률 **`{m_prob:.4f}%`** (평균 **`{m_opt_st['mean_tries']:.1f}회`**)\n"
                        f"👉 평일 기대 원가: **{fmt_man(main_norm_cost, '메소')}** / ✨ **미라클 데이 원가: `{fmt_man(main_mira_cost, '메소')}`**"
                    )

            # E단계: 아랫잠(에디셔널)
            with st.container(border=True):
                use_adi_pot = st.checkbox("✨ [파트 5] 아랫잠(에디셔널) 견적 동시 포함하기 (`mesu.live` 확률·레벨별 비용 100% 자동 적용)", value=st.session_state.est_use_adi)
                st.session_state.est_use_adi = use_adi_pot
                adi_norm_cost, adi_mira_cost = 0.0, 0.0
                adi_p50_mira, adi_p85_mira, adi_p95_mira = 0.0, 0.0, 0.0
                adi_desc = "미포함"
                if use_adi_pot:
                    a_opts = list(MAPLE_ADI_POT_OPTIONS.keys())
                    a_idx = a_opts.index(st.session_state.est_adi_opt) if st.session_state.est_adi_opt in a_opts else 1
                    ac_top1, ac_top2 = st.columns([1.8, 1.0])
                    with ac_top1:
                        adi_opt_sel = st.selectbox("아랫잠 목표 옵션 선택 (선택 즉시 확률/등급 자동 세팅!)", a_opts, index=a_idx)
                        st.session_state.est_adi_opt = adi_opt_sel
                    a_info = MAPLE_ADI_POT_OPTIONS[adi_opt_sel]
                    with ac_top2:
                        a_st_idx = TIER_ORDER.index(st.session_state.est_adi_start) if st.session_state.est_adi_start in TIER_ORDER else 0
                        a_start_t = st.selectbox("아랫잠 시작 등급 (해방무기는 에픽)", TIER_ORDER, index=a_st_idx)
                        st.session_state.est_adi_start = a_start_t

                    a_targ_t = a_info["tier"]
                    a_unit_c = float(MAPLE_CUBE_COST_TABLE["아랫잠 (에디셔널)"][lv_bracket][a_targ_t])
                    a_prob = float(a_info["prob_pct"]) if a_info["prob_pct"] is not None else 2.2200

                    if a_info["prob_pct"] is None or st.checkbox("✏️ 아랫잠 확률/비용 수동 미세조정 (특수 옵션용)", value=False, key="a_manual_chk"):
                        ac_sub1, ac_sub2, ac_sub3 = st.columns(3)
                        with ac_sub1:
                            a_targ_t = st.selectbox("수동 에디 등급", TIER_ORDER, index=TIER_ORDER.index(a_targ_t), key=f"a_tt_{adi_opt_sel}")
                        with ac_sub2:
                            a_unit_c = st.number_input("수동 에디 1회 비용(만)", value=float(MAPLE_CUBE_COST_TABLE["아랫잠 (에디셔널)"][lv_bracket][a_targ_t]), step=100.0, format="%.0f", key=f"a_uc_{lv_bracket}_{a_targ_t}")
                        with ac_sub3:
                            a_prob = st.number_input("수동 에디 확률(%)", value=a_prob, step=0.1, format="%.4f", key=f"a_pr_{adi_opt_sel}")

                    a_tu_norm = calc_mesu_tierup("아랫잠 (에디셔널)", lv_bracket, a_start_t, a_targ_t, False)
                    a_tu_mira = calc_mesu_tierup("아랫잠 (에디셔널)", lv_bracket, a_start_t, a_targ_t, True)
                    a_opt_st = calc_mesu_option_stats(a_prob, a_unit_c)

                    adi_norm_cost = a_tu_norm["mean_cost"] + a_opt_st["mean_cost"]
                    adi_mira_cost = a_tu_mira["mean_cost"] + a_opt_st["mean_cost"]
                    adi_p50_mira = a_tu_mira["p50_cost"] + a_opt_st["p50_cost"]
                    adi_p85_mira = a_tu_mira["p85_cost"] + a_opt_st["p85_cost"]
                    adi_p95_mira = a_tu_mira["p95_cost"] + a_opt_st["p95_cost"]
                    adi_desc = f"{adi_opt_sel[:18]} (자동: {a_prob:.3f}% / 평균 {a_opt_st['mean_tries']:.1f}회 / 1회 {int(a_unit_c):,}만)"
                    st.info(
                        f"✅ **아랫잠 자동 적용됨:** `{a_start_t} ➔ {a_targ_t}` | 1회 비용 **`{fmt_man(a_unit_c, '메소')}`** | 공식 확률 **`{a_prob:.4f}%`** (평균 **`{a_opt_st['mean_tries']:.1f}회`**)\n"
                        f"👉 평일 기대 원가: **{fmt_man(adi_norm_cost, '메소')}** / ✨ **미라클 데이 원가: `{fmt_man(adi_mira_cost, '메소')}`**"
                    )

        # 오른쪽 컬럼: 올인원 종합 영수증 & 시장 보정% 반영 최종 판정
        with e_col2:
            with st.container(border=True):
                st.markdown("##### 🧾 올인원(All-in-One) 완제품 원가 영수증 & AI 매물 감정 결과")

                fixed_base_part = base_item_price + scissors_cost + flame_norm_cost
                grand_total_normal = fixed_base_part + scroll_norm_cost + sf_norm_cost + main_norm_cost + adi_norm_cost
                grand_total_event = fixed_base_part + scroll_event_cost + sf_event_cost + main_mira_cost + adi_mira_cost

                val_mult = 1.0 + (market_valuation_shift / 100.0)
                fair_market_normal = grand_total_normal * val_mult
                fair_market_event = grand_total_event * val_mult

                m_top1, m_top2, m_top3 = st.columns(3)
                m_top1.metric("📅 평일 직작 총 원가", fmt_man(grand_total_normal, "메소"), "노이벤트 기준")
                m_top2.metric("✨ 이벤트 풀활용 총 원가", fmt_man(grand_total_event, "메소"), f"평일 대비 -{fmt_man(grand_total_normal - grand_total_event, '메소')} 절약")
                m_top3.metric(
                    f"⚖️ 보정({market_valuation_shift:+.0f}%) 적정 시세",
                    fmt_man(fair_market_event, "메소"),
                    f"현재 경매장가: {fmt_man(auction_finished_price, '메소')}"
                )

                receipt_rows = [
                    {"제작 단계": "🛒 0. 노작 베이스 + 가위값", "평일 원가": fmt_man(base_item_price + scissors_cost, "메소"), "✨이벤트(미라클/피버/썬데이) 원가": fmt_man(base_item_price + scissors_cost, "메소"), "자동 적용된 스펙/근거": f"노작 {fmt_man(base_item_price, '메소')} + 가위 {fmt_man(scissors_cost, '메소')}"},
                    {"제작 단계": "🔥 1. 추가옵션 (환불)", "평일 원가": fmt_man(flame_norm_cost, "메소"), "✨이벤트(미라클/피버/썬데이) 원가": fmt_man(flame_norm_cost, "메소"), "자동 적용된 스펙/근거": flame_desc},
                    {"제작 단계": "📜 2. 주문서 작 (주흔/기타)", "평일 원가": fmt_man(scroll_norm_cost, "메소"), "✨이벤트(미라클/피버/썬데이) 원가": fmt_man(scroll_event_cost, "메소"), "자동 적용된 스펙/근거": scroll_desc},
                    {"제작 단계": "⭐ 3. 스타포스 (스페어포함)", "평일 원가": fmt_man(sf_norm_cost, "메소"), "✨이벤트(미라클/피버/썬데이) 원가": fmt_man(sf_event_cost, "메소"), "자동 적용된 스펙/근거": sf_desc},
                    {"제작 단계": "🎲 4. 윗잠재능력 (잠재)", "평일 원가": fmt_man(main_norm_cost, "메소"), "✨이벤트(미라클/피버/썬데이) 원가": fmt_man(main_mira_cost, "메소"), "자동 적용된 스펙/근거": main_desc},
                    {"제작 단계": "✨ 5. 아랫잠재능력 (에디)", "평일 원가": fmt_man(adi_norm_cost, "메소"), "✨이벤트(미라클/피버/썬데이) 원가": fmt_man(adi_mira_cost, "메소"), "자동 적용된 스펙/근거": adi_desc},
                ]
                st.dataframe(pd.DataFrame(receipt_rows), use_container_width=True, hide_index=True)

                non_pot_event_base = fixed_base_part + scroll_event_cost + sf_event_cost
                p50_tot = non_pot_event_base + main_p50_mira + adi_p50_mira
                p85_tot = non_pot_event_base + main_p85_mira + adi_p85_mira
                p95_tot = non_pot_event_base + main_p95_mira + adi_p95_mira
                st.caption(
                    f"📊 **잠재능력 운빨 분포 포함 총 제작비 (이벤트 날 기준):** "
                    f"🍀 상위 50%(중앙값) **`{fmt_man(p50_tot, '메소')}`** | "
                    f"🛡️ 85% 안전선 **`{fmt_man(p85_tot, '메소')}`** | "
                    f"⚠️ 95% 억까선 **`{fmt_man(p95_tot, '메소')}`**"
                )

                st.divider()

                if auction_finished_price <= 0:
                    st.info("💡 **순수 직작 견적 모드 (제네시스 해방 무기 등 교환불가 장비):** 위 영수증의 **`✨이벤트 풀활용 총 원가`**와 **`상위 50%~85% 안전선`** 예산을 목표로 메소를 모으시면 됩니다!")
                else:
                    net_sell_revenue = auction_finished_price * fee_mult
                    flip_profit_event = net_sell_revenue - grand_total_event
                    flip_profit_normal = net_sell_revenue - grand_total_normal

                    st.markdown(f"###### ⚖️ 판정 1: 직접 풀세팅 제작 후 경매장에 `{fmt_man(auction_finished_price, '메소')}`에 팔 때 (장사꾼 관점)")
                    if flip_profit_event > 0 and flip_profit_normal > 0:
                        st.success(
                            f"🟢 **[직작 장사 강력 추천!]** 평일에 만들어 팔아도 평균 **`+{fmt_man(flip_profit_normal, '메소')}`** 이득이며, "
                            f"**✨이벤트 날(미라클/썬데이)**에 제작해 팔면 수수료({fee_pct_str})를 떼고도 평균 **`+{fmt_man(flip_profit_event, '메소')}`**의 순마진이 남습니다!"
                        )
                    elif flip_profit_event > 0 and flip_profit_normal <= 0:
                        st.warning(
                            f"🟡 **[이벤트 데이 전용 장사템!]** 평일에 만들면 **`{fmt_man(flip_profit_normal, '메소')}` 적자**지만, "
                            f"**✨미라클/썬데이 이벤트**를 활용해 만들면 평균 **`+{fmt_man(flip_profit_event, '메소')}` 흑자**가 납니다!"
                        )
                    else:
                        st.error(
                            f"🔴 **[직작 장사 금지 - 적자 경고!]** 이벤트 날에 모든 할인을 받아 만들어도 평균 **`{fmt_man(flip_profit_event, '메소')}` 손해**입니다! "
                            f"절대 직접 만들어 팔지 마세요."
                        )

                    diff_from_fair = auction_finished_price - fair_market_event
                    st.markdown(f"###### 🛒 판정 2: 현재 경매장 매물가(`{fmt_man(auction_finished_price, '메소')}`) vs 보정 적정 시세(`{fmt_man(fair_market_event, '메소')}`)")
                    if diff_from_fair < 0:
                        st.info(
                            f"💎 **[꿀매물 / 완제품 구매 추천!]** 현재 경매장 가격이 시장 보정({market_valuation_shift:+.0f}%)을 감안한 적정 제작가보다도 "
                            f"**`{fmt_man(abs(diff_from_fair), '메소')}` 더 저렴합니다!** 직접 만들지 말고 경매장 매물을 바로 구매하시는 것이 무조건 이득입니다."
                        )
                    else:
                        st.info(
                            f"🛠️ **[경매장 거품 / 직작 우위]** 경매장 매물이 적정 시세보다 **`+{fmt_man(diff_from_fair, '메소')}` 비싸게** 올라와 있습니다. "
                            f"급하지 않다면 이벤트 날 직접 제작하거나 가격 흥정을 추천합니다."
                        )

                if st.button("📌 이 올인원 종합 견적을 아래 비교 리스트에 저장하기", use_container_width=True):
                    net_s = auction_finished_price * fee_mult
                    fp_ev = net_s - grand_total_event
                    df_fair = auction_finished_price - fair_market_event
                    mp_data["saved_evals"].append({
                        "아이템명": eval_item_name,
                        "레벨구간": lv_bracket[:7],
                        "세팅요약": f"{sf_desc[:3] if use_sf else '노성'}/{main_desc[:10] if use_main_pot else '노윗잠'}/{adi_desc[:10] if use_adi_pot else '노에디'}",
                        "평일총원가": fmt_man(grand_total_normal, "메소"),
                        "✨이벤트총원가": fmt_man(grand_total_event, "메소"),
                        f"보정시세({market_valuation_shift:+.0f}%)": fmt_man(fair_market_event, "메소"),
                        "경매장매물가": fmt_man(auction_finished_price, "메소") if auction_finished_price > 0 else "교불(직작)",
                        "장사순마진": (f"+{fmt_man(fp_ev, '메소')}" if fp_ev >= 0 else fmt_man(fp_ev, "메소")) if auction_finished_price > 0 else "-",
                        "최종판정": "⚔️해방/교불직작" if auction_finished_price <= 0 else ("🟢직작장사추천" if fp_ev > 0 else ("💎완제꿀매물" if df_fair < 0 else "🔴관망"))
                    })
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.rerun()

        if mp_data.get("saved_evals"):
            with st.expander("📋 내가 저장해 둔 올인원 종합 견적 비교 리스트", expanded=True):
                st.dataframe(pd.DataFrame(mp_data["saved_evals"]), use_container_width=True, hide_index=True)
                if st.button("🗑️ 저장된 비교 리스트 비우기"):
                    mp_data["saved_evals"] = []
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True; st.rerun()

        st.divider()

        with st.expander("📚 [데이터 총람] mesu.live 기준 잠재/스타포스/추옵 AI 산출 수치 원본 표 보기", expanded=False):
            st.markdown("##### 📌 1. 레벨 구간별 1회 잠재능력 재설정 비용 정가표")
            cost_guide_rows = []
            for c_type, brackets in MAPLE_CUBE_COST_TABLE.items():
                for brk, tiers in brackets.items():
                    cost_guide_rows.append({
                        "구분": c_type, "레벨 구간": brk,
                        "레어 1회": fmt_man(tiers["레어"], "메소"), "에픽 1회": fmt_man(tiers["에픽"], "메소"),
                        "유니크 1회": fmt_man(tiers["유니크"], "메소"), "레전드리 1회": fmt_man(tiers["레전드리"], "메소")
                    })
            st.dataframe(pd.DataFrame(cost_guide_rows), use_container_width=True, hide_index=True)

            st.markdown("##### 📌 2. 레벨 구간별 등급업(천장 시스템 반영) 기댓값 비교표")
            tier_guide_rows = []
            for c_type, brackets in MAPLE_CUBE_COST_TABLE.items():
                for brk in brackets.keys():
                    ep_norm = calc_mesu_tierup(c_type, brk, "에픽", "레전드리", False)
                    ep_mira = calc_mesu_tierup(c_type, brk, "에픽", "레전드리", True)
                    tier_guide_rows.append({
                        "구분": c_type, "레벨 구간": brk,
                        "에픽->레전 평균(평일)": fmt_man(ep_norm["mean_cost"], "메소"),
                        "에픽->레전 평균(✨미라클)": fmt_man(ep_mira["mean_cost"], "메소"),
                        "에픽->레전 50%중앙값(미라클)": fmt_man(ep_mira["p50_cost"], "메소"),
                        "에픽->레전 100%천장합계": fmt_man(ep_norm["ceil_cost"], "메소"),
                    })
            st.dataframe(pd.DataFrame(tier_guide_rows), use_container_width=True, hide_index=True)

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
                        "id": new_lid, "날짜": log_date,
                        "시세(1억당메포)": float(log_rate), "메모": log_memo.strip()
                    })
                    mm_cfg["current_watch_rate"] = float(log_rate)
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.session_state.mp_editor_ver += 1
                    st.toast(f"✅ 메소마켓 시세(1억당 {int(log_rate):,} 메포)가 기록되었습니다!")
                    st.rerun()

                st.divider()
                st.markdown("##### ⚙️ 2. 외부 요인(인플레/패치/이벤트) 과거 기준선 `%` 일괄 보정")
                s_c1, s_c2 = st.columns(2)
                with s_c1:
                    shift_pct = st.number_input(
                        "🎚️ 과거 기준선 일괄 변동률 (%)",
                        min_value=-80.0, max_value=200.0, value=float(mm_cfg.get("shift_pct", 0.0)), step=1.0, format="%.1f"
                    )
                with s_c2:
                    band_th = st.number_input(
                        "🎯 매수/매도 추천 민감도 (±%)",
                        min_value=1.0, max_value=30.0, value=float(mm_cfg.get("band_threshold", 5.0)), step=0.5, format="%.1f"
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
                            f"현재 시세(`{cur_watch:,.0f} P`)가 보정된 과거 평균(`{adj_avg:,.0f} P`)보다 **`+{diff_pct_from_adj:.1f}%` 높은 고점**입니다!"
                        )
                    elif cur_watch <= sell_mp_trigger:
                        st.error(
                            f"🔴 **[AI 강력 추천: 지금 보유한 '메이플포인트'를 팔아 메소를 확보하세요!]**\n\n"
                            f"현재 시세(`{cur_watch:,.0f} P`)가 보정된 과거 평균(`{adj_avg:,.0f} P`)보다 **`{diff_pct_from_adj:.1f}%` 낮은 저점(메포 가치 폭등)**입니다!"
                        )
                    else:
                        st.warning(
                            f"🟡 **[AI 판정: 중립 / 관망 구간입니다]**\n\n"
                            f"현재 시세(`{cur_watch:,.0f} P`)가 보정 평균(`{adj_avg:,.0f} P`) 근처(`{diff_pct_from_adj:+.1f}%`)에서 움직이고 있습니다."
                        )

        st.divider()
        sub_c1, sub_c2 = st.columns(2, gap="large")

        with sub_c1:
            st.markdown("##### 📊 꾸준히 기록한 메소마켓 시세 일지")
            if rate_logs:
                shift_mult = 1.0 + ( float(mm_cfg.get("shift_pct", 0.0)) / 100.0 )
                log_rows = []
                for x in sorted(rate_logs, key=lambda i: i.get("id", 0), reverse=True):
                    r_val = float(x.get("시세(1억당메포)", 2400.0))
                    log_rows.append({
                        "id": x["id"], "날짜": str(x.get("날짜", "")),
                        "시세(1억당메포)": r_val, "보정환산시세": round(r_val * shift_mult, 0),
                        "메모": str(x.get("메모", "")), "삭제": False
                    })
                edited_logs = st.data_editor(
                    pd.DataFrame(log_rows),
                    column_config={
                        "id": None, "날짜": st.column_config.TextColumn("✏️ 날짜", width="small"),
                        "시세(1억당메포)": st.column_config.NumberColumn("✏️ 기록 시세", format="%d P"),
                        "보정환산시세": st.column_config.NumberColumn(f"보정 시세({mm_cfg.get('shift_pct',0):+.1f}%)", format="%d P", disabled=True),
                        "메모": st.column_config.TextColumn("✏️ 메모", width="medium"),
                        "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small")
                    },
                    use_container_width=True, hide_index=True, key=f"mm_rate_log_ed_{st.session_state.mp_editor_ver}"
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
                        "id": None, "날짜": st.column_config.TextColumn("일시", width="small"),
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

        with st.expander("📖 3. 메이플 매입 족보 (시세 변동 `%` 보정 지원) & 과거 거래 영수증 / 엑셀(CSV) 다운로드", expanded=False):
            if not mp_trades:
                st.caption("아직 등록된 메이플 장사 내역이 없습니다.")
            else:
                mjb_c1, mjb_c2, mjb_c3 = st.columns([1.5, 1.5, 1.2])
                with mjb_c1:
                    mp_search_kw = st.text_input("🔍 메이플 족보/과거기록 아이템 검색", key="mp_jokbo_search")
                with mjb_c2:
                    mp_shift = st.number_input(
                        "🎚️ 메이플 전체 템 시세 변동 보정 (%)",
                        min_value=-80.0, max_value=200.0, value=float(mp_data.get("jokbo_shift_pct", 0.0)), step=5.0, format="%.1f"
                    )
                    if mp_shift != float(mp_data.get("jokbo_shift_pct", 0.0)):
                        mp_data["jokbo_shift_pct"] = mp_shift
                        save_json_local(MAPLE_FILE, mp_data)
                        st.session_state.mp_dirty = True
                with mjb_c3:
                    st.write("")
                    csv_mp = pd.DataFrame(mp_trades).to_csv(index=False).encode("utf-8-sig")
                    st.download_button(
                        "📥 메이플 전체 장부 엑셀(CSV) 다운로드",
                        data=csv_mp,
                        file_name=f"maple_trades_{cur_ym}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                mp_mult = 1.0 + (mp_shift / 100.0)
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
                    adj_avg_buy = avg_buy * mp_mult
                    adj_be_price = math.ceil(adj_avg_buy / fee_mult)
                    avg_sell_str = f"{int(jb['판매합계']/jb['판매수량']):,}만" if jb["판매수량"] > 0 else "판매전"
                    mp_jokbo_rows.append({
                        "아이템명": nm,
                        "누적매입": f"{jb['총 매입수량']}개",
                        "원본 평단가": f"{int(avg_buy):,}만",
                        f"보정 평단가({mp_shift:+.0f}%)": f"{int(adj_avg_buy):,}만 ({fmt_man(adj_avg_buy, '메소')})",
                        "최고비싸게산값": f"{int(jb['최고 매입가']):,}만",
                        "최저매입가": f"{int(jb['최저 매입가']):,}만",
                        f"보정 {fee_pct_str}본전가": f"{adj_be_price:,}만",
                        "평균판매가": avg_sell_str,
                        "누적순수익": fmt_man(jb["누적 순수익"], "메소"),
                    })

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

    # --------------------------------------------------------------------------
    # 📘 [서브탭 5] 직작 & 장사 백과사전 (1추/2추, 방어구 급수 계산기, 작 보는 법, 대장장이/합성/토드 완벽 가이드)
    # --------------------------------------------------------------------------
    with mp_sub5:
        st.markdown("#### 📘 메이플스토리 직작 & 장사 필수 백과사전 (언제든 꺼내 보는 실전 매뉴얼)")
        st.caption("경매장에서 매물을 보거나 직접 아이템을 제작·합성·강화해서 팔 때 반드시 알아야 할 핵심 개념과 공식을 한눈에 볼 수 있게 정리했습니다.")

        # 실시간 방어구/장신구 추옵 급수 암산 도우미 내장!
        with st.container(border=True):
            st.markdown("##### 🧮 1초 만에 계산하는 '방어구/장신구 추옵 급수(OO급)' 계산기 & 보는 법")
            st.markdown(
                "인게임 아이템 툴팁에서 **초록색 숫자(`+OO`)**로 적힌 추가옵션 수치를 아래에 넣으면 몇 급인지 즉시 계산됩니다! "
                "**(공식: `주스탯 1 = 1급` / `공격력·마력 1 = 4급` / `올스탯 1% = 10급` / `부스탯 10 = 1급`)**"
            )
            fc1, fc2, fc3, fc4, fc5 = st.columns([1, 1, 1, 1, 1.5])
            with fc1:
                g_stat = st.number_input("초록색 주스탯 (+)", min_value=0, max_value=200, value=60, step=5)
            with fc2:
                g_att = st.number_input("초록색 공/마 (+)", min_value=0, max_value=30, value=5, step=1)
            with fc3:
                g_all = st.number_input("초록색 올스탯% (+)", min_value=0, max_value=10, value=5, step=1)
            with fc4:
                g_sub = st.number_input("초록색 부스탯 (+)", min_value=0, max_value=200, value=0, step=10)
            with fc5:
                calc_grade = g_stat + (g_att * 4) + (g_all * 10) + round(g_sub * 0.1, 1)
                st.metric("🔥 이 아이템의 추옵 급수", f"{calc_grade:.0f} 급", f"스탯{g_stat} + 공마({g_att}×4) + 올스탯({g_all}%×10)")

            grade_table = [
                {"장비 종류": "👑 보스 방어구/장신구 (데브펜, 트와마, 가엔링, 아케인, 앱솔 등)", "추옵 특징": "보스 추옵 보정 O (최대 4줄 고정, 높은 수치 등장)", "가성비/부캐용": "100급 ~ 110급", "국민 본캐용 (가장 거래 활발)": "120급 ~ 130급", "고스펙/준종결 (비쌈)": "140급 ~ 150급+"},
                {"장비 종류": "👓 일반 제작/드롭 장비 (미카엘라 새안경, 하프이어링, 마이스터링 등)", "추옵 특징": "보스 추옵 보정 X (1~4줄 랜덤, 낮은 수치 등장)", "가성비/부캐용": "50급 ~ 65급", "국민 본캐/드메용": "75급 ~ 85급 (보장 120급 가치)", "고스펙/준종결 (비쌈)": "95급 ~ 110급+ (극추옵)"},
            ]
            st.dataframe(pd.DataFrame(grade_table), use_container_width=True, hide_index=True)

        g_col1, g_col2 = st.columns(2, gap="large")

        with g_col1:
            with st.container(border=True):
                st.markdown("##### ⚔️ 2. 무기 '1추옵 / 2추옵' 완벽 이해하기")
                st.markdown(
                    """
                    무기는 방어구처럼 'OO급'으로 부르지 않고 **초록색 공격력/마력이 몇 단계로 붙었는가(`1추옵 ~ 5추옵`)**로 부릅니다.
                    * **1추옵 (5단계 최고 수치):** 해당 무기에 붙을 수 있는 가장 높은 추가 공격력/마력입니다.
                    * **2추옵 (4단계 차상위 수치):** 1추옵 바로 아래 단계의 추가 공격력/마력입니다.
                    * **💡 무기 추옵 장사/직작 핵심 기준:**
                      1. **해방 전 임시 무기 (17~18성 아케인):** **`2추옵 + 보공`** 또는 **`1추옵 단독`**이면 충분합니다. (절대 영환불/검환불을 많이 쓰지 마세요!)
                      2. **제네시스 해방 무기 (최종 무기):** 해방 무기는 평생 쓰는 무기이므로 **`1추옵 + 보공 + 데미지/올스탯/주스탯`** 또는 최소 **`2추옵 + 보공 10~12% + 데미지/주스탯`**을 목표로 돌립니다.
                    """
                )
                wp_table = [
                    {"무기 등급": "200제 제네시스 무기 (해방)", "추옵 특징": "보스 추옵 보정 O", "1추옵 비율": "무기 기본 공/마의 약 44%~51%", "국민 목표 옵션": "1추옵 + 보공 (또는 2추+보공+뎀)"},
                    {"무기 등급": "200제 아케인셰이드 무기", "추옵 특징": "보스 추옵 보정 O", "1추옵 비율": "무기 기본 공/마의 약 44%~51%", "국민 목표 옵션": "해방 전 임시용: 1추 단독 or 2추+보공"},
                    {"무기 등급": "160제 앱솔랩스 무기", "추옵 특징": "보스 추옵 보정 O", "1추옵 비율": "무기 기본 공/마의 약 36%~42%", "국민 목표 옵션": "부캐 주보돌이용: 1~2추옵 아무거나"},
                ]
                st.dataframe(pd.DataFrame(wp_table), use_container_width=True, hide_index=True)

            with st.container(border=True):
                st.markdown("##### 🔨 3. 대장장이(장비/장신구 제작) & 합성 & 토드의 망치 장사 가이드")
                st.markdown(
                    """
                    * **💍 장신구/장비 제작 & 합성 장사 원리:**
                      1. 마이스터빌에서 피로도를 써서 **미카엘라의 새 안경(90제), 하프 이어링(75제), 골든 클로버 벨트, 데아 시두스 이어링** 등을 대량 제작하거나 경매장에서 싼 노작을 매입합니다.
                      2. **장비 합성(연금술):** 노작 2개를 합성하면 확률적으로 **에픽 잠재능력**이나 **고추옵(80~100급)**이 뜹니다.
                      3. **미라클 데이 활용:** 합성이나 제작으로 만든 템을 미라클 데이에 **레전드리 등업 $\\rightarrow$ 아획/메획(드메) 1~2줄**을 띄워 팔면 노작 대비 수십억 메소의 마진이 남습니다.
                    * **🔨 토드의 망치 (에픽 2줄 장사) 원리:**
                      1. 큐브 감정비가 거의 안 드는 **저레벨 장비(80~120제)**에서 수상한 큐브로 **`에픽 주스탯 9%~12%(2줄)`** 및 **`에디셔널 공/마 +10`**을 싸게 띄웁니다.
                      2. `토드의 망치`로 10레벨 단위씩 상위 장비로 전승시켜 **160제(앱솔랩스/데브펜/트와마) 또는 200제**에 옮겨 담아 경매장에 팔면, 직접 고레벨 템에 큐브를 돌리는 것보다 원가가 절반 이하로 줄어듭니다!
                    """
                )

        with g_col2:
            with st.container(border=True):
                st.markdown("##### 📜 4. 경매장 완제품 '작(주문서 강화) 상태' 구별하는 법")
                st.markdown(
                    """
                    아이템 툴팁에서 **`파란색 글씨(+OO)`로 오른 총 수치**에서 **`초록색 추옵(+OO)`과 `스타포스 상승분`을 뺀 수치**(또는 메수라이브/인게임 상세 툴팁의 주문서 상승치)를 보면 무슨 작이 발렸는지 바로 알 수 있습니다!
                    """
                )
                scr_table = [
                    {"부위 및 작 이름": "⚔️ 무기: 주흔 15% 완작", "1작당 상승 수치": "공/마 +9, 주스탯 +4", "주요 사용처": "본캐 아케인 무기, 제네시스 해방 무기(기본 지급)"},
                    {"부위 및 작 이름": "🛡️ 방어구: 주흔 30% 완작", "1작당 상승 수치": "주스탯 +7 (120제+), 4번째 성공 시 공/마+1", "주요 사용처": "본캐 17~22성 앱솔/아케인/에테르넬 방어구 정석"},
                    {"부위 및 작 이름": "🛡️ 방어구/장신구: 주흔 70% 완작", "1작당 상승 수치": "주스탯 +4 (방어구) / +2~3 (장신구)", "주요 사용처": "가성비 부캐, 드메템(미카엘라 등), 토드용 베이스"},
                    {"부위 및 작 이름": "🧤 장갑: 주흔 15% / 30% 완작", "1작당 상승 수치": "공/마 +4 (15%작) / 공/마 +3 (30%작)", "주요 사용처": "장갑은 스탯이 아니라 무조건 공격력/마력 작!"},
                    {"부위 및 작 이름": "💍 장신구: 놀긍혼 (긍정의 혼돈)", "1작당 상승 수치": "공/마 0~+6 랜덤 (평균 공/마 +3 이상이면 상급)", "주요 사용처": "18~22성 여명/칠흑 장신구 가성비 고스펙 작"},
                    {"부위 및 작 이름": "👑 장신구: 프악공 / 프악마", "1작당 상승 수치": "1장당 공/마 +4~5 확정 상승", "주요 사용처": "22성 칠흑 등 초고자본 종결 장신구 (작값만 수십억)"},
                ]
                st.dataframe(pd.DataFrame(scr_table), use_container_width=True, hide_index=True)

            with st.container(border=True):
                st.markdown("##### 📖 5. 메이플 장사꾼 필수 은어 & 줄임말 사전")
                term_table = [
                    {"용어": "드메템 (아획/메획)", "뜻과 장사 포인트": "아이템 드롭률 +20% / 메소 획득량 +20% 잠재가 붙은 장신구(반지4, 펜던트2, 얼굴, 눈, 귀고리 총 9부위). 사냥 필수품이라 거래량이 가장 많고 환금성이 최고인 장사 종목!"},
                    {"용어": "무보엠", "뜻과 장사 포인트": "무기 + 보조무기 + 엠블렘 3부위. 스탯% 대신 '보스 공격력(보공)%', '공격력/마력(공마)%', '방어율 무시(방무)%'가 뜨는 가장 중요한 딜 상승 부위."},
                    {"용어": "정옵 / 이탈옵", "뜻과 장사 포인트": "정옵(예: 레전 12%+9%+9%=30%), 이탈옵(두 번째·세 번째 줄에서도 첫 줄 최고 수치인 12%가 뜬 12%+12%+9%=33% 같은 고가 매물)."},
                    {"용어": "크뎀 장갑 (1줄/2줄)", "뜻과 장사 포인트": "장갑 레전드리에서만 뜨는 '크리티컬 데미지 +8%'. 크뎀 1줄은 주스탯 약 24~27%급 효율, 크뎀 2줄(16%)은 종결급으로 고가에 거래됨."},
                    {"용어": "쿨감뚝 (-2초/-3초/-4초)", "뜻과 장사 포인트": "모자 레전드리에서만 뜨는 '모든 스킬의 재사용 대기시간 -2초'. 특정 직업들의 필수 부위라 미라클 데이에 쿨감 3초~4초가 뜨면 대박 마진 가능."},
                    {"용어": "노작 / 스페어", "뜻과 장사 포인트": "아무 강화도 안 된 순수 원본 아이템. 스타포스 18~22성 도전 중 장비가 파괴(펑)되었을 때 전승 복구용으로 똑같은 노작 장비(스페어) 1개가 소모됨."},
                ]
                st.dataframe(pd.DataFrame(term_table), use_container_width=True, hide_index=True)
