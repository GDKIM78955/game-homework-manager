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
        "loa_krw_per_10k_gold": 3500.0,
        "loa_hourly_gold": 15000.0,
        "loa_monthly_gold_sold": 0.0,
        "gs_krw_per_1eok": 1800.0,
        "mp_krw_per_1eok": 2200.0
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
# ⚓ 1. 로스트아크 데이터 및 로직 (7~11레벨 보석 개수 필드 포함)
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
            "카던큐브": "",
            "보석7": 0, "보석8": 0, "보석9": 0, "보석10": 0, "보석11": 0,
            "보석메모": "",
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
        for lv in range(7, 12):
            row.setdefault(f"보석{lv}", 0)
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
        "jokbo_shift_pct": 0.0,
        "daily_tasks": {"quest": False, "factory": False, "hunt_goal": False},
        "client2_farm": {
            "current_money": 0.0,
            "profit_link_mode": PROFIT_LINK_OPTS[0],
            "drop_item_name": "주력 드랍템",
            "drop_item_price": 10.0,
            "drops_per_hour": 30.0,
            "extra_hourly_man": 500.0,
            "daily_hours": 2.0,
            "targets": []
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
# 🍁 3. 메이플스토리 2026 넥슨 공식 확률·비용 통합 엔진 (잠재 4구간 + 2025개편 스타포스 수식)
# ==============================================================================
# [A] 넥슨 공식 잠재능력 1회 재설정 비용 정가표 (4구간 통일, 단위: 만 메소)
MAPLE_CUBE_COST_TABLE = {
    "윗잠 (잠재능력)": {
        "1~159제 (미카엘라/이벤링/보장/루타비스)": {"레어": 400.0, "에픽": 1600.0, "유니크": 3400.0, "레전드리": 4000.0},
        "160~199제 (여명/앱솔랩스)": {"레어": 425.0, "에픽": 1700.0, "유니크": 3612.5, "레전드리": 4250.0},
        "200~249제 (아케인셰이드/칠흑/제네시스)": {"레어": 450.0, "에픽": 1800.0, "유니크": 3825.0, "레전드리": 4500.0},
        "250~300제 (에테르넬/광휘)": {"레어": 500.0, "에픽": 2000.0, "유니크": 4250.0, "레전드리": 5000.0},
    },
    "아랫잠 (에디셔널)": {
        "1~159제 (미카엘라/이벤링/보장/루타비스)": {"레어": 1950.0, "에픽": 3900.0, "유니크": 6630.0, "레전드리": 7800.0},
        "160~199제 (여명/앱솔랩스)": {"레어": 2072.0, "에픽": 4144.0, "유니크": 7044.0, "레전드리": 8288.0},
        "200~249제 (아케인셰이드/칠흑/제네시스)": {"레어": 2200.0, "에픽": 4400.0, "유니크": 7480.0, "레전드리": 8800.0},
        "250~300제 (에테르넬/광휘)": {"레어": 2450.0, "에픽": 4900.0, "유니크": 8330.0, "레전드리": 9800.0},
    }
}

# 레벨 구간별 대표 스타포스 장비 레벨 기본값
BRACKET_DEFAULT_LV = {
    "1~159제 (미카엘라/이벤링/보장/루타비스)": 150,
    "160~199제 (여명/앱솔랩스)": 160,
    "200~249제 (아케인셰이드/칠흑/제네시스)": 200,
    "250~300제 (에테르넬/광휘)": 250,
}

# [B] 넥슨 공식 메소 재설정 등급업 확률(p) + 천장 횟수(pity)
MAPLE_TIERUP_SPEC = {
    "윗잠 (잠재능력)": {
        "레어->에픽": {"p": 0.150000, "pity": 10},
        "에픽->유니크": {"p": 0.035000, "pity": 42},
        "유니크->레전드리": {"p": 0.014000, "pity": 107}
    },
    "아랫잠 (에디셔널)": {
        "레어->에픽": {"p": 0.023810, "pity": 62},
        "에픽->유니크": {"p": 0.009804, "pity": 152},
        "유니크->레전드리": {"p": 0.007000, "pity": 214}
    }
}

MAPLE_EQUIP_PARTS = ["장신구 (반지/펜던트/귀고리/얼장/눈장)", "방어구 (상의/하의/신발/망토/어깨)", "장갑", "모자", "무보엠 (무기/보조/엠블렘)"]

# [C] 부위 필터 지원 윗잠/아랫잠 공식 확률 프리셋
MAPLE_MAIN_POT_OPTIONS = {
    "[레전드리/장신구] 드랍 or 메획 1줄 이상 (20%+)": {"prob_pct": 15.8200, "tier": "레전드리", "parts": ["장신구"]},
    "[레전드리/장신구] 드랍+메획 총합 2줄 이상 (드메 2줄 핵심!)": {"prob_pct": 1.3960, "tier": "레전드리", "parts": ["장신구"]},
    "[레전드리/장신구] 드랍 or 메획 1줄 + 주스탯 2줄": {"prob_pct": 1.1200, "tier": "레전드리", "parts": ["장신구"]},
    "[레전드리/장신구] 드랍+메획 총합 3줄 (극옵 드메 3줄)": {"prob_pct": 0.0385, "tier": "레전드리", "parts": ["장신구"]},
    "[레전드리] 주스탯 21% 이상 (올스탯 포함)": {"prob_pct": 6.4500, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[레전드리] 주스탯 24% 이상 (정옵 2줄+)": {"prob_pct": 3.1800, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[레전드리] 주스탯 27% 이상 (준3줄 국민옵)": {"prob_pct": 1.5400, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[레전드리] 주스탯 30% 이상 (3줄 정옵)": {"prob_pct": 0.5780, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[레전드리] 주스탯 33% 이상 (극옵 3줄)": {"prob_pct": 0.2190, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[레전드리/장갑] 크리티컬 데미지 1줄(8%) + 주스탯 1줄+": {"prob_pct": 5.6200, "tier": "레전드리", "parts": ["장갑"]},
    "[레전드리/장갑] 크리티컬 데미지 2줄 (16% 이상)": {"prob_pct": 0.7420, "tier": "레전드리", "parts": ["장갑"]},
    "[레전드리/모자] 쿨타임 감소 -2초 이상 (주스탯 무관)": {"prob_pct": 6.8500, "tier": "레전드리", "parts": ["모자"]},
    "[레전드리/모자] 쿨타임 감소 -2초 + 주스탯 1줄+": {"prob_pct": 2.9500, "tier": "레전드리", "parts": ["모자"]},
    "[레전드리/모자] 쿨타임 감소 -3초 이상": {"prob_pct": 1.4800, "tier": "레전드리", "parts": ["모자"]},
    "[레전드리/모자] 쿨타임 감소 -4초 이상": {"prob_pct": 0.3520, "tier": "레전드리", "parts": ["모자"]},
    "[레전드리/무보엠] 보공/방무/공마 유효 2줄": {"prob_pct": 8.3300, "tier": "레전드리", "parts": ["무보엠"]},
    "[레전드리/무보엠] 보공/공마 유효 3줄 (방무 제외)": {"prob_pct": 0.9120, "tier": "레전드리", "parts": ["무보엠"]},
    "[레전드리/무보엠] 공격력/마력 21% 이상 (2줄+)": {"prob_pct": 3.5800, "tier": "레전드리", "parts": ["무보엠"]},
    "[레전드리/무보엠] 공격력/마력 30% 이상 (3줄)": {"prob_pct": 0.2640, "tier": "레전드리", "parts": ["무보엠"]},
    "[유니크] 주스탯 15% ~ 18% (유니크 2줄)": {"prob_pct": 6.6700, "tier": "유니크", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[에픽] 주스탯 9% ~ 12% (에픽 2줄 토드용)": {"prob_pct": 10.2000, "tier": "에픽", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[에픽/무보엠] 공격력/마력 9% ~ 12% (에픽 2줄)": {"prob_pct": 6.8000, "tier": "에픽", "parts": ["무보엠"]},
    "🔗 mesu.live 세부 확률(%) 직접 입력": {"prob_pct": None, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자", "무보엠"]}
}

MAPLE_ADI_POT_OPTIONS = {
    "[아랫잠/레어] 공/마 +10 (에디 레어 1줄 가성비)": {"prob_pct": 6.2500, "tier": "레어", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[아랫잠/에픽] 공/마 +10 또는 주스탯 4%+ (에디 에픽 1.5~2줄)": {"prob_pct": 5.5500, "tier": "에픽", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[아랫잠/에픽] 공/마 +21 또는 주스탯 8%+ (에디 에픽 2줄 정옵)": {"prob_pct": 0.9200, "tier": "에픽", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[아랫잠/유니크] 에디 주스탯 2줄 or 공/마 2줄 (유니크 국민옵)": {"prob_pct": 2.2200, "tier": "유니크", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[아랫잠/레전드리] 에디 주스탯 2줄+ (정옵 2줄)": {"prob_pct": 2.1500, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[아랫잠/레전드리] 에디 주스탯 2.5~3줄 (준종결/종결)": {"prob_pct": 0.7690, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자"]},
    "[아랫잠/무보엠] 에디 공/마 6% ~ 9% (에픽 1.5~2줄)": {"prob_pct": 4.8000, "tier": "에픽", "parts": ["무보엠"]},
    "[아랫잠/무보엠] 에디 공격력/마력 12%~15% (유니크/레전 1줄+)": {"prob_pct": 6.8000, "tier": "레전드리", "parts": ["무보엠"]},
    "[아랫잠/무보엠] 에디 공격력/마력 21% 이상 (2줄)": {"prob_pct": 1.8180, "tier": "레전드리", "parts": ["무보엠"]},
    "🔗 mesu.live 아랫잠 세부 확률(%) 직접 입력": {"prob_pct": None, "tier": "레전드리", "parts": ["장신구", "방어구", "장갑", "모자", "무보엠"]}
}

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

# [D] 2025.03 개편 이후 넥슨 공식 스타포스 이벤트 기준 (성수 하락 삭제 반영)
STARFORCE_EVENTS = {
    "📅 노이벤트 (평일 기준)": {"cost_mult": 1.00, "boom_mult": 1.00},
    "💰 스타포스 비용 30% 할인": {"cost_mult": 0.70, "boom_mult": 1.00},
    "🛡️ 21성 이하 파괴 확률 30% 감소": {"cost_mult": 1.00, "boom_mult": 0.70},
    "✨ 샤이닝 스타포스 (비용 30% 할인 + 21성 이하 파괴 30% 감소)": {"cost_mult": 0.70, "boom_mult": 0.70},
}

# 2025.03 개편 넥슨 공식 스타포스 확률 (s -> s+1: 성공확률, 파괴확률 / 하락 없음)
SF_OFFICIAL_PROB = {
    0: (0.95, 0.0), 1: (0.90, 0.0), 2: (0.85, 0.0), 3: (0.85, 0.0), 4: (0.80, 0.0),
    5: (0.75, 0.0), 6: (0.70, 0.0), 7: (0.65, 0.0), 8: (0.60, 0.0), 9: (0.55, 0.0),
    10: (0.50, 0.0), 11: (0.45, 0.0), 12: (0.40, 0.0), 13: (0.35, 0.0), 14: (0.30, 0.0),
    15: (0.30, 0.021), 16: (0.30, 0.021),
    17: (0.15, 0.068), 18: (0.15, 0.068), 19: (0.15, 0.085),
    20: (0.30, 0.105), 21: (0.15, 0.1275),
}

def get_sf_click_base_man(item_lv, star):
    L = float(item_lv)
    s = int(star)
    if s < 10:
        raw = 1000.0 + (L ** 3) * (s + 1) / 25.0
    else:
        div_map = {
            10: 400.0, 11: 220.0, 12: 150.0, 13: 110.0, 14: 75.0,
            15: 200.0, 16: 200.0, 17: 150.0, 18: 70.0, 19: 45.0,
            20: 200.0, 21: 125.0
        }
        div = div_map.get(s, 200.0)
        raw = 1000.0 + (L ** 3) * ((s + 1) ** 2.7) / div
    return round(raw, -2) / 10000.0

def calc_starforce_expected(item_lv, start_star, target_star, spare_cost_man, event_key, use_safeguard=False, use_starcatch=True):
    s_start = max(0, min(21, int(start_star)))
    s_target = max(1, min(22, int(target_star)))
    if s_start >= s_target:
        return {"meso_cost": 0.0, "spare_cost": 0.0, "total_cost": 0.0, "booms": 0.0}

    ev = STARFORCE_EVENTS.get(event_key, {"cost_mult": 1.0, "boom_mult": 1.0})
    c_mult = ev["cost_mult"]
    b_mult = ev["boom_mult"]

    # s -> s+1 단계별 기대 메소비(F_meso) 및 기대 파괴수(F_boom) 마르코프 체인 정밀 계산 (파괴 시 12성 복구)
    F_meso = [0.0] * 22
    F_boom = [0.0] * 22

    for s in range(s_target):
        p_base, b_base = SF_OFFICIAL_PROB[s]
        base_man = get_sf_click_base_man(item_lv, s)

        # 파괴방지 (15~17성: 기본비용 +200% 추가, 파괴확률 0)
        sg_active = use_safeguard and (15 <= s <= 17)
        b_cur = 0.0 if sg_active else (b_base * (b_mult if s <= 21 else 1.0))
        click_man = (base_man * c_mult) + (base_man * 2.0 if sg_active else 0.0)

        # 스타캐치 (성공확률 1.05배, 실패/파괴 비율 비례 축소)
        if use_starcatch and p_base < 1.0:
            p_cur = min(1.0, p_base * 1.05)
            rem_scale = (1.0 - p_cur) / max(1e-9, 1.0 - p_base)
            b_cur = b_cur * rem_scale
        else:
            p_cur = p_base

        if b_cur <= 0.0 or s < 15:
            F_meso[s] = click_man / p_cur
            F_boom[s] = 0.0
        else:
            climb_meso = sum(F_meso[12:s])
            climb_boom = sum(F_boom[12:s])
            F_meso[s] = (click_man + b_cur * climb_meso) / p_cur
            F_boom[s] = (b_cur * (1.0 + climb_boom)) / p_cur

    meso_tot = sum(F_meso[s_start:s_target])
    booms_tot = sum(F_boom[s_start:s_target])
    spare_tot = booms_tot * float(spare_cost_man)
    return {
        "meso_cost": round(meso_tot, 1),
        "spare_cost": round(spare_tot, 1),
        "total_cost": round(meso_tot + spare_tot, 1),
        "booms": round(booms_tot, 3)
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

def calc_scroll_expected_cost(scroll_mode, slots, trace_per_try, trace_price_each, inno_cost, css_cost, is_fever=True):
    trace_try_cost_man = (trace_per_try * trace_price_each) / 10000.0
    if "100%" in scroll_mode:
        p = 1.0
    elif "70%" in scroll_mode:
        p = 0.99 if is_fever else 0.84
    elif "30%" in scroll_mode:
        p = 0.59 if is_fever else 0.44
    else:
        p = 0.39 if is_fever else 0.29

    if p >= 0.99:
        return round(slots * trace_try_cost_man + 150.0, 1), f"확률 {int(p*100)}% 스트레이트 완작"

    target_first4 = 2 if p < 0.45 else 3
    prob_pass_first4 = 0.0
    for k in range(target_first4, 5):
        prob_pass_first4 += math.comb(4, k) * (p ** k) * ((1.0 - p) ** (4 - k))
    prob_pass_first4 = max(0.05, prob_pass_first4)

    expected_inno_cycles = (1.0 / prob_pass_first4) - 1.0
    inno_stage_cost = expected_inno_cycles * (4 * trace_try_cost_man + inno_cost) + (4 * trace_try_cost_man)

    rem_slots = max(0, slots - target_first4)
    rem_tries = rem_slots / p
    rem_fails = rem_slots * ((1.0 - p) / p)
    finish_stage_cost = (rem_tries * trace_try_cost_man) + (rem_fails * css_cost) + 200.0

    total_scroll_man = round(inno_stage_cost + finish_stage_cost, 1)
    desc = f"실질확률 {int(p*100)}% | 평균 이노센트 {expected_inno_cycles:.1f}회 + 순백복구 {rem_fails:.1f}회"
    return total_scroll_man, desc

def create_initial_maple(now_str, today_str):
    return {
        "last_weekly_reset": now_str,
        "last_daily_date": today_str,
        "fee_rate": 0.03,
        "jokbo_shift_pct": 0.0,
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

    loa_hourly_krw = (loa_hr_g / 10000.0) * loa_rate
    gs_c2_cfg = gs_data["client2_farm"]
    gs_hourly_man = (float(gs_c2_cfg["drop_item_price"]) * float(gs_c2_cfg["drops_per_hour"])) + float(gs_c2_cfg["extra_hourly_man"])
    gs_hourly_krw = (gs_hourly_man / 10000.0) * gs_rate

    mp_hc = mp_data["hunting_cfg"]
    mp_fee_m = 1.0 - float(mp_data.get("fee_rate", 0.03))
    mp_hunt_hr_man = float(mp_hc["pure_meso_hr"]) + (float(mp_hc["frag_price"]) * float(mp_hc["frags_per_hr"]) * mp_fee_m) + (float(mp_hc["extra_drops_hr"]) * mp_fee_m) - float(mp_hc["consumable_hr"])
    mp_hourly_krw = (mp_hunt_hr_man / 10000.0) * mp_rate

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
    "🍁 메이플스토리 (3명의+2026공식견적기+메소마켓)"
])
# [파트 1 끝]
# [파트 2 시작]
# ==============================================================================
# 탭 1: ⚓ 로스트아크 화면 (7~11레벨 보석 개수 관리 + 25서버 총합계 바 포함)
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

    col_v1, col_v2, col_v3, col_v4, col_v5 = st.columns([1.1, 1.1, 1.1, 1.2, 2.0])
    with col_v1:
        show_lv = st.checkbox("📊 캐릭터별 템렙", value=True)
    with col_v2:
        show_cd = st.checkbox("🌀 카던 휴게", value=True)
    with col_v3:
        show_raid = st.checkbox("⚔️ 레이드/계승", value=True)
    with col_v4:
        show_gem = st.checkbox("💎 7~11렙 보석", value=True)
    with col_v5:
        group_by_char = st.checkbox("👥 캐릭터별로 묶어서 배열 (1렙-1카-1캐)", value=True)

    GEM_COLS = ["보석7", "보석8", "보석9", "보석10", "보석11"]

    # 전체 25서버 7~11레벨 보석 합계 요약 바
    if show_gem:
        gem_totals = {lv: sum(int(r.get(f"보석{lv}", 0) or 0) for r in loa_data["rows"]) for lv in range(7, 12)}
        gem_summary = "  |  ".join([f"**{lv}렙:** `{gem_totals[lv]:,}개`" for lv in range(7, 12)])
        st.info(f"💎 **전체 25서버 보유 보석 합계** 👉  {gem_summary}")

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
    display_cols.append("카던큐브")
    if show_gem:
        display_cols.extend(GEM_COLS)
    display_cols.append("보석메모")

    df = pd.DataFrame(loa_data["rows"])
    for col in display_cols:
        if col not in df.columns:
            if col in ["생활완료", "보석배", "낙원", "이벤", "싱글"]:
                df[col] = False
            elif col in GEM_COLS:
                df[col] = 0
            else:
                df[col] = ""

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
        "보석7": st.column_config.NumberColumn("💎7렙", min_value=0, step=1, format="%d개", width="small"),
        "보석8": st.column_config.NumberColumn("💎8렙", min_value=0, step=1, format="%d개", width="small"),
        "보석9": st.column_config.NumberColumn("💎9렙", min_value=0, step=1, format="%d개", width="small"),
        "보석10": st.column_config.NumberColumn("💎10렙", min_value=0, step=1, format="%d개", width="small"),
        "보석11": st.column_config.NumberColumn("💎11렙", min_value=0, step=1, format="%d개", width="small"),
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

        for gcol in GEM_COLS:
            if gcol in edit_row:
                gval = 0 if pd.isna(edit_row[gcol]) else max(0, int(edit_row[gcol]))
                if int(orig.get(gcol, 0) or 0) != gval:
                    orig[gcol] = gval
                    changed = True
                    need_table_refresh = True

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

            # ✨ 업그레이드: 2클라 목표템 자유 추가/수정/삭제 & 즉시 재계산
            t_head1, t_head2 = st.columns([2.2, 1.0])
            with t_head1:
                st.markdown("##### 🎯 2. 다음 단계 목표 템 목록 (자유 추가·수정·삭제)")
            with t_head2:
                if st.button("🗑️ 목표 목록 전체 비우기", use_container_width=True, key="gs_clear_targets"):
                    c2["targets"] = []
                    save_json_local(GERSANG_FILE, gs_data)
                    st.session_state.gs_dirty = True
                    st.session_state.gs_editor_ver += 1
                    st.rerun()

            target_df = pd.DataFrame(c2["targets"])
            if target_df.empty:
                target_df = pd.DataFrame(columns=["포함", "아이템명", "목표가", "구매완료", "메모", "삭제"])
            else:
                target_df["삭제"] = False

            edited_targets = st.data_editor(
                target_df[["포함", "아이템명", "목표가", "구매완료", "메모", "삭제"]],
                column_config={
                    "포함": st.column_config.CheckboxColumn("🎯포함", width="small", default=True),
                    "아이템명": st.column_config.TextColumn("✏️구할 아이템 (아래 빈칸 클릭해 추가)", width="medium"),
                    "목표가": st.column_config.NumberColumn("✏️예상가(만 전)", width="small", min_value=0.0, step=100.0, format="%d만", default=10000.0),
                    "구매완료": st.column_config.CheckboxColumn("✅완료", width="small", default=False),
                    "메모": st.column_config.TextColumn("✏️메모", width="small", default=""),
                    "삭제": st.column_config.CheckboxColumn("🗑️삭제", width="small", default=False),
                },
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key=f"gs_target_editor_{st.session_state.gs_editor_ver}"
            )

            new_targets = []
            deleted_any = False
            for idx, r in edited_targets.iterrows():
                if not pd.isna(r.get("삭제")) and bool(r["삭제"]):
                    deleted_any = True
                    continue
                if pd.isna(r["아이템명"]) or str(r["아이템명"]).strip() == "":
                    continue
                new_targets.append({
                    "id": len(new_targets) + 1,
                    "포함": True if pd.isna(r["포함"]) else bool(r["포함"]),
                    "아이템명": str(r["아이템명"]).strip(),
                    "목표가": 0.0 if pd.isna(r["목표가"]) else float(r["목표가"]),
                    "구매완료": False if pd.isna(r["구매완료"]) else bool(r["구매완료"]),
                    "메모": "" if pd.isna(r["메모"]) else str(r["메모"])
                })

            if new_targets != c2["targets"] or deleted_any:
                c2["targets"] = new_targets
                save_json_local(GERSANG_FILE, gs_data)
                st.session_state.gs_dirty = True
                if deleted_any:
                    st.session_state.gs_editor_ver += 1
                st.rerun()

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
# [파트 2 끝]
# [파트 3 시작]
# ==============================================================================
# 탭 3: 🍁 메이플스토리 화면 (2026 넥슨 공식 엔진 + 단품/반제품 초고속 견적기)
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
        "🛠️ 2. 2026 공식 견적기 (단품/반제품/풀세팅)",
        "💱 3. 메소마켓 (시세 일지 & % 보정 & AI 추천)",
        "📖 4. 메이플 장사 가계부 & 시세 족보",
        "📘 5. 직작 & 장사 백과사전 (추옵/옵션/작 자동판독기)"
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
    # 🛠️ [서브탭 2] 2026 넥슨 공식 단품·반제품·올인원 종합 견적 & 매물 판독기
    # --------------------------------------------------------------------------
    with mp_sub2:
        st.markdown("#### 🛠️ 2026 넥슨 공식 단품·반제품·풀세팅 견적기 (`잠재 4구간 · 에디 공식확률 · 2025개편 스타포스 수식`)")
        st.caption(
            "**위 `[⚡ 단품 초고속 조회]` 버튼을 누르면 필요한 파트 1개만 켜져서 반제품(예: 레전 윗잠만 붙은 매물) 시세를 3초 만에 감정할 수 있습니다!** "
            "원하는 체크박스를 추가로 켜서 `윗잠 + 스타포스` 같은 조합 견적도 자유롭게 확인하세요."
        )

        AUTO_TRACE_SPEC = {
            "1~159제 (미카엘라/이벤링/보장/루타비스)": {"장신구 (5~6작)": (6, 400), "방어구 (8~12작)": (8, 550), "무기 (9~10작)": (10, 900)},
            "160~199제 (여명/앱솔랩스)": {"장신구 (6~7작)": (6, 550), "방어구 (8~12작)": (9, 750), "무기 (9~10작)": (10, 1200)},
            "200~249제 (아케인셰이드/칠흑/제네시스)": {"장신구 (6~7작)": (7, 800), "방어구 (8~12작)": (9, 1150), "무기 (9~10작)": (10, 1800)},
            "250~300제 (에테르넬/광휘)": {"장신구 (6~7작)": (7, 1100), "방어구 (8~12작)": (9, 1500), "무기 (9~10작)": (10, 2400)},
        }

        lv_list = list(MAPLE_CUBE_COST_TABLE["윗잠 (잠재능력)"].keys())

        preset_keys = {
            "est_name": "데이브레이크 펜던트 / 반제품·완제품 감정",
            "est_lv": lv_list[1],
            "est_exact_lv": 160,
            "est_part": MAPLE_EQUIP_PARTS[0],
            "est_base": 5000.0,
            "est_include_base": True,
            "est_auc": 250000.0,
            "est_val_shift": 0.0,
            "est_use_scis": False,
            "est_use_flm": False,
            "est_fl_cat": "보스 장신구/방어구 (추옵 보정 O)",
            "est_use_scr": False,
            "est_use_sf": False,
            "est_sf_start": 0,
            "est_sf_target": 18,
            "est_sf_ev": "✨ 샤이닝 스타포스 (비용 30% 할인 + 21성 이하 파괴 30% 감소)",
            "est_sf_sg": False,
            "est_sf_sc": True,
            "est_use_main": True,
            "est_use_adi": False,
            "est_main_start": "에픽",
            "est_main_opt": "[레전드리] 주스탯 27% 이상 (준3줄 국민옵)",
            "est_adi_start": "레어",
            "est_adi_opt": "[아랫잠/에픽] 공/마 +10 또는 주스탯 4%+ (에디 에픽 1.5~2줄)"
        }
        for pk, pv in preset_keys.items():
            if pk not in st.session_state:
                st.session_state[pk] = pv

        # 구버전 세션값 자동 보정
        if st.session_state.est_lv not in lv_list:
            st.session_state.est_lv = lv_list[1]
            st.session_state.est_exact_lv = BRACKET_DEFAULT_LV[lv_list[1]]
        if st.session_state.est_part not in MAPLE_EQUIP_PARTS:
            st.session_state.est_part = MAPLE_EQUIP_PARTS[0]
        if st.session_state.est_sf_ev not in STARFORCE_EVENTS:
            st.session_state.est_sf_ev = list(STARFORCE_EVENTS.keys())[3]

        # [상단 바 1] 단품/반제품 초고속 모드 전환 버튼
        with st.container(border=True):
            st.markdown("##### ⚡ 단품·반제품 초고속 조회 (원하는 파트 1개만 즉시 켜기 — 이후 체크박스로 자유 조합 가능)")
            qm1, qm2, qm3, qm4, qm5, qm6 = st.columns(6)
            with qm1:
                if st.button("🎲 윗잠만 단독 조회", use_container_width=True, type="primary" if (st.session_state.est_use_main and not any([st.session_state.est_use_flm, st.session_state.est_use_scr, st.session_state.est_use_sf, st.session_state.est_use_adi])) else "secondary"):
                    st.session_state.est_use_flm = False; st.session_state.est_use_scr = False; st.session_state.est_use_sf = False
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = False; st.session_state.est_include_base = True
                    st.rerun()
            with qm2:
                if st.button("✨ 아랫잠만 단독 조회", use_container_width=True, type="primary" if (st.session_state.est_use_adi and not any([st.session_state.est_use_flm, st.session_state.est_use_scr, st.session_state.est_use_sf, st.session_state.est_use_main])) else "secondary"):
                    st.session_state.est_use_flm = False; st.session_state.est_use_scr = False; st.session_state.est_use_sf = False
                    st.session_state.est_use_main = False; st.session_state.est_use_adi = True; st.session_state.est_include_base = True
                    st.rerun()
            with qm3:
                if st.button("⭐ 스타포스만 단독 조회", use_container_width=True, type="primary" if (st.session_state.est_use_sf and not any([st.session_state.est_use_flm, st.session_state.est_use_scr, st.session_state.est_use_main, st.session_state.est_use_adi])) else "secondary"):
                    st.session_state.est_use_flm = False; st.session_state.est_use_scr = False; st.session_state.est_use_sf = True
                    st.session_state.est_use_main = False; st.session_state.est_use_adi = False; st.session_state.est_include_base = False
                    st.rerun()
            with qm4:
                if st.button("🔥 추옵만 단독 조회", use_container_width=True, type="primary" if (st.session_state.est_use_flm and not any([st.session_state.est_use_scr, st.session_state.est_use_sf, st.session_state.est_use_main, st.session_state.est_use_adi])) else "secondary"):
                    st.session_state.est_use_flm = True; st.session_state.est_use_scr = False; st.session_state.est_use_sf = False
                    st.session_state.est_use_main = False; st.session_state.est_use_adi = False; st.session_state.est_include_base = False
                    st.rerun()
            with qm5:
                if st.button("📜 작만 단독 조회", use_container_width=True, type="primary" if (st.session_state.est_use_scr and not any([st.session_state.est_use_flm, st.session_state.est_use_sf, st.session_state.est_use_main, st.session_state.est_use_adi])) else "secondary"):
                    st.session_state.est_use_flm = False; st.session_state.est_use_scr = True; st.session_state.est_use_sf = False
                    st.session_state.est_use_main = False; st.session_state.est_use_adi = False; st.session_state.est_include_base = False
                    st.rerun()
            with qm6:
                if st.button("🛠️ 5개 전체 풀세팅", use_container_width=True, type="primary" if all([st.session_state.est_use_flm, st.session_state.est_use_scr, st.session_state.est_use_sf, st.session_state.est_use_main, st.session_state.est_use_adi]) else "secondary"):
                    st.session_state.est_use_flm = True; st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                    st.session_state.est_use_main = True; st.session_state.est_use_adi = True; st.session_state.est_include_base = True
                    st.rerun()

            with st.expander("🎯 국민 완제품 원클릭 프리셋 펼치기 (미카엘라 드메 / 18성·22성 / 제네시스 해방무기)", expanded=False):
                pr1, pr2, pr3, pr4, pr5, pr6 = st.columns(6)
                with pr1:
                    if st.button("👓 90제 미카엘라 드메2줄", use_container_width=True):
                        st.session_state.est_name = "미카엘라의 새 안경 (90제 드메2줄)"
                        st.session_state.est_lv = lv_list[0]; st.session_state.est_exact_lv = 90; st.session_state.est_part = MAPLE_EQUIP_PARTS[0]
                        st.session_state.est_base = 1500.0; st.session_state.est_include_base = True; st.session_state.est_auc = 320000.0; st.session_state.est_val_shift = 0.0
                        st.session_state.est_use_flm = False; st.session_state.est_use_scr = False; st.session_state.est_use_sf = False
                        st.session_state.est_use_main = True; st.session_state.est_use_adi = False
                        st.session_state.est_main_start = "에픽"
                        st.session_state.est_main_opt = "[레전드리/장신구] 드랍+메획 총합 2줄 이상 (드메 2줄 핵심!)"
                        st.rerun()
                with pr2:
                    if st.button("💍 17성 유니크 가성비", use_container_width=True):
                        st.session_state.est_name = "17성 유니크 가성비 방어구/장신구"
                        st.session_state.est_lv = lv_list[1]; st.session_state.est_exact_lv = 160; st.session_state.est_part = MAPLE_EQUIP_PARTS[0]
                        st.session_state.est_base = 3000.0; st.session_state.est_include_base = True; st.session_state.est_auc = 95000.0; st.session_state.est_val_shift = 0.0
                        st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 장신구/방어구 (추옵 보정 O)"
                        st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                        st.session_state.est_sf_start = 0; st.session_state.est_sf_target = 17
                        st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                        st.session_state.est_main_start = "에픽"; st.session_state.est_main_opt = "[유니크] 주스탯 15% ~ 18% (유니크 2줄)"
                        st.session_state.est_adi_start = "레어"; st.session_state.est_adi_opt = "[아랫잠/에픽] 공/마 +10 또는 주스탯 4%+ (에디 에픽 1.5~2줄)"
                        st.rerun()
                with pr3:
                    if st.button("🔥 18성 레전27% 국민템", use_container_width=True):
                        st.session_state.est_name = "18성 레전 27% 국민 본캐 템"
                        st.session_state.est_lv = lv_list[1]; st.session_state.est_exact_lv = 160; st.session_state.est_part = MAPLE_EQUIP_PARTS[0]
                        st.session_state.est_base = 5000.0; st.session_state.est_include_base = True; st.session_state.est_auc = 480000.0; st.session_state.est_val_shift = 0.0
                        st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 장신구/방어구 (추옵 보정 O)"
                        st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                        st.session_state.est_sf_start = 0; st.session_state.est_sf_target = 18
                        st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                        st.session_state.est_main_start = "에픽"; st.session_state.est_main_opt = "[레전드리] 주스탯 27% 이상 (준3줄 국민옵)"
                        st.session_state.est_adi_start = "레어"; st.session_state.est_adi_opt = "[아랫잠/유니크] 에디 주스탯 2줄 or 공/마 2줄 (유니크 국민옵)"
                        st.rerun()
                with pr4:
                    if st.button("👑 22성 레전30% 종결템", use_container_width=True):
                        st.session_state.est_name = "22성 아케인/칠흑 종결 세팅"
                        st.session_state.est_lv = lv_list[2]; st.session_state.est_exact_lv = 200; st.session_state.est_part = MAPLE_EQUIP_PARTS[1]
                        st.session_state.est_base = 35000.0; st.session_state.est_include_base = True; st.session_state.est_auc = 2800000.0; st.session_state.est_val_shift = 0.0
                        st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 장신구/방어구 (추옵 보정 O)"
                        st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                        st.session_state.est_sf_start = 0; st.session_state.est_sf_target = 22
                        st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                        st.session_state.est_main_start = "에픽"; st.session_state.est_main_opt = "[레전드리] 주스탯 30% 이상 (3줄 정옵)"
                        st.session_state.est_adi_start = "레어"; st.session_state.est_adi_opt = "[아랫잠/레전드리] 에디 주스탯 2.5~3줄 (준종결/종결)"
                        st.rerun()
                with pr5:
                    if st.button("⚔️ 제네시스 해방무기 직작", use_container_width=True):
                        st.session_state.est_name = "제네시스 해방 무기 (22성·15%완작 기본 지급)"
                        st.session_state.est_lv = lv_list[2]; st.session_state.est_exact_lv = 200; st.session_state.est_part = MAPLE_EQUIP_PARTS[4]
                        st.session_state.est_base = 0.0; st.session_state.est_include_base = False; st.session_state.est_auc = 0.0; st.session_state.est_val_shift = 0.0
                        st.session_state.est_use_scis = False
                        st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 무기 (아케인/해방무기 등)"
                        st.session_state.est_use_scr = False; st.session_state.est_use_sf = False
                        st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                        st.session_state.est_main_start = "유니크"; st.session_state.est_main_opt = "[레전드리/무보엠] 보공/공마 유효 3줄 (방무 제외)"
                        st.session_state.est_adi_start = "에픽"; st.session_state.est_adi_opt = "[아랫잠/무보엠] 에디 공격력/마력 21% 이상 (2줄)"
                        st.rerun()
                with pr6:
                    if st.button("🗡️ 해방전 18성 아케인무기", use_container_width=True):
                        st.session_state.est_name = "해방 전 18성 아케인셰이드 무기 (중고 감가 -35%)"
                        st.session_state.est_lv = lv_list[2]; st.session_state.est_exact_lv = 200; st.session_state.est_part = MAPLE_EQUIP_PARTS[4]
                        st.session_state.est_base = 10000.0; st.session_state.est_include_base = True; st.session_state.est_auc = 350000.0; st.session_state.est_val_shift = -35.0
                        st.session_state.est_use_flm = True; st.session_state.est_fl_cat = "보스 무기 (아케인/해방무기 등)"
                        st.session_state.est_use_scr = True; st.session_state.est_use_sf = True
                        st.session_state.est_sf_start = 0; st.session_state.est_sf_target = 18
                        st.session_state.est_use_main = True; st.session_state.est_use_adi = True
                        st.session_state.est_main_start = "에픽"; st.session_state.est_main_opt = "[레전드리/무보엠] 보공/방무/공마 유효 2줄"
                        st.session_state.est_adi_start = "레어"; st.session_state.est_adi_opt = "[아랫잠/무보엠] 에디 공격력/마력 12%~15% (유니크/레전 1줄+)"
                        st.rerun()

        e_col1, e_col2 = st.columns([1.2, 1.2], gap="large")

        with e_col1:
            with st.container(border=True):
                st.markdown("##### 🛒 [기본 설정] 장비 레벨 · 부위 필터 · 노작(스페어)가 · 비교할 매물가")
                eval_item_name = st.text_input("아이템 이름", value=st.session_state.est_name)
                st.session_state.est_name = eval_item_name

                lv_c1, lv_c2 = st.columns([1.3, 1.1])
                with lv_c1:
                    lv_idx = lv_list.index(st.session_state.est_lv)
                    lv_bracket = st.selectbox("1. 잠재 레벨 구간 (2026 공식 4구간)", lv_list, index=lv_idx)
                    if lv_bracket != st.session_state.est_lv:
                        st.session_state.est_lv = lv_bracket
                        st.session_state.est_exact_lv = BRACKET_DEFAULT_LV[lv_bracket]
                with lv_c2:
                    part_idx = MAPLE_EQUIP_PARTS.index(st.session_state.est_part)
                    equip_part = st.selectbox("2. 장비 부위 (해당 부위 옵션만 표시!)", MAPLE_EQUIP_PARTS, index=part_idx)
                    st.session_state.est_part = equip_part
                part_short = equip_part.split(" ")[0]

                b_c1, b_c2 = st.columns(2)
                with b_c1:
                    base_item_price = st.number_input("🛒 노작(스페어) 1개 시세 (만 메소)", min_value=0.0, value=float(st.session_state.est_base), step=1000.0, format="%.0f")
                    st.session_state.est_base = base_item_price
                    include_base = st.checkbox(
                        f"초기 노작 1개값({fmt_man(base_item_price, '메소')})을 총원가에 합산",
                        value=bool(st.session_state.est_include_base),
                        help="반제품 매물(노작+윗잠)을 감정할 땐 켜두고, 이미 가진 템에 스타포스/추옵만 추가로 돌릴 땐 끄세요. (꺼도 스타포스 파괴 시 스페어 비용엔 자동 반영됩니다!)"
                    )
                    st.session_state.est_include_base = include_base
                with b_c2:
                    auction_finished_price = st.number_input("🏷️ 비교할 경매장 매물 가격 (만 메소, 0=순수견적)", min_value=0.0, value=float(st.session_state.est_auc), step=10000.0, format="%.0f")
                    st.session_state.est_auc = auction_finished_price
                    st.caption(f"비교 매물가: **{fmt_man(auction_finished_price, '메소')}**")

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
                        "🎚️ 시장 시세 보정 / 중고 감가율 (%)",
                        min_value=-70.0, max_value=100.0, value=float(st.session_state.est_val_shift), step=5.0, format="%.1f",
                        help="완제품/반제품의 경매장 중고 감가를 반영하려면 -15% ~ -35% 등을 입력하세요."
                    )
                    st.session_state.est_val_shift = market_valuation_shift

            # [파트 1] 윗잠(잠재능력) - 가장 많이 조회하므로 최상단 배치!
            with st.container(border=True):
                use_main_pot = st.checkbox("🎲 [파트 1] 윗잠(잠재능력) 견적 포함하기 (2026 넥슨 공식 비용·확률)", value=st.session_state.est_use_main)
                st.session_state.est_use_main = use_main_pot
                main_norm_cost, main_mira_cost = 0.0, 0.0
                main_p50_mira, main_p85_mira, main_p95_mira = 0.0, 0.0, 0.0
                main_desc = "미포함"
                if use_main_pot:
                    filtered_m_opts = [k for k, v in MAPLE_MAIN_POT_OPTIONS.items() if part_short in v["parts"]]
                    m_idx = filtered_m_opts.index(st.session_state.est_main_opt) if st.session_state.est_main_opt in filtered_m_opts else 0
                    mc_top1, mc_top2 = st.columns([1.8, 1.0])
                    with mc_top1:
                        main_opt_sel = st.selectbox(f"윗잠 목표 옵션 ({part_short} 전용 필터 적용됨)", filtered_m_opts, index=m_idx)
                        st.session_state.est_main_opt = main_opt_sel
                    m_info = MAPLE_MAIN_POT_OPTIONS[main_opt_sel]
                    with mc_top2:
                        m_st_idx = TIER_ORDER.index(st.session_state.est_main_start) if st.session_state.est_main_start in TIER_ORDER else 1
                        m_start_t = st.selectbox("윗잠 시작 등급", TIER_ORDER, index=m_st_idx)
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
                    main_desc = f"{m_start_t}➔{m_targ_t} | {main_opt_sel[:16]} ({m_prob:.3f}% / 평균 {m_opt_st['mean_tries']:.1f}회)"
                    st.info(
                        f"✅ **윗잠 공식 견적:** `{m_start_t} ➔ {m_targ_t}` | 1회 **`{fmt_man(m_unit_c, '메소')}`** | 확률 **`{m_prob:.4f}%`** (평균 **`{m_opt_st['mean_tries']:.1f}회`**)\n"
                        f"👉 평일 기대값: **{fmt_man(main_norm_cost, '메소')}** / ✨ **미라클 데이: `{fmt_man(main_mira_cost, '메소')}`**"
                    )

            # [파트 2] 아랫잠(에디셔널) - 2026 공식 비용/확률/천장 반영
            with st.container(border=True):
                use_adi_pot = st.checkbox("✨ [파트 2] 아랫잠(에디셔널) 견적 포함하기 (2026 넥슨 공식 비용·확률·천장)", value=st.session_state.est_use_adi)
                st.session_state.est_use_adi = use_adi_pot
                adi_norm_cost, adi_mira_cost = 0.0, 0.0
                adi_p50_mira, adi_p85_mira, adi_p95_mira = 0.0, 0.0, 0.0
                adi_desc = "미포함"
                if use_adi_pot:
                    filtered_a_opts = [k for k, v in MAPLE_ADI_POT_OPTIONS.items() if part_short in v["parts"]]
                    a_idx = filtered_a_opts.index(st.session_state.est_adi_opt) if st.session_state.est_adi_opt in filtered_a_opts else 0
                    ac_top1, ac_top2 = st.columns([1.8, 1.0])
                    with ac_top1:
                        adi_opt_sel = st.selectbox(f"아랫잠 목표 옵션 ({part_short} 전용 필터 적용됨)", filtered_a_opts, index=a_idx)
                        st.session_state.est_adi_opt = adi_opt_sel
                    a_info = MAPLE_ADI_POT_OPTIONS[adi_opt_sel]
                    with ac_top2:
                        a_st_idx = TIER_ORDER.index(st.session_state.est_adi_start) if st.session_state.est_adi_start in TIER_ORDER else 0
                        a_start_t = st.selectbox("아랫잠 시작 등급", TIER_ORDER, index=a_st_idx)
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
                    adi_desc = f"{a_start_t}➔{a_targ_t} | {adi_opt_sel[:16]} ({a_prob:.3f}% / 평균 {a_opt_st['mean_tries']:.1f}회)"
                    st.info(
                        f"✅ **아랫잠 공식 견적:** `{a_start_t} ➔ {a_targ_t}` | 1회 **`{fmt_man(a_unit_c, '메소')}`** | 확률 **`{a_prob:.4f}%`** (평균 **`{a_opt_st['mean_tries']:.1f}회`**)\n"
                        f"👉 평일 기대값: **{fmt_man(adi_norm_cost, '메소')}** / ✨ **미라클 데이: `{fmt_man(adi_mira_cost, '메소')}`**"
                    )

            # [파트 3] 스타포스 - 2025 개편 넥슨 공식 수식 + 시작→목표 구간 계산
            with st.container(border=True):
                use_sf = st.checkbox("⭐ [파트 3] 스타포스 견적 포함하기 (2025 개편 넥슨 공식 수식 · 시작➔목표 구간 계산)", value=st.session_state.est_use_sf)
                st.session_state.est_use_sf = use_sf
                sf_norm_cost = 0.0
                sf_event_cost = 0.0
                sf_desc = "미포함"
                if use_sf:
                    sf_r1, sf_r2, sf_r3 = st.columns(3)
                    with sf_r1:
                        exact_lv = st.number_input("장비 착용 레벨 (예: 140/150/160/200/250)", min_value=70, max_value=300, value=int(st.session_state.est_exact_lv), step=10, key=f"sf_lv_{lv_bracket}")
                        st.session_state.est_exact_lv = exact_lv
                    with sf_r2:
                        sf_start = st.number_input("현재(시작) 성수", min_value=0, max_value=21, value=int(st.session_state.est_sf_start), step=1)
                        st.session_state.est_sf_start = sf_start
                    with sf_r3:
                        sf_t_default = max(sf_start + 1, min(22, int(st.session_state.est_sf_target)))
                        sf_target = st.number_input("목표 성수", min_value=sf_start + 1, max_value=22, value=sf_t_default, step=1)
                        st.session_state.est_sf_target = sf_target

                    sf_ev_list = list(STARFORCE_EVENTS.keys())
                    sf_ev_idx = sf_ev_list.index(st.session_state.est_sf_ev) if st.session_state.est_sf_ev in sf_ev_list else 3
                    sf_ev_name = st.selectbox("스타포스 이벤트 선택", sf_ev_list, index=sf_ev_idx)
                    st.session_state.est_sf_ev = sf_ev_name

                    sf_o1, sf_o2 = st.columns(2)
                    with sf_o1:
                        sf_sg = st.checkbox("🛡️ 15~17성 파괴방지 적용 (+200% 비용)", value=bool(st.session_state.est_sf_sg))
                        st.session_state.est_sf_sg = sf_sg
                    with sf_o2:
                        sf_sc = st.checkbox("🎯 스타캐치 성공 적용 (성공률 ×1.05)", value=bool(st.session_state.est_sf_sc))
                        st.session_state.est_sf_sc = sf_sc

                    sf_norm_res = calc_starforce_expected(exact_lv, sf_start, sf_target, base_item_price, "📅 노이벤트 (평일 기준)", sf_sg, sf_sc)
                    sf_ev_res = calc_starforce_expected(exact_lv, sf_start, sf_target, base_item_price, sf_ev_name, sf_sg, sf_sc)

                    sf_norm_cost = sf_norm_res["total_cost"]
                    sf_event_cost = sf_ev_res["total_cost"]
                    sf_desc = f"{exact_lv}제 {sf_start}➔{sf_target}성 (강화비 {fmt_man(sf_ev_res['meso_cost'], '메소')} + 파괴 {sf_ev_res['booms']:.2f}회)"
                    st.info(
                        f"⭐ **{exact_lv}제 `{sf_start}성 ➔ {sf_target}성` 넥슨 공식 기댓값 ({'파방O' if sf_sg else '파방X'} / {'스타캐치O' if sf_sc else 'X'}):**\n"
                        f"- 평일 총합: **{fmt_man(sf_norm_cost, '메소')}** (메소 {fmt_man(sf_norm_res['meso_cost'], '메소')} + 평균 파괴 `{sf_norm_res['booms']:.2f}회`)\n"
                        f"- ✨ **선택 이벤트 총합: `{fmt_man(sf_event_cost, '메소')}`** (메소 `{fmt_man(sf_ev_res['meso_cost'], '메소')}` + 파괴 스페어 `{fmt_man(sf_ev_res['spare_cost'], '메소')}` / 평균 `{sf_ev_res['booms']:.2f}회`)"
                    )

            # [파트 4] 추가옵션 (환생의 불꽃)
            with st.container(border=True):
                use_flame = st.checkbox("🔥 [파트 4] 추가옵션(환생의 불꽃) 견적 포함하기", value=st.session_state.est_use_flm)
                st.session_state.est_use_flm = use_flame
                flame_norm_cost = 0.0
                flame_desc = "미포함"
                if use_flame:
                    fl_cats = list(MAPLE_FLAME_PRESETS.keys())
                    if part_short == "무보엠":
                        default_fl_cat_idx = 2
                    elif st.session_state.est_fl_cat in fl_cats:
                        default_fl_cat_idx = fl_cats.index(st.session_state.est_fl_cat)
                    else:
                        default_fl_cat_idx = 0
                    fl_c1, fl_c2 = st.columns(2)
                    with fl_c1:
                        fl_cat = st.selectbox("장비 추옵 분류", fl_cats, index=default_fl_cat_idx)
                        st.session_state.est_fl_cat = fl_cat
                        fl_target = st.selectbox("목표 추옵 급수/옵션", list(MAPLE_FLAME_PRESETS[fl_cat].keys()), index=min(2, len(MAPLE_FLAME_PRESETS[fl_cat])-1))
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
                    flame_desc = f"{fl_target[:14]} (평균 {fl_tries:.1f}개 × {int(fl_unit_price)}만)"
                    st.caption(f"👉 **추옵 기대 원가: `{fmt_man(flame_norm_cost, '메소')}`** ({flame_desc})")

            # [파트 5] 주문서 작
            with st.container(border=True):
                use_scroll = st.checkbox("📜 [파트 5] 주문서 작(주흔 15%/30%/70%/100% · 악공 · 놀긍) 견적 포함하기", value=st.session_state.est_use_scr)
                st.session_state.est_use_scr = use_scroll
                scroll_norm_cost = 0.0
                scroll_event_cost = 0.0
                scroll_desc = "미포함"
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
                        part_keys = list(AUTO_TRACE_SPEC[lv_bracket].keys())
                        def_p_idx = 2 if part_short == "무보엠" else (0 if part_short == "장신구" else 1)
                        part_type = st.selectbox("장비 부위 (주흔 자동 세팅)", part_keys, index=def_p_idx)

                    if "직접 입력" in sc_mode:
                        scroll_norm_cost = st.number_input("직접 입력: 총 작 완성 예상 비용 (만 메소)", min_value=0.0, value=15000.0, step=1000.0, format="%.0f")
                        scroll_event_cost = scroll_norm_cost
                        scroll_desc = "사용자 직접 입력 작 비용"
                    else:
                        auto_slots, auto_trace_per = AUTO_TRACE_SPEC[lv_bracket][part_type]
                        trace_price = 2500.0
                        css_cost = 450.0
                        if st.checkbox("⚙️ 주흔 시세 / 슬롯 수 세부 조정하기", value=False):
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
                            f"👉 **자동 세팅({auto_slots}작 / 1회당 주흔 {auto_trace_per:,}개)** | "
                            f"평일: **{fmt_man(scroll_norm_cost, '메소')}** / 🔥 **피버타임: `{fmt_man(scroll_event_cost, '메소')}`** ({scroll_desc})"
                        )

        # 오른쪽 컬럼: 선택 파트 요약 영수증 & 반제품/완제품 즉시 판정
        with e_col2:
            with st.container(border=True):
                active_names = []
                if use_main_pot: active_names.append("🎲윗잠")
                if use_adi_pot: active_names.append("✨아랫잠")
                if use_sf: active_names.append(f"⭐스타포스({st.session_state.est_sf_start}➔{st.session_state.est_sf_target}성)")
                if use_flame: active_names.append("🔥추옵")
                if use_scroll: active_names.append("📜작")
                mode_badge = " + ".join(active_names) if active_names else "선택된 작업 없음"

                st.markdown(f"##### 🧾 공식 견적 영수증 | 현재 계산 범위: **`{mode_badge}`**")

                base_add = base_item_price if include_base else 0.0
                work_only_normal = flame_norm_cost + scroll_norm_cost + sf_norm_cost + main_norm_cost + adi_norm_cost
                work_only_event = flame_norm_cost + scroll_event_cost + sf_event_cost + main_mira_cost + adi_mira_cost

                grand_total_normal = base_add + scissors_cost + work_only_normal
                grand_total_event = base_add + scissors_cost + work_only_event

                val_mult = 1.0 + (market_valuation_shift / 100.0)
                fair_market_event = grand_total_event * val_mult

                m_top1, m_top2, m_top3 = st.columns(3)
                m_top1.metric("🛠️ 순수 작업 기대 원가 (이벤트)", fmt_man(work_only_event, "메소"), f"평일: {fmt_man(work_only_normal, '메소')}")
                m_top2.metric("✨ 총 직작 원가 (이벤트)", fmt_man(grand_total_event, "메소"), f"{'노작 포함' if include_base else '노작 제외'} | 평일 대비 -{fmt_man(grand_total_normal - grand_total_event, '메소')}")
                m_top3.metric(
                    f"⚖️ 보정({market_valuation_shift:+.0f}%) 적정가",
                    fmt_man(fair_market_event, "메소"),
                    f"경매장 매물가: {fmt_man(auction_finished_price, '메소')}" if auction_finished_price > 0 else "순수 직작 견적 모드"
                )

                receipt_rows = []
                if include_base or scissors_cost > 0:
                    receipt_rows.append({"항목": "🛒 초기 노작 + 가위", "평일 원가": fmt_man(base_add + scissors_cost, "메소"), "✨이벤트 원가": fmt_man(base_add + scissors_cost, "메소"), "세부 근거": f"노작 {fmt_man(base_add, '메소')} + 가위 {fmt_man(scissors_cost, '메소')}"})
                if use_main_pot:
                    receipt_rows.append({"항목": "🎲 윗잠재능력", "평일 원가": fmt_man(main_norm_cost, "메소"), "✨이벤트 원가": fmt_man(main_mira_cost, "메소"), "세부 근거": main_desc})
                if use_adi_pot:
                    receipt_rows.append({"항목": "✨ 아랫잠재능력", "평일 원가": fmt_man(adi_norm_cost, "메소"), "✨이벤트 원가": fmt_man(adi_mira_cost, "메소"), "세부 근거": adi_desc})
                if use_sf:
                    receipt_rows.append({"항목": "⭐ 스타포스", "평일 원가": fmt_man(sf_norm_cost, "메소"), "✨이벤트 원가": fmt_man(sf_event_cost, "메소"), "세부 근거": sf_desc})
                if use_flame:
                    receipt_rows.append({"항목": "🔥 추가옵션", "평일 원가": fmt_man(flame_norm_cost, "메소"), "✨이벤트 원가": fmt_man(flame_norm_cost, "메소"), "세부 근거": flame_desc})
                if use_scroll:
                    receipt_rows.append({"항목": "📜 주문서 작", "평일 원가": fmt_man(scroll_norm_cost, "메소"), "✨이벤트 원가": fmt_man(scroll_event_cost, "메소"), "세부 근거": scroll_desc})

                if receipt_rows:
                    st.dataframe(pd.DataFrame(receipt_rows), use_container_width=True, hide_index=True)
                else:
                    st.warning("왼쪽에서 계산할 파트를 1개 이상 체크하거나 위 단품 버튼을 눌러주세요.")

                if use_main_pot or use_adi_pot:
                    non_pot_event_base = base_add + scissors_cost + flame_norm_cost + scroll_event_cost + sf_event_cost
                    p50_tot = non_pot_event_base + main_p50_mira + adi_p50_mira
                    p85_tot = non_pot_event_base + main_p85_mira + adi_p85_mira
                    p95_tot = non_pot_event_base + main_p95_mira + adi_p95_mira
                    st.caption(
                        f"📊 **잠재 운빨 분포 반영 총 비용 (이벤트 기준):** "
                        f"🍀 상위 50%(중앙값) **`{fmt_man(p50_tot, '메소')}`** | "
                        f"🛡️ 85% 안전선 **`{fmt_man(p85_tot, '메소')}`** | "
                        f"⚠️ 95% 억까선 **`{fmt_man(p95_tot, '메소')}`**"
                    )

                st.divider()

                if auction_finished_price <= 0:
                    st.info(
                        f"💡 **순수 기대값 조회 모드:** 선택하신 **`[{mode_badge}]`**의 넥슨 공식 평균 기대 원가는 "
                        f"평일 **`{fmt_man(grand_total_normal, '메소')}`**, 이벤트 날 **`{fmt_man(grand_total_event, '메소')}`**입니다."
                    )
                else:
                    diff_from_fair = auction_finished_price - fair_market_event
                    st.markdown(f"###### 🛒 판정 1 (구매자 관점): 경매장 매물가(`{fmt_man(auction_finished_price, '메소')}`) vs 보정 직작 원가(`{fmt_man(fair_market_event, '메소')}`)")
                    if diff_from_fair < 0:
                        st.success(
                            f"💎 **[꿀매물 / 사서 쓰는 게 이득!]** 경매장 매물이 넥슨 공식 직작 기대 원가(보정 {market_valuation_shift:+.0f}% 반영)보다 "
                            f"**`{fmt_man(abs(diff_from_fair), '메소')}` 더 저렴합니다!** 직접 돌리지 말고 이 매물을 사서 마감하시는 게 이득입니다."
                        )
                    else:
                        st.warning(
                            f"🛠️ **[거품 매물 / 직작 우위]** 경매장 매물이 공식 직작 원가보다 **`+{fmt_man(diff_from_fair, '메소')}` 비쌉니다.** "
                            f"더 싼 매물을 찾거나 이벤트 날 직접 작업하는 편이 유리합니다."
                        )

                    net_sell_revenue = auction_finished_price * fee_mult
                    flip_profit_event = net_sell_revenue - grand_total_event
                    flip_profit_normal = net_sell_revenue - grand_total_normal

                    st.markdown(f"###### ⚖️ 판정 2 (장사꾼 관점): 직접 만들어 `{fmt_man(auction_finished_price, '메소')}`에 팔 때 (수수료 {fee_pct_str} 공제)")
                    if flip_profit_event > 0 and flip_profit_normal > 0:
                        st.info(f"🟢 **[직작 장사 강력 추천]** 평일 평균 **`+{fmt_man(flip_profit_normal, '메소')}`** / ✨이벤트 평균 **`+{fmt_man(flip_profit_event, '메소')}`** 순마진!")
                    elif flip_profit_event > 0:
                        st.info(f"🟡 **[이벤트 전용 장사]** 평일은 적자(`{fmt_man(flip_profit_normal, '메소')}`)지만, ✨이벤트 날 제작 시 평균 **`+{fmt_man(flip_profit_event, '메소')}`** 흑자!")
                    else:
                        st.error(f"🔴 **[직작 판매 적자 경고]** 이벤트 날 만들어 팔아도 평균 **`{fmt_man(flip_profit_event, '메소')}` 손해**입니다.")

                if st.button("📌 이 견적을 아래 비교 리스트에 저장하기", use_container_width=True):
                    net_s = auction_finished_price * fee_mult
                    fp_ev = net_s - grand_total_event
                    df_fair = auction_finished_price - fair_market_event
                    mp_data["saved_evals"].append({
                        "아이템명": eval_item_name,
                        "부위/구간": f"{part_short}({lv_bracket[:7]})",
                        "계산범위": mode_badge,
                        "평일원가": fmt_man(grand_total_normal, "메소"),
                        "✨이벤트원가": fmt_man(grand_total_event, "메소"),
                        f"보정가({market_valuation_shift:+.0f}%)": fmt_man(fair_market_event, "메소"),
                        "경매장가": fmt_man(auction_finished_price, "메소") if auction_finished_price > 0 else "순수견적",
                        "판정": "📋순수견적" if auction_finished_price <= 0 else ("💎매물꿀매" if df_fair < 0 else ("🟢직작장사" if fp_ev > 0 else "🔴관망"))
                    })
                    save_json_local(MAPLE_FILE, mp_data)
                    st.session_state.mp_dirty = True
                    st.rerun()

        if mp_data.get("saved_evals"):
            with st.expander("📋 내가 저장해 둔 견적 비교 리스트", expanded=True):
                st.dataframe(pd.DataFrame(mp_data["saved_evals"]), use_container_width=True, hide_index=True)
                if st.button("🗑️ 저장된 비교 리스트 비우기"):
                    mp_data["saved_evals"] = []
                    save_json_local(MAPLE_FILE, mp_data); st.session_state.mp_dirty = True; st.rerun()

        st.divider()

        with st.expander("📚 [2026 넥슨 공식 데이터 총람] 잠재 4구간 정가표 · 에디 천장 기댓값 · 개편 스타포스 공식표", expanded=False):
            st.markdown("##### 📌 1. 2026 넥슨 공식 잠재능력 1회 재설정 비용 정가표 (4구간)")
            cost_guide_rows = []
            for c_type, brackets in MAPLE_CUBE_COST_TABLE.items():
                for brk, tiers in brackets.items():
                    cost_guide_rows.append({
                        "구분": c_type, "레벨 구간": brk,
                        "레어 1회": fmt_man(tiers["레어"], "메소"), "에픽 1회": fmt_man(tiers["에픽"], "메소"),
                        "유니크 1회": fmt_man(tiers["유니크"], "메소"), "레전드리 1회": fmt_man(tiers["레전드리"], "메소")
                    })
            st.dataframe(pd.DataFrame(cost_guide_rows), use_container_width=True, hide_index=True)

            st.markdown("##### 📌 2. 2026 공식 등급업(천장 반영) 에픽 ➔ 레전드리 기댓값")
            tier_guide_rows = []
            for c_type, brackets in MAPLE_CUBE_COST_TABLE.items():
                for brk in brackets.keys():
                    ep_norm = calc_mesu_tierup(c_type, brk, "에픽", "레전드리", False)
                    ep_mira = calc_mesu_tierup(c_type, brk, "에픽", "레전드리", True)
                    tier_guide_rows.append({
                        "구분": c_type, "레벨 구간": brk,
                        "에픽->레전 평균(평일)": fmt_man(ep_norm["mean_cost"], "메소"),
                        "에픽->레전 평균(✨미라클)": fmt_man(ep_mira["mean_cost"], "메소"),
                        "50%중앙값(미라클)": fmt_man(ep_mira["p50_cost"], "메소"),
                        "100%천장합계": fmt_man(ep_norm["ceil_cost"], "메소"),
                    })
            st.dataframe(pd.DataFrame(tier_guide_rows), use_container_width=True, hide_index=True)

            st.markdown("##### 📌 3. 2025 개편 넥슨 공식 스타포스 기대 메소 & 평균 파괴 횟수 (0성 출발 / 스타캐치 O / 파방 X / 스페어 제외)")
            sf_guide_rows = []
            for lv_sample in [150, 160, 200, 250]:
                r17 = calc_starforce_expected(lv_sample, 0, 17, 0.0, "✨ 샤이닝 스타포스 (비용 30% 할인 + 21성 이하 파괴 30% 감소)", False, True)
                r18 = calc_starforce_expected(lv_sample, 0, 18, 0.0, "✨ 샤이닝 스타포스 (비용 30% 할인 + 21성 이하 파괴 30% 감소)", False, True)
                r21 = calc_starforce_expected(lv_sample, 0, 21, 0.0, "✨ 샤이닝 스타포스 (비용 30% 할인 + 21성 이하 파괴 30% 감소)", False, True)
                r22 = calc_starforce_expected(lv_sample, 0, 22, 0.0, "✨ 샤이닝 스타포스 (비용 30% 할인 + 21성 이하 파괴 30% 감소)", False, True)
                sf_guide_rows.append({
                    "장비 레벨": f"{lv_sample}제",
                    "17성 (샤타)": f"{fmt_man(r17['meso_cost'], '메소')} (파괴 {r17['booms']:.2f}회)",
                    "18성 (샤타)": f"{fmt_man(r18['meso_cost'], '메소')} (파괴 {r18['booms']:.2f}회)",
                    "21성 (샤타)": f"{fmt_man(r21['meso_cost'], '메소')} (파괴 {r21['booms']:.2f}회)",
                    "22성 (샤타)": f"{fmt_man(r22['meso_cost'], '메소')} (파괴 {r22['booms']:.2f}회)",
                })
            st.dataframe(pd.DataFrame(sf_guide_rows), use_container_width=True, hide_index=True)
# [파트 3 끝]
# [파트 4 시작]
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
                shift_mult = 1.0 + (float(mm_cfg.get("shift_pct", 0.0)) / 100.0)
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
    # 📘 [서브탭 5] 직작 & 장사 백과사전 (무기 추옵 계산기 + 옵션 우선순위 판독기 + 주문서 작 역산 판독기)
    # --------------------------------------------------------------------------
    with mp_sub5:
        st.markdown("#### 📘 메이플스토리 직작 & 장사 필수 백과사전 (실시간 자동 판독기 4종 탑재)")
        st.caption("경매장 매물 감정이나 직작 시 **방어구 추옵 급수 · 무기 1~5추옵 · 무기 옵션 우선순위/환금성 · 주문서 작 종류**를 숫자와 선택만으로 1초 만에 판독할 수 있습니다.")

        # 1. 방어구/장신구 추옵 급수 계산기
        with st.container(border=True):
            st.markdown("##### 🧮 1. '방어구/장신구 추옵 급수(OO급)' 계산기")
            st.markdown(
                "인게임 아이템 툴팁의 **초록색 숫자(`+OO`)**를 넣으면 몇 급인지 즉시 계산됩니다! "
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
                {"장비 종류": "👑 보스 방어구/장신구 (데브펜, 트와마, 가엔링, 아케인, 앱솔 등)", "추옵 특징": "보스 추옵 보정 O (4줄 고정, 높은 수치)", "가성비/부캐용": "100급 ~ 110급", "국민 본캐용 (거래 활발)": "120급 ~ 130급", "고스펙/준종결": "140급 ~ 150급+"},
                {"장비 종류": "👓 일반 제작/드롭 장비 (미카엘라 새안경, 하프이어링, 마이스터링 등)", "추옵 특징": "보스 추옵 보정 X (1~4줄 랜덤)", "가성비/부캐용": "50급 ~ 65급", "국민 본캐/드메용": "75급 ~ 85급", "고스펙/준종결": "95급 ~ 110급+"},
            ]
            st.dataframe(pd.DataFrame(grade_table), use_container_width=True, hide_index=True)

        g_col1, g_col2 = st.columns(2, gap="large")

        # 왼쪽 컬럼: 2. 무기 1~5추옵 자동 판독기 + 3. 무기 옵션 우선순위 & 시장 가치 판독기
        with g_col1:
            with st.container(border=True):
                st.markdown("##### ⚔️ 2. 무기 '1추옵 ~ 5추옵' 실시간 자동 판독기")
                st.caption("무기 등급과 직업군(또는 흰색 기본 공/마)을 고르고 경매장 매물의 **초록색 공/마(+)**를 넣으면 몇 추옵인지 즉시 판독합니다!")

                WEAPON_BASE_ATT = {
                    "아케인셰이드 / 제네시스 (200제)": {
                        "스태프 (법사)": 353, "완드 (법사)": 318, "샤이닝로드 (루미)": 318, "ESP리미터 (키네)": 318,
                        "매직건틀렛 (일리움)": 318, "부채 (호영)": 318, "두손검/두손도끼/두손둔기": 295,
                        "창 / 폴암": 295, "건틀렛 리볼버 (블래)": 295, "데스페라도 (데벤)": 295,
                        "튜너 (아델)": 295, "무권 (아크)": 295, "한손검/한손도끼/한손둔기": 283,
                        "활 (보마)": 276, "석궁 (신궁)": 276, "에인션트 보우 (패파)": 276, "듀얼보우건 (메르)": 276,
                        "브레스 슈터 (카인)": 276, "케인 (팬텀)": 276, "체인 (카데나)": 276, "단검 (섀도어)": 276,
                        "블레이드 (듀블 보조)": 140, "건 (캡틴)": 221, "너클 (바이퍼/은월/스커)": 221,
                        "에너지소드 (제논)": 221, "소울슈터 (엔버)": 221, "아대 (나로)": 149,
                        "✏️ 직접 기본 공/마 입력": 295
                    },
                    "앱솔랩스 (160제)": {
                        "스태프 (법사)": 241, "완드 (법사)": 218, "두손검/두손도끼/두손둔기": 205,
                        "창 / 폴암": 205, "한손검/한손도끼/한손둔기": 197, "활/석궁/케인/체인/단검": 192,
                        "건 / 너클 / 소울슈터": 154, "아대 (나로)": 103,
                        "✏️ 직접 기본 공/마 입력": 205
                    },
                    "파프니르 (150제)": {
                        "스태프 (법사)": 204, "완드 (법사)": 185, "두손검/두손도끼/두손둔기": 171,
                        "창 / 폴암": 171, "한손검/한손도끼/한손둔기": 164, "활/석궁/케인/체인/단검": 160,
                        "건 / 너클 / 소울슈터": 128, "아대 (나로)": 86,
                        "✏️ 직접 기본 공/마 입력": 171
                    }
                }

                FLAME_TIER_COEFF = {
                    "아케인셰이드 / 제네시스 (200제)": [0.4408, 0.3206, 0.2204, 0.1403, 0.0802],
                    "앱솔랩스 (160제)": [0.3630, 0.2640, 0.1815, 0.1155, 0.0660],
                    "파프니르 (150제)": [0.3630, 0.2640, 0.1815, 0.1155, 0.0660],
                }

                wc1, wc2 = st.columns(2)
                with wc1:
                    wp_grade = st.selectbox("1. 무기 등급(레벨)", list(WEAPON_BASE_ATT.keys()), key="wp_calc_grade")
                with wc2:
                    wp_job = st.selectbox("2. 직업 / 무기 종류", list(WEAPON_BASE_ATT[wp_grade].keys()), key="wp_calc_job")

                wc3, wc4 = st.columns(2)
                with wc3:
                    default_b_att = WEAPON_BASE_ATT[wp_grade][wp_job]
                    base_att_in = st.number_input("3. 무기 흰색 기본 공/마", min_value=50, max_value=600, value=int(default_b_att), step=1, key=f"wp_batt_{wp_grade}_{wp_job}")
                with wc4:
                    coeffs = FLAME_TIER_COEFF[wp_grade]
                    t1 = math.ceil(base_att_in * coeffs[0])
                    t2 = math.ceil(base_att_in * coeffs[1])
                    t3 = math.ceil(base_att_in * coeffs[2])
                    t4 = math.ceil(base_att_in * coeffs[3])
                    t5 = math.ceil(base_att_in * coeffs[4])
                    green_att_in = st.number_input("4. 매물의 초록색 공/마 (+)", min_value=0, max_value=300, value=int(t1), step=1, key="wp_gatt")

                if green_att_in >= t1:
                    wp_verdict = f"👑 1추옵 (최고 등급! 기준 +{t1} 이상)"
                elif green_att_in >= t2:
                    wp_verdict = f"🔥 2추옵 (실전 합격! 기준 +{t2} 이상)"
                elif green_att_in >= t3:
                    wp_verdict = f"🟡 3추옵 (가성비/환불 권장, 기준 +{t3})"
                elif green_att_in >= t4:
                    wp_verdict = f"⚪ 4추옵 (미달, 기준 +{t4})"
                elif green_att_in >= t5:
                    wp_verdict = f"⚪ 5추옵 (최하급, 기준 +{t5})"
                else:
                    wp_verdict = "❌ 공/마 추옵 없음 (환불 필수)"

                st.success(f"**판독:** **`{wp_verdict}`**\n\n이 무기의 공식 기준표: **1추 `+{t1}`** | **2추 `+{t2}`** | **3추 `+{t3}`** | 4추 `+{t4}` | 5추 `+{t5}`")

            with st.container(border=True):
                st.markdown("##### 🎯 3. 무기(무보엠) 옵션 우선순위 & 경매장 시장 가치 판독기")
                st.caption("사용 목적과 현재 뜬 잠재 3줄을 고르면 **실전 효율과 경매장 환금성(잘 팔리는지 여부)**을 판독해 드립니다.")

                op_c1, op_c2 = st.columns([1.2, 1.8])
                with op_c1:
                    wp_purpose = st.radio("사용 목적", ["🐉 보스/해방용", "⚔️ 사냥(재획)용", "💰 경매장 장사용"], key="wp_purp")
                with op_c2:
                    POT_LINE_OPTS = ["공격력/마력 %", "보스 공격력 %", "방어율 무시 %", "주스탯% / 잡옵"]
                    l1 = st.selectbox("1번째 줄", POT_LINE_OPTS, index=0, key="wp_l1")
                    l2 = st.selectbox("2번째 줄", POT_LINE_OPTS, index=1, key="wp_l2")
                    l3 = st.selectbox("3번째 줄", POT_LINE_OPTS, index=0, key="wp_l3")

                lines = [l1, l2, l3]
                n_att = lines.count("공격력/마력 %")
                n_boss = lines.count("보스 공격력 %")
                n_ied = lines.count("방어율 무시 %")
                n_valid_boss = n_att + n_boss

                if wp_purpose == "⚔️ 사냥(재획)용":
                    if n_att == 3:
                        st.success("👑 **[사냥 종결 3줄]** 공/마% 3줄! 사냥·보스 모두 최상급이며 경매장에서도 초고가에 즉시 팔립니다.")
                    elif n_att == 2:
                        st.info("🔥 **[사냥 실전 2줄]** 재획 원킬 컷에 아주 우수합니다. (보공/방무는 일반 몬스터에게 적용되지 않습니다.)")
                    else:
                        st.warning(f"🟡 **[사냥용 비추천]** 사냥에는 오직 **공/마%**만 적용됩니다. 현재 유효 {n_att}줄입니다.")
                elif wp_purpose == "💰 경매장 장사용":
                    if n_valid_boss == 3:
                        st.success("💎 **[S급 황금 매물 - 최고 환금성]** 방무가 섞이지 않은 순수 `공/마% + 보공%` 3줄! 감가 없이 제값에 가장 빨리 팔립니다.")
                    elif n_valid_boss == 2 and n_ied == 1:
                        st.info("🟡 **[A급 실전 3줄 - 방무 감가 존재]** 실전 성능은 좋지만 경매장에서는 순수 보공/공마 3줄보다 시세가 낮게 형성됩니다. 적정가에 빠르게 처분하세요.")
                    elif n_valid_boss == 2:
                        st.info("🟢 **[B급 국민 2줄]** 해방 전 거쳐가는 아케인 무기나 부캐용으로 거래량이 꾸준한 국민 매물입니다.")
                    else:
                        st.error("🔴 **[장사 비추천 / 꽝 매물]** 방무 2줄 이상이거나 잡옵이 많아 경매장에서 잘 팔리지 않습니다. 큐브를 더 돌리세요.")
                else:
                    if n_valid_boss == 3:
                        st.success("👑 **[보스 종결 3줄 (보보공/보공공/공공공)]** 제네시스 해방 무기 기준 평생 쓰는 졸업 옵션입니다!")
                    elif n_valid_boss == 2 and n_ied == 1:
                        st.success("🔥 **[보스 실전 3줄 (방무 1줄 포함)]** 방무가 부족한 구간에서는 체감 딜이 엄청나게 좋습니다. 본캐 실사용으로 강력 추천!")
                    elif n_valid_boss == 2:
                        st.info("🟢 **[해방 전 합격 2줄]** 해방 전 아케인 무기나 주보돌이용으로 충분한 가성비 옵션입니다.")
                    else:
                        st.warning("🟡 **[스펙업 필요]** 보스용 무기는 최소 `공/마% + 보공%` 2줄 이상을 맞추는 것이 정석입니다.")

                prio_df = pd.DataFrame([
                    {"순위": "1순위", "옵션": "공격력 / 마력 %", "보스": "★★★★★", "사냥": "★★★★★", "경매장 환금성": "👑 최고가 (무조건 1티어)"},
                    {"순위": "2순위", "옵션": "보스 공격력 %", "보스": "★★★★★", "사냥": "❌ 미적용", "경매장 환금성": "🔥 최상 (공%와 조합 시 종결)"},
                    {"순위": "3순위", "옵션": "방어율 무시 %", "보스": "★★★☆☆", "사냥": "❌ 미적용", "경매장 환금성": "🟡 감가 발생 (1줄까지만 유효)"},
                    {"순위": "4순위", "옵션": "주스탯 %", "보스": "❌ 잡옵", "사냥": "❌ 잡옵", "경매장 환금성": "🔴 무가치 (방어구/장신구 전용)"},
                ])
                st.dataframe(prio_df, use_container_width=True, hide_index=True)

        # 오른쪽 컬럼: 4. 주문서 작 역산 판독기 + 5. 대장장이/합성/토드 & 은어 사전
        with g_col2:
            with st.container(border=True):
                st.markdown("##### 📜 4. 경매장 완제품 '주문서 작' 실시간 역산 판독기")
                st.caption(
                    "아이템 툴팁의 **순수 주문서 상승치(`파란색 총합 - 초록색 추옵 - 스타포스 상승분`)**와 **강화(작) 횟수**를 넣으면 무슨 작인지 판독합니다!"
                )

                sr_c1, sr_c2 = st.columns(2)
                with sr_c1:
                    sr_part = st.selectbox("1. 장비 부위", ["⚔️ 무기 (150~200제)", "🛡️ 방어구 (120제 이상)", "🧤 장갑", "💍 장신구 (반지/펜던트/귀고리 등)"], key="sr_part")
                    sr_cnt = st.number_input("2. 주문서 성공(작) 횟수 (예: +8, +10)", min_value=1, max_value=15, value=9, step=1, key="sr_cnt")
                with sr_c2:
                    sr_att = st.number_input("3. 순수 주문서 상승 공/마 (+)", min_value=0, max_value=200, value=81, step=1, key="sr_att")
                    sr_stat = st.number_input("4. 순수 주문서 상승 주스탯 (+)", min_value=0, max_value=200, value=36, step=1, key="sr_stat")

                per_att = sr_att / sr_cnt
                per_stat = sr_stat / sr_cnt

                if "무기" in sr_part:
                    if per_att >= 9.5:
                        sr_res = f"👑 매지컬 / 프악공 등 초고자본 특수작! (1작당 공/마 +{per_att:.1f})"
                    elif 8.5 <= per_att < 9.5:
                        sr_res = f"🔥 주흔 15% 완작! (1작당 공/마 +{per_att:.1f}, 주스탯 +{per_stat:.1f} - 본캐/해방 정석)"
                    elif 6.5 <= per_att < 8.5:
                        sr_res = f"🟢 주흔 30% 완작 (1작당 공/마 +{per_att:.1f}, 주스탯 +{per_stat:.1f})"
                    elif 4.5 <= per_att < 6.5:
                        sr_res = f"🟡 주흔 70% 완작 (1작당 공/마 +{per_att:.1f} - 부캐/가성비)"
                    else:
                        sr_res = f"⚪ 주흔 100% 작 또는 잡작 (1작당 공/마 +{per_att:.1f})"
                elif "방어구" in sr_part:
                    if per_att >= 2.5:
                        sr_res = f"👑 놀긍혼 / 프방공 등 고자본 공마작! (1작당 공/마 +{per_att:.1f}, 주스탯 +{per_stat:.1f})"
                    elif per_stat >= 9.5:
                        sr_res = f"👑 주흔 15% 완작! (1작당 주스탯 +{per_stat:.1f} - 22성 종결급)"
                    elif 6.5 <= per_stat < 9.5:
                        sr_res = f"🔥 주흔 30% 완작! (1작당 주스탯 +{per_stat:.1f} - 본캐 17~22성 국민 정석)"
                    elif 3.5 <= per_stat < 6.5:
                        sr_res = f"🟡 주흔 70% 완작 (1작당 주스탯 +{per_stat:.1f} - 부캐/토드/가성비)"
                    else:
                        sr_res = f"⚪ 주흔 100% 작 또는 미완작 (1작당 주스탯 +{per_stat:.1f})"
                elif "장갑" in sr_part:
                    if per_att >= 3.8:
                        sr_res = f"👑 주흔 15% 완작 또는 프방공! (1작당 공/마 +{per_att:.1f})"
                    elif 2.8 <= per_att < 3.8:
                        sr_res = f"🔥 주흔 30% 완작! (1작당 공/마 +{per_att:.1f} - 본캐 국민 정석)"
                    elif 1.8 <= per_att < 2.8:
                        sr_res = f"🟡 주흔 70% 완작 (1작당 공/마 +{per_att:.1f} - 가성비)"
                    else:
                        sr_res = f"⚪ 주흔 100% 작 또는 잡작 (1작당 공/마 +{per_att:.1f})"
                else:
                    if per_att >= 3.8 and per_stat == 0:
                        sr_res = f"👑 프악공 / 프악마 완작! (1작당 공/마 +{per_att:.1f} 확정 상승 - 종결급)"
                    elif per_att >= 2.0:
                        sr_res = f"🔥 놀긍혼(긍정의 혼돈) 작! (1작당 공/마 +{per_att:.1f}, 주스탯 +{per_stat:.1f} / 공+4↑ 상급)"
                    elif per_stat >= 4.0:
                        sr_res = f"🟢 주흔 30% 완작 (1작당 주스탯 +{per_stat:.1f})"
                    else:
                        sr_res = f"🟡 주흔 70% / 100% 작 (1작당 주스탯 +{per_stat:.1f} - 드메템/가성비)"

                st.info(f"**판독 결과:** **`{sr_res}`**")

                scr_table = [
                    {"부위 및 작 이름": "⚔️ 무기: 주흔 15% / 30% / 70%", "1작당 상승 수치": "공+9·스탯+4 / 공+7·스탯+3 / 공+5·스탯+2"},
                    {"부위 및 작 이름": "🛡️ 방어구: 주흔 15% / 30% / 70%", "1작당 상승 수치": "스탯 +10 / +7 / +4 (4작째 공/마+1)"},
                    {"부위 및 작 이름": "🧤 장갑: 주흔 15% / 30% / 70%", "1작당 상승 수치": "공/마 +4 / +3 / +2 (스탯 안 오름)"},
                    {"부위 및 작 이름": "💍 장신구: 놀긍혼 / 프악공", "1작당 상승 수치": "놀긍(공+3~5 랜덤) / 프악공(공+4~5 확정)"},
                ]
                st.dataframe(pd.DataFrame(scr_table), use_container_width=True, hide_index=True)

            with st.container(border=True):
                st.markdown("##### 🔨 5. 대장장이·합성·토드 가이드 & 장사꾼 필수 은어 사전")
                st.markdown(
                    """
- **💍 제작 & 합성 장사:** 미카엘라 안경(90제)·하프 이어링(75제) 등을 제작·합성해 에픽/고추옵을 띄우고, **미라클 데이에 레전드리 드메(아획/메획) 1~2줄**을 만들어 팔면 고마진 확보 가능!
- **🔨 토드의 망치 장사:** 감정비가 싼 80~120제에서 `에픽 주스탯 9~12% + 에디 공+10`을 띄워 10레벨 단위로 160~200제에 전승 판매.
                    """
                )
                term_table = [
                    {"용어": "드메템 (아획/메획)", "뜻과 장사 포인트": "드롭률/메획 +20% 잠재 장신구. 거래량과 환금성이 가장 좋은 1티어 장사 종목."},
                    {"용어": "정옵 / 이탈옵", "뜻과 장사 포인트": "정옵(12+9+9=30%), 이탈옵(둘째·셋째 줄에 첫 줄 최고치 12%가 뜬 33% 고가 매물)."},
                    {"용어": "크뎀 장갑 / 쿨감뚝", "뜻과 장사 포인트": "장갑 크뎀 8%(1줄=주스탯 24~27%급), 모자 쿨감 -2~4초(미라클 데이 대박 종목)."},
                    {"용어": "노작 / 스페어", "뜻과 장사 포인트": "강화 안 된 원본 장비. 18~22성 스타포스 파괴 시 전승 복구용으로 똑같은 노작 1개 소모."},
                ]
                st.dataframe(pd.DataFrame(term_table), use_container_width=True, hide_index=True)
# [파트 4 끝]
