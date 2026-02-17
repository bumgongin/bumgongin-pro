# app.py - 범공인 Pro 메인 관리 타워
import streamlit as st
import core_engine as engine
import list_view # 이사 간 실행 부대를 불러옵니다.
import styles

# 1. 초기화
st.set_page_config(page_title="범공인 Pro (v24.60)", layout="wide")
styles.apply_custom_css()
engine.initialize_search_state()

# 2. 사이드바 (컨트롤러)
with st.sidebar:
    st.header("📂 관리 도구")
    # 시트 선택 및 필터 로직... (사장님 코드의 사이드바 내용 유지)
    if 'df_main' not in st.session_state:
        st.session_state.df_main = engine.load_sheet_data(st.session_state.current_sheet)

st.title("🏙️ 범공인 매물장 (Pro)")

# 3. 핵심 실행: 실제 화면 구성은 list_view가 담당하게 함
list_view.show_main_list()
