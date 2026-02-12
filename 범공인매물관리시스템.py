import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.16)",
    layout="wide",
    initial_sidebar_state="expanded"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

# 💡 [핵심] 6개 시트 명칭 확정
SHEET_NAMES = ["임대", "임대(종료)", "매매", "매매(종료)", "임대브리핑", "매매브리핑"]

# [2. 스타일 설정]
st.markdown("""
    <style>
    .stButton button { min-height: 50px !important; font-size: 16px !important; font-weight: bold !important; }
    input[type=number] { min-height: 40px; }
    div[data-testid="stExpander"] details summary p { font-size: 1.1rem; font-weight: 600; }
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 로드 엔진 (매매/임대 통합 매핑 & 인코딩 방어)]
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    empty_df = pd.DataFrame()
    
    # 1. 데이터 읽기 (ASCII 에러 방어)
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
    except Exception:
        try:
            encoded_name = urllib.parse.quote(sheet_name)
            df = conn.read(spreadsheet=SHEET_URL, worksheet=encoded_name, ttl=0)
        except Exception:
            return empty_df

    # 2. 데이터 정제
    df.columns = df.columns.str.strip()
    
    # 3. 컬럼 매핑 (임대 + 매매 통합)
    mapping = {
        # 공통
        "지역_번지": "번지", "매물 특징": "내용", "해당층": "층", "매물 구분": "구분", 
        "건물명": "건물명", "관리비(만원)": "관리비",
        # 임대 관련
        "보증금(만원)": "보증금", "월차임(만원)": "월차임", "권리금_입금가(만원)": "권리금", "전용면적(평)": "면적",
        # 매매 관련
        "매매가(만원)": "매매가", "수익률(%)": "수익률", "대지면적(평)": "대지면적", "연면적(평)": "연면적"
    }
    df = df.rename(columns=mapping)
    df = df.fillna("") 
    
    # 4. 숫자형 데이터 안전 변환 (통합)
    numeric_cols = [
        "보증금", "월차임", "권리금", "관리비", "면적", "층", # 임대
        "매매가", "수익률", "대지면적", "연면적" # 매매
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 5. '선택' 컬럼 초기화
    if '선택' in df.columns: df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

# [A] 시트 관리 및 사이드바
if 'current_sheet' not in st.session_state:
    st.session_state.current_sheet = SHEET_NAMES[0]

with st.sidebar:
    st.header("📂 작업 공간 선택")
    
    try:
        current_idx = SHEET_NAMES.index(st.session_state.current_sheet)
    except ValueError:
        current_idx = 0
        
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES, index=current_idx)
    
    # 시트 변경 시: 캐시 삭제 -> 앱 재시작 (데이터 갱신)
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet 
        st.cache_data.clear()   
        st.rerun()              

    st.divider()
    
    # 초기화 버튼: 세션 충돌 방지 (Clean Reset)
    if st.button("🔄 검색 조건 초기화", type="primary", use_container_width=True):
        st.cache_data.clear()    
        st.session_state.clear() 
        st.rerun()               

    st.caption("Developed by Gemini & Pro-Mode")

# 데이터 불러오기
try:
    df_main = load_data(st.session_state.current_sheet)
    
    if df_main.empty:
        st.warning(f"⚠️ '{st.session_state.current_sheet}' 데이터를 불러올 수 없습니다. 탭 이름을 확인하세요.")
        st.stop()

    # ---------------------------------------------------------
    # [스마트 기본값 계산] (안전한 Getter)
    # ---------------------------------------------------------
    def get_safe_max(col, default=100.0):
        if col in df_main.columns and not df_main.empty:
            val = df_main[col].max()
            return float(val) if pd.notnull(val) else default
        return default

    # 현재 시트가 '매매' 관련인지 '임대' 관련인지 판단
    is_sale_mode = "매매" in st.session_state.current_sheet

    # ---------------------------------------------------------
    # [모듈 2: 조건부 필터 엔진 UI]
    # ---------------------------------------------------------
    with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
        # 1. 공통 검색 구역
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        with c1: 
            st.text_input("통합 검색", key='search_keyword', placeholder="내용, 건물명, 번지 등 전체 검색")
        with c2: 
            st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
        
        # 지역 선택 (컬럼 존재 시)
        unique_gu = ["전체"]
        if '지역_구' in df_main.columns:
            unique_gu += sorted(df_main['지역_구'].astype(str).unique().tolist())
            
        with c3: 
            if 'selected_gu_box' not in st.session_state: st.session_state.selected_gu_box = "전체"
            selected_gu = st.selectbox("지역 (구)", unique_gu, key='selected_gu_box')
            
        unique_dong = ["전체"]
        if '지역_동' in df_main.columns:
            if selected_gu == "전체":
                unique_dong += sorted(df_main['지역_동'].astype(str).unique().tolist())
            else:
                unique_dong += sorted(df_main[df_main['지역_구'] == selected_gu]['지역_동'].astype(str).unique().tolist())
                
        with c4: 
            if 'selected_dong_box' not in st.session_state: st.session_state.selected_dong_box = "전체"
            selected_dong = st.selectbox("지역 (동)", unique_dong, key='selected_dong_box')

        st.divider()

        # 2. 조건부 수치 입력 (매매 vs 임대)
        r1_col1, r1_col2, r1_col3 = st.columns(3)

        # Helper: 세션 값 가져오기
        def get_sess(key, default):
            if key not in st.session_state: st.session_state[key] = default
            return st.session_state[key]

        # [A] 매매 모드일 때 UI
        if is_sale_mode:
            max_price = get_safe_max("매매가", 100000.0)
            max_land = get_safe_max("대지면적", 100.0)
            max_total = get_safe_max("연면적", 200.0)
            
            with r1_col1:
                st.markdown("##### 💰 매매가 (단위: 만원)")
                c_d1, c_d2 = st.columns(2)
                c_d1.number_input("매매가(최소)", step=1000.0, key='min_price', value=get_sess('min_price', 0.0))
                c_d2.number_input("매매가(최대)", max_value=100000000.0, step=1000.0, key='max_price', value=get_sess('max_price', max_price))
            
            with r1_col2:
                st.markdown("##### 📊 수익률 & 층수")
                c_k1, c_k2 = st.columns(2)
                c_k1.number_input("수익률(최소)", step=0.1, key='min_yield', value=get_sess('min_yield', 0.0))
                c_k2.number_input("수익률(최대)", max_value=100.0, step=0.1, key='max_yield', value=get_sess('max_yield', 20.0))
                
                # 층수는 공통
                c_f1, c_f2 = st.columns(2)
                c_f1.number_input("층(최저)", min_value=-20.0, step=1.0, key='min_fl', value=get_sess('min_fl', -20.0))
                c_f2.number_input("층(최고)", max_value=200.0, step=1.0, key='max_fl', value=get_sess('max_fl', 100.0))

            with r1_col3:
                st.markdown("##### 📐 면적 (대지/연면적)")
                c_a1, c_a2 = st.columns(2)
                c_a1.number_input("대지(최소)", step=1.0, key='min_land', value=get_sess('min_land', 0.0))
                c_a2.number_input("대지(최대)", max_value=1000000.0, step=1.0, key='max_land', value=get_sess('max_land', max_land))
                
                c_b1, c_b2 = st.columns(2)
                c_b1.number_input("연면(최소)", step=1.0, key='min_total', value=get_sess('min_total', 0.0))
                c_b2.number_input("연면(최대)", max_value=1000000.0, step=1.0, key='max_total', value=get_sess('max_total', max_total))

        # [B] 임대 모드일 때 UI (기존 유지)
        else:
            max_dep = get_safe_max("보증금", 10000.0)
            max_rent = get_safe_max("월차임", 500.0)
            max_area = get_safe_max("면적", 100.0)
            
            with r1_col1:
                st.markdown("##### 💰 임대 조건 (만원)")
                c_d1, c_d2 = st.columns(2)
                c_d1.number_input("보증금(최소)", step=500.0, key='min_dep', value=get_sess('min_dep', 0.0))
                c_d2.number_input("보증금(최대)", max_value=100000000.0, step=500.0, key='max_dep', value=get_sess('max_dep', max_dep))
                
                c_r1, c_r2 = st.columns(2)
                c_r1.number_input("월세(최소)", step=10.0, key='min_rent', value=get_sess('min_rent', 0.0))
                c_r2.number_input("월세(최대)", max_value=10000000.0, step=10.0, key='max_rent', value=get_sess('max_rent', max_rent))

            with r1_col2:
                st.markdown("##### 🔑 권리금/관리비")
                is_no_kwon = st.checkbox("무권리 매물만 보기", key='is_no_kwon', value=get_sess('is_no_kwon', False))
                c_k1, c_k2 = st.columns(2)
                c_k1.number_input("권리금(최소)", step=100.0, key='min_kwon', disabled=is_no_kwon, value=get_sess('min_kwon', 0.0))
                c_k2.number_input("권리금(최대)", max_value=100000000.0, step=100.0, key='max_kwon', disabled=is_no_kwon, value=get_sess('max_kwon', 50000.0))

                c_m1, c_m2 = st.columns(2)
                c_m1.number_input("관리비(최소)", step=5.0, key='min_man', value=get_sess('min_man', 0.0))
                c_m2.number_input("관리비(최대)", max_value=1000000.0, step=5.0, key='max_man', value=get_sess('max_man', 1000.0))

            with r1_col3:
                st.markdown("##### 📐 면적/층수")
                c_a1, c_a2 = st.columns(2)
                c_a1.number_input("면적(최소)", step=5.0, key='min_area', value=get_sess('min_area', 0.0))
                c_a2.number_input("면적(최대)", max_value=1000000.0, step=5.0, key='max_area', value=get_sess('max_area', max_area))
                
                c_f1, c_f2 = st.columns(2)
                c_f1.number_input("층(최저)", min_value=-20.0, step=1.0, key='min_fl', value=get_sess('min_fl', -20.0))
                c_f2.number_input("층(최고)", max_value=200.0, step=1.0, key='max_fl', value=get_sess('max_fl', 100.0))

    # ---------------------------------------------------------
    # [지능형 필터링 로직: 컬럼 존재 여부 확인 필수]
    # ---------------------------------------------------------
    df_filtered = df_main.copy()

    # 1. 지역
    if selected_gu != "전체" and '지역_구' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['지역_구'] == selected_gu]
    if selected_dong != "전체" and '지역_동' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['지역_동'] == selected_dong]

    # 2. 번지
    if st.session_state.exact_bunji and '번지' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]

    # 3. 수치 필터 (매매 vs 임대 분기 처리)
    if is_sale_mode:
        if '매매가' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
        if '수익률' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['수익률'] >= st.session_state.min_yield) & (df_filtered['수익률'] <= st.session_state.max_yield)]
        if '대지면적' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land) & (df_filtered['대지면적'] <= st.session_state.max_land)]
        if '연면적' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['연면적'] >= st.session_state.min_total) & (df_filtered['연면적'] <= st.session_state.max_total)]
    else:
        # 임대 필터
        if '보증금' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
        if '월차임' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        if '면적' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
        if '관리비' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['관리비'] >= st.session_state.min_man) & (df_filtered['관리비'] <= st.session_state.max_man)]
        if '권리금' in df_filtered.columns:
            if is_no_kwon:
                df_filtered = df_filtered[df_filtered['권리금'] == 0]
            else:
                df_filtered = df_filtered[(df_filtered['권리금'] >= st.session_state.min_kwon) & (df_filtered['권리금'] <= st.session_state.max_kwon)]

    # 공통 층수 필터
    if '층' in df_filtered.columns:
         df_filtered = df_filtered[(df_filtered['층'] >= st.session_state.min_fl) & (df_filtered['층'] <= st.session_state.max_fl)]

    # ---------------------------------------------------------
    # [핵심] 슈퍼 옴니 서치 (Super Omni Search)
    # ---------------------------------------------------------
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        search_scope = df_filtered.drop(columns=['선택'], errors='ignore')
        # 모든 데이터를 문자로 변환 -> 하나로 합침 -> 검색
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]

    # ---------------------------------------------------------
    # [결과 출력 & 리스트 뷰]
    # ---------------------------------------------------------
    if len(df_filtered) == 0:
        st.warning(f"🔍 '{st.session_state.current_sheet}' 시트에서 조건에 맞는 매물을 찾을 수 없습니다.")
    else:
        st.info(f"📋 **{st.session_state.current_sheet}** 검색 결과: **{len(df_filtered)}**건 (전체 {len(df_main)}건)")
    
    # 리스트 수정 방지 (Read-only)
    disabled_cols = [col for col in df_filtered.columns if col != '선택']
    
    # 키 충돌 방지를 위한 유니크 키 생성
    editor_key = f"editor_{st.session_state.current_sheet}"
    
    #  - 데이터 에디터 시각화
    st.data_editor(
        df_filtered,
        disabled=disabled_cols,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "선택": st.column_config.CheckboxColumn(width="small"),
            "매매가": st.column_config.NumberColumn("매매가(만)", format="%d"),
            "보증금": st.column_config.NumberColumn("보증금(만)", format="%d"),
            "월차임": st.column_config.NumberColumn("월세(만)", format="%d"),
            "권리금": st.column_config.NumberColumn("권리금(만)", format="%d"),
            "면적": st.column_config.NumberColumn("면적(평)", format="%.1f"),
            "대지면적": st.column_config.NumberColumn("대지(평)", format="%.1f"),
            "연면적": st.column_config.NumberColumn("연면(평)", format="%.1f"),
            "수익률": st.column_config.NumberColumn("수익률", format="%.2f%%"),
            "내용": st.column_config.TextColumn("특징", width="large"),
        },
        key=editor_key
    )

except Exception as e:
    st.error(f"🚨 시스템 에러: {e}")
    st.write("잠시 후 다시 시도하거나, [검색 조건 초기화] 버튼을 눌러주세요.")
