import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.17.1)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [2. 스타일 설정]
st.markdown("""
    <style>
    .stButton button { min-height: 50px !important; font-size: 16px !important; font-weight: bold !important; }
    input[type=number] { min-height: 40px; }
    div[data-testid="stExpander"] details summary p { font-size: 1.1rem; font-weight: 600; }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] { border: 2px solid #ddd; }
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 💡 GID 매핑 (데이터 무결성 핵심)
SHEET_BASE_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU"
SHEET_GIDS = {
    "임대": "2063575964", 
    "임대(종료)": "791354475", 
    "매매": "1833762712", 
    "매매(종료)": "1597438389",
    "임대브리핑": "982780192", 
    "매매브리핑": "807085458"
}
SHEET_NAMES = list(SHEET_GIDS.keys())

# [3. 데이터 로드 엔진 (GID + 정직한 매핑)]
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    
    csv_url = f"{SHEET_BASE_URL}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(csv_url)
    except Exception:
        return None

    # 헤더 정제
    df.columns = df.columns.str.replace(' ', '').str.strip()
    
    # 1:1 매핑 (Synonym Map)
    synonym_map = {
        "보증금": ["보증금(만원)", "기보증금(만원)", "기보증금", "보증금"],
        "월차임": ["월차임(만원)", "기월세(만원)", "월세(만원)", "월세", "기월세"],
        "권리금": ["권리금_입금가(만원)", "권리금(만원)", "권리금"],
        "관리비": ["관리비(만원)", "관리비"],
        "매매가": ["매매가(만원)", "매매금액(만원)", "매매금액", "매매가"],
        "면적": ["전용면적(평)", "실평수", "전용면적", "면적"],
        "대지면적": ["대지면적(평)", "대지", "대지면적"],
        "연면적": ["연면적(평)", "연면적"],
        "수익률": ["수익률(%)", "수익률"],
        "층": ["해당층", "층", "지상층"],
        "내용": ["매물특징", "특징", "비고", "내용"],
        "번지": ["지역_번지", "번지", "지번"],
        "구분": ["매물구분", "구분", "용도"],
        "건물명": ["건물명", "빌딩명"]
    }

    for standard, aliases in synonym_map.items():
        for alias in aliases:
            clean_alias = alias.replace(' ', '')
            if clean_alias in df.columns:
                df.rename(columns={clean_alias: standard}, inplace=True)
                break

    # 숫자형 변환
    numeric_candidates = ["보증금", "월차임", "권리금", "관리비", "면적", "층", "매매가", "수익률", "대지면적", "연면적"]
    for col in numeric_candidates:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    df = df.fillna("")

    if '선택' in df.columns: df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

# [A] 시트 관리
if 'current_sheet' not in st.session_state:
    st.session_state.current_sheet = SHEET_NAMES[0]

with st.sidebar:
    st.header("📂 작업 공간 선택")
    
    try:
        curr_idx = SHEET_NAMES.index(st.session_state.current_sheet)
    except:
        curr_idx = 0
        
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES, index=curr_idx)
    
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        st.cache_data.clear()
        st.rerun()

    st.divider()
    
    if st.button("🔄 검색 조건 초기화", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.session_state.clear()
        st.rerun()

    st.caption("Developed by Gemini & Pro-Mode")

# [B] 데이터 로드
df_main = load_data(st.session_state.current_sheet)

if df_main is None:
    st.error(f"🚨 '{st.session_state.current_sheet}' 시트를 찾을 수 없습니다. GID 설정을 확인하세요.")
    st.stop()

# 모드 판단
is_sale_mode = "매매" in st.session_state.current_sheet

# Helper Functions
def get_max_if_exists(col):
    if col in df_main.columns and not df_main.empty:
        val = df_main[col].max()
        return float(val) if val > 0 else 100.0
    return None

def sess(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

# ---------------------------------------------------------
# [모듈 2: 조건부 필터 UI]
# ---------------------------------------------------------
with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
    # 1. 텍스트, 구분, 지역
    c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 1])
    with c1: st.text_input("통합 검색", key='search_keyword', placeholder="내용, 건물명, 번지 등 전체 검색")
    with c2: st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
    
    # 구분 (안전한 인덱스 참조)
    with c3:
        unique_cat = ["전체"]
        if '구분' in df_main.columns:
            unique_cat += sorted(df_main['구분'].astype(str).unique().tolist())
        
        curr_cat = sess('selected_cat', '전체')
        # 값이 리스트에 없으면 강제 초기화
        cat_idx = unique_cat.index(curr_cat) if curr_cat in unique_cat else 0
        sel_cat = st.selectbox("구분", unique_cat, key='selected_cat', index=cat_idx)

    # 지역
    unique_gu = ["전체"]
    if '지역_구' in df_main.columns:
        unique_gu += sorted(df_main['지역_구'].astype(str).unique().tolist())
    
    with c4: 
        curr_gu = sess('selected_gu', '전체')
        gu_idx = unique_gu.index(curr_gu) if curr_gu in unique_gu else 0
        sel_gu = st.selectbox("지역 (구)", unique_gu, key='selected_gu', index=gu_idx)
        
    unique_dong = ["전체"]
    if '지역_동' in df_main.columns:
        if sel_gu == "전체":
            unique_dong += sorted(df_main['지역_동'].astype(str).unique().tolist())
        else:
            unique_dong += sorted(df_main[df_main['지역_구'] == sel_gu]['지역_동'].astype(str).unique().tolist())
            
    with c5: 
        curr_dong = sess('selected_dong', '전체')
        dong_idx = unique_dong.index(curr_dong) if curr_dong in unique_dong else 0
        sel_dong = st.selectbox("지역 (동)", unique_dong, key='selected_dong', index=dong_idx)

    st.divider()

    # 2. 수치 필터 (매매/임대 분기 + 로직 수리)
    r1, r2, r3 = st.columns(3)
    LIMIT_HUGE = 100000000.0 

    if is_sale_mode:
        # [매매 모드 UI]
        with r1:
            st.markdown("##### 💰 매매가 (만원)")
            max_price = get_max_if_exists("매매가")
            if max_price is not None:
                c_a, c_b = st.columns(2)
                c_a.number_input("최소", step=1000.0, key='min_price', value=sess('min_price', 0.0))
                c_b.number_input("최대", step=1000.0, key='max_price', value=sess('max_price', max_price))
            else: st.caption("🚫 매매가 정보 없음")

        with r2:
            st.markdown("##### 📊 수익률(%)")
            max_yield = get_max_if_exists("수익률")
            if max_yield is not None:
                c_a, c_b = st.columns(2)
                c_a.number_input("최소", step=0.1, key='min_yield', value=sess('min_yield', 0.0))
                c_b.number_input("최대", step=0.1, key='max_yield', value=sess('max_yield', 20.0))
            else: st.caption("🚫 수익률 정보 없음")

        with r3:
            st.markdown("##### 📐 대지/연면적 (평)")
            max_land = get_max_if_exists("대지면적")
            max_total = get_max_if_exists("연면적")
            
            c_a, c_b = st.columns(2)
            if max_land is not None:
                c_a.number_input("대지 최소", step=1.0, key='min_land', value=sess('min_land', 0.0))
            else: c_a.caption("-")
            
            # [수정] 대지 최대값은 max_land 변수를 참조하도록 수정
            if max_land is not None: 
                c_b.number_input("대지 최대", max_value=1000000.0, step=1.0, key='max_land', value=sess('max_land', max_land))
            else: c_b.caption("-")
            
            st.caption("--- 연면적 ---")
            c_c, c_d = st.columns(2)
            if max_total is not None:
                c_c.number_input("연면 최소", step=1.0, key='min_total', value=sess('min_total', 0.0))
                c_d.number_input("연면 최대", max_value=1000000.0, step=1.0, key='max_total', value=sess('max_total', max_total))
            else: c_c.caption("-")

    else:
        # [임대 모드 UI]
        with r1:
            st.markdown("##### 💰 보증금/월세 (만원)")
            max_dep = get_max_if_exists("보증금")
            max_rent = get_max_if_exists("월차임")
            
            c_a, c_b = st.columns(2)
            if max_dep is not None:
                c_a.number_input("보증금 최소", step=500.0, key='min_dep', value=sess('min_dep', 0.0))
                c_b.number_input("보증금 최대", max_value=LIMIT_HUGE, step=500.0, key='max_dep', value=sess('max_dep', max_dep)) 
            else: c_a.caption("보증금X")
                
            c_c, c_d = st.columns(2) 
            if max_rent is not None:
                c_c.number_input("월세 최소", step=10.0, key='min_rent', value=sess('min_rent', 0.0))
                c_d.number_input("월세 최대", max_value=1000000.0, step=10.0, key='max_rent', value=sess('max_rent', max_rent)) 
            else: c_c.caption("월세X")

        with r2:
            st.markdown("##### 🔑 권리금/관리비")
            is_no_kwon = st.checkbox("무권리만", key='is_no_kwon')
            max_kwon = get_max_if_exists("권리금")
            max_man = get_max_if_exists("관리비")
            
            c_a, c_b = st.columns(2)
            if max_kwon is not None:
                c_a.number_input("권리금 최소", step=100.0, key='min_kwon', disabled=is_no_kwon, value=sess('min_kwon', 0.0))
                c_b.number_input("권리금 최대", max_value=LIMIT_HUGE, step=100.0, key='max_kwon', disabled=is_no_kwon, value=sess('max_kwon', max_kwon)) 
            else: c_a.caption("권리금X")
            
            c_c, c_d = st.columns(2)
            if max_man is not None:
                c_c.number_input("관리비 최소", step=5.0, key='min_man', value=sess('min_man', 0.0))
                c_d.number_input("관리비 최대", max_value=1000000.0, step=5.0, key='max_man', value=sess('max_man', max_man)) 
            else: c_c.caption("관리비X")

        with r3:
            st.markdown("##### 📐 면적 (평)")
            max_area = get_max_if_exists("면적")
            if max_area is not None:
                c_a, c_b = st.columns(2)
                c_a.number_input("면적 최소", step=5.0, key='min_area', value=sess('min_area', 0.0))
                c_b.number_input("면적 최대", step=5.0, key='max_area', value=sess('max_area', max_area))
            else: st.caption("🚫 면적 정보 없음")

# ---------------------------------------------------------
# [필터링 로직: 안전성 최우선]
# ---------------------------------------------------------
df_filtered = df_main.copy()

if '구분' in df_filtered.columns and sel_cat != "전체":
    df_filtered = df_filtered[df_filtered['구분'] == sel_cat]

if '지역_구' in df_filtered.columns and sel_gu != "전체":
    df_filtered = df_filtered[df_filtered['지역_구'] == sel_gu]
if '지역_동' in df_filtered.columns and sel_dong != "전체":
    df_filtered = df_filtered[df_filtered['지역_동'] == sel_dong]

if '번지' in df_filtered.columns and st.session_state.exact_bunji:
    df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]

# 수치 필터
if is_sale_mode:
    if '매매가' in df_filtered.columns and 'min_price' in st.session_state:
        df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
    # [수정] 수익률 Min ~ Max 범위 검색 적용
    if '수익률' in df_filtered.columns and 'min_yield' in st.session_state:
        df_filtered = df_filtered[(df_filtered['수익률'] >= st.session_state.min_yield) & (df_filtered['수익률'] <= st.session_state.max_yield)]
    if '대지면적' in df_filtered.columns and 'min_land' in st.session_state:
        df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land) & (df_filtered['대지면적'] <= st.session_state.max_land)]
    if '연면적' in df_filtered.columns and 'min_total' in st.session_state:
        df_filtered = df_filtered[(df_filtered['연면적'] >= st.session_state.min_total) & (df_filtered['연면적'] <= st.session_state.max_total)]
else:
    if '보증금' in df_filtered.columns and 'min_dep' in st.session_state:
        df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
    if '월차임' in df_filtered.columns and 'min_rent' in st.session_state:
        df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
    if '면적' in df_filtered.columns and 'min_area' in st.session_state:
        df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
    if '관리비' in df_filtered.columns and 'min_man' in st.session_state:
        df_filtered = df_filtered[(df_filtered['관리비'] >= st.session_state.min_man) & (df_filtered['관리비'] <= st.session_state.max_man)]
    if '권리금' in df_filtered.columns and 'min_kwon' in st.session_state:
        if st.session_state.is_no_kwon:
            df_filtered = df_filtered[df_filtered['권리금'] == 0]
        else:
            df_filtered = df_filtered[(df_filtered['권리금'] >= st.session_state.min_kwon) & (df_filtered['권리금'] <= st.session_state.max_kwon)]

# ---------------------------------------------------------
# [핵심] 슈퍼 옴니 서치
# ---------------------------------------------------------
search_val = st.session_state.search_keyword.strip()
if search_val:
    search_scope = df_filtered.drop(columns=['선택'], errors='ignore')
    mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
    df_filtered = df_filtered[mask]

# ---------------------------------------------------------
# [결과 출력]
# ---------------------------------------------------------
if len(df_filtered) == 0:
    st.warning("🔍 검색 결과가 없습니다.")
else:
    st.info(f"📋 **{st.session_state.current_sheet}** 검색 결과: **{len(df_filtered)}**건")

# 리스트 잠금
disabled_cols = [c for c in df_filtered.columns if c != '선택']
editor_key = f"editor_{st.session_state.current_sheet}"

# 동적 컬럼 포맷
col_cfg = {"선택": st.column_config.CheckboxColumn(width="small")}
if "매매가" in df_filtered.columns: col_cfg["매매가"] = st.column_config.NumberColumn("매매가(만)", format="%d")
if "보증금" in df_filtered.columns: col_cfg["보증금"] = st.column_config.NumberColumn("보증금(만)", format="%d")
if "월차임" in df_filtered.columns: col_cfg["월차임"] = st.column_config.NumberColumn("월세(만)", format="%d")
if "권리금" in df_filtered.columns: col_cfg["권리금"] = st.column_config.NumberColumn("권리금(만)", format="%d")
if "면적" in df_filtered.columns: col_cfg["면적"] = st.column_config.NumberColumn("면적(평)", format="%.1f")
if "대지면적" in df_filtered.columns: col_cfg["대지면적"] = st.column_config.NumberColumn("대지(평)", format="%.1f")
if "연면적" in df_filtered.columns: col_cfg["연면적"] = st.column_config.NumberColumn("연면(평)", format="%.1f")
if "수익률" in df_filtered.columns: col_cfg["수익률"] = st.column_config.NumberColumn("수익률", format="%.2f%%")
if "내용" in df_filtered.columns: col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")

edited_df = st.data_editor(
    df_filtered,
    disabled=disabled_cols,
    use_container_width=True,
    hide_index=True,
    height=600,
    column_config=col_cfg,
    key=editor_key
)

# ---------------------------------------------------------
# [Phase 3: 액션 버튼 바 (Logic 정교화)]
# ---------------------------------------------------------
st.divider()

selected_rows = edited_df[edited_df['선택'] == True]
selected_count = len(selected_rows)

if selected_count > 0:
    st.success(f"✅ {selected_count}건의 매물이 선택되었습니다.")
    
    # 탭 이름 정제 (이동 목적지 계산)
    current_tab = st.session_state.current_sheet
    
    # 순수 탭 이름 추출 (괄호나 브리핑 제거)
    base_tab = current_tab.replace("(종료)", "").replace("브리핑", "").strip()
    
    target_end_tab = f"{base_tab}(종료)"
    target_brief_tab = f"{base_tab}브리핑"
    
    ac1, ac2, ac3 = st.columns(3)
    
    # 1. 종료 처리
    with ac1:
        # 이미 종료 탭이면 이동 버튼 비활성화
        is_end_tab = "(종료)" in current_tab
        if st.button(f"🚀 선택 매물 종료 ({target_end_tab})", use_container_width=True, disabled=is_end_tab):
            # 실제 이동 전 확인 절차 (Warning Box)
            with st.status("🚀 데이터 이동 준비 중...", expanded=True) as status:
                st.write(f"선택한 {selected_count}건을 '{target_end_tab}' 시트로 이동합니다.")
                st.warning("⚠️ 이동 후 원본 시트에서는 삭제됩니다. 계속하시겠습니까?")
                # 여기서 실제 GSpread 업데이트 로직(Phase 3) 호출 예정
                # if st.button("확인 (Yes)"): ... 
                status.update(label="대기 중... (서비스 계정 연결 필요)", state="error")
            
    # 2. 브리핑 복사
    with ac2:
        # 이미 브리핑 탭이면 복사 버튼 비활성화
        is_brief_tab = "브리핑" in current_tab
        if st.button(f"📋 브리핑용 복사 ({target_brief_tab})", use_container_width=True, disabled=is_brief_tab):
            st.info(f"📢 [기능 준비 중] 선택된 {selected_count}건을 '{target_brief_tab}' 시트로 복사합니다.")
            
    # 3. 삭제
    with ac3:
        if st.button("🗑️ 매물 영구 삭제", type="primary", use_container_width=True):
            with st.status("🗑️ 삭제 진행 중...", expanded=True) as status:
                st.error(f"⚠️ [경고] 선택된 {selected_count}건이 영구 삭제됩니다. 복구할 수 없습니다.")
                status.update(label="삭제 대기 중 (서비스 계정 연결 필요)", state="error")

else:
    st.caption("👈 목록에서 '선택' 체크박스를 클릭하면 작업 버튼이 나타납니다.")
