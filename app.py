import streamlit as st

st.set_page_config(page_title="나만의 게임 숙제 매니저", page_icon="🎮", layout="wide")

st.title("🎮 로아 · 메이플 · 거상 통합 매니저")
st.caption("매일 헷갈리는 숙제와 효율을 한눈에 관리하는 나만의 대시보드")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("⚓ 로스트아크")
    st.info("초기화: 매일 오전 06:00 / 수요일 06:00")
    st.checkbox("카던 (공명의 기운)", key="loa_chaos")
    st.checkbox("가디언 토벌", key="loa_guardian")
    st.checkbox("에포나 의뢰 3회", key="loa_epona")

with col2:
    st.subheader("🍁 메이플스토리")
    st.warning("초기화: 매일 자정 00:00 / 목요일 00:00")
    st.checkbox("아케인/어센틱 일일 퀘스트", key="maple_daily")
    st.checkbox("몬스터파크", key="maple_monpark")
    st.checkbox("일간 보스 & 우르스", key="maple_boss")

with col3:
    st.subheader("💰 천하제일상 거상")
    st.success("초기화: 매일 자정 00:00")
    st.checkbox("일일 퀘스트 (백종/염라 등)", key="gersang_daily")
    st.checkbox("생산 시설 확인 및 작업량 채우기", key="gersang_prod")
    st.checkbox("오늘치 반자사/사냥 목표 달성", key="gersang_hunt")
