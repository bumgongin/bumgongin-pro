import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.15)",
    layout="wide",
    initial_sidebar_state="expanded"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

# 💡 [핵심] 사장님 요청 7개 시트 실명칭 100% 반영
SHEET_NAMES = ["임대", "임대(종료)", "매매", "매매(종료)", "매매브리핑", "임대브리핑", "스케줄"]

# [2. 스타일 설정]
st.markdown("""
    <style>
    .stButton button { min-height: 50px !important; font-size: 16px !important; font-weight: bold !important; }
    input[type=number] { min-height: 40px; }
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 24px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [3. 데이터 로드 엔진 (방어 로직 강화)]
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 빈 데이터프레임 생성 (에러 방지용)
    empty_df = pd.DataFrame()
    
    try:
        # 1차 시도
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
    except Exception:
        try:
            # 2차 시도: URL 인코딩
            encoded_name = urllib.parse.quote(sheet_name)
            df = conn.read(spreadsheet=SHEET_URL, worksheet=encoded_name, ttl=0)
        except Exception:
            return empty_df

    # 데이터 정제
    df.columns = df.columns.str.strip()
    
    # 컬럼명 매핑
    mapping = {
        "보증금(만원)": "보증금", "월차임(만원)": "월차임", "권리금_입금가(만원)": "권리금",
        "전용면적(평)": "면적", "매물 특징": "내용", "지역_번지": "번지",
        "관리비(만원)": "관리비", "해당층": "층", "매물 구분": "구분", "건물명": "건물명"
    }
    df = df.rename(columns=mapping)
    df = df.fillna("") 
    
    # 숫자형 데이터 안전 변환 (컬럼이 존재할 때만 변환)
    numeric_cols = ["보증금", "월차임", "면적", "권리금", "관리비", "층"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # '선택' 컬럼 초기화
    if '선택' in df.columns: df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    
    return df

# [4. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

# [A] 데이터 로드 및 시트 관리
if 'current_sheet' not in st.session_state:
    st.session_state.current_sheet = SHEET_NAMES[0]

with st.sidebar:
    st.header("📂 작업 공간 선택")
    
    # 시트 선택 (인덱스 에러 방지)
    try:
        current_idx = SHEET_NAMES.index(st.session_state.current_sheet)
    except ValueError:
        current_idx = 0
        
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES, index=current_idx)
    
    # 시트 변경 감지 -> 즉시 리프레시
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet 
        st.cache_data.clear()   
        st.rerun()              

    st.divider()
    
    # [수정된 초기화 버튼] 에러 원천 차단 (단순화)
    if st.button("🔄 검색 조건 초기화", type="primary", use_container_width=True):
        st.cache_data.clear()    # 데이터 갱신
        st.session_state.clear() # 모든 세션 변수 삭제 (필터 초기화)
        st.rerun()               # 앱 재시작

    st.caption("Developed by Gemini & Pro-Mode")

# 데이터 불러오기
try:
    df_main = load_data(st.session_state.current_sheet)
    
    if df_main.empty:
        st.warning(f"⚠️ '{st.session_state.current_sheet}' 시트를 불러오지 못했습니다. 탭 이름을 확인하거나 데이터가 있는지 확인해주세요.")
        st.stop()

    # ---------------------------------------------------------
    # [스마트 기본값 계산] (안전한 Getter 함수 사용)
    # ---------------------------------------------------------
    def get_safe_max(col, default=100.0):
        # 컬럼이 존재하고 데이터가 있을 때만 최대값 반환, 아니면 기본값
        if col in df_main.columns and not df_main.empty:
            val = df_main[col].max()
            return float(val) if pd.notnull(val) else default
        return default

    # 각 필터별 최대값 계산 (컬럼 없으면 기본값으로 설정되어 에러 방지)
    max_vals = {
        'dep': get_safe_max("보증금", 10000.0),
        'rent': get_safe_max("월차임", 500.0),
        'kwon': get_safe_max("권리금", 5000.0),
        'man': get_safe_max("관리비", 50.0),
        'area': get_safe_max("면적", 100.0),
        'fl': get_safe_max("층", 50.0)
    }
    
    LIMIT_HUGE = 100000000.0 
    LIMIT_RENT = 1000000.0

    # ---------------------------------------------------------
    # [모듈 2: 필터 엔진 UI]
    # ---------------------------------------------------------
    with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
        # 1. 텍스트 검색
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        with c1: 
            st.text_input("통합 검색", key='search_keyword', placeholder="내용, 건물명, 번지, 메모 등 전체 검색")
        with c2: 
            st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
        
        # 2. 지역 선택 (컬럼 존재 여부 체크)
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

        # 3. 수치 입력 (세션 상태 활용)
        r1_col1, r1_col2, r1_col3 = st.columns(3)

        # 초기값 설정을 위한 Helper
        def get_sess(key, default):
            if key not in st.session_state: st.session_state[key] = default
            return st.session_state[key]

        with r1_col1:
            st.markdown("##### 💰 금액 조건 (단위: 만원)")
            c_d1, c_d2 = st.columns(2)
            c_d1.number_input("보증금(최소)", step=1000.0, key='min_dep', value=get_sess('min_dep', 0.0))
            c_d2.number_input("보증금(최대)", max_value=LIMIT_HUGE, step=1000.0, key='max_dep', value=get_sess('max_dep', max_vals['dep']))
            
            c_r1, c_r2 = st.columns(2)
            c_r1.number_input("월세(최소)", step=100.0, key='min_rent', value=get_sess('min_rent', 0.0))
            c_r2.number_input("월세(최대)", max_value=LIMIT_RENT, step=100.0, key='max_rent', value=get_sess('max_rent', max_vals['rent']))

        with r1_col2:
            st.markdown("##### 🔑 권리금/관리비")
            is_no_kwon = st.checkbox("무권리 매물만 보기", key='is_no_kwon', value=get_sess('is_no_kwon', False))
            c_k1, c_k2 = st.columns(2)
            c_k1.number_input("권리금(최소)", step=500.0, key='min_kwon', disabled=is_no_kwon, value=get_sess('min_kwon', 0.0))
            c_k2.number_input("권리금(최대)", max_value=LIMIT_HUGE, step=500.0, key='max_kwon', disabled=is_no_kwon, value=get_sess('max_kwon', max_vals['kwon']))

            c_m1, c_m2 = st.columns(2)
            # 관리비 컬럼이 없어도 UI는 유지하되, 필터링에서 제외 (에러 방지)
            c_m1.number_input("관리비(최소)", step=5.0, key='min_man', value=get_sess('min_man', 0.0))
            c_m2.number_input("관리비(최대)", max_value=LIMIT_RENT, step=5.0, key='max_man', value=get_sess('max_man', max_vals['man']))

        with r1_col3:
            st.markdown("##### 📐 면적/층수")
            c_a1, c_a2 = st.columns(2)
            c_a1.number_input("면적(최소)", step=10.0, key='min_area', value=get_sess('min_area', 0.0))
            c_a2.number_input("면적(최대)", max_value=LIMIT_HUGE, step=10.0, key='max_area', value=get_sess('max_area', max_vals['area']))
            
            c_f1, c_f2 = st.columns(2)
            c_f1.number_input("층(최저)", min_value=-20.0, step=1.0, key='min_fl', value=get_sess('min_fl', -20.0))
            c_f2.number_input("층(최고)", max_value=100.0, step=1.0, key='max_fl', value=get_sess('max_fl', max_vals['fl']))

    # ---------------------------------------------------------
    # [필터링 로직: 컬럼 존재 여부 확인 필수]
    # ---------------------------------------------------------
    df_filtered = df_main.copy()

    # 1. 지역 (컬럼 있을 때만)
    if selected_gu != "전체" and '지역_구' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['지역_구'] == selected_gu]
    if selected_dong != "전체" and '지역_동' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['지역_동'] == selected_dong]

    # 2. 번지 (정밀)
    if st.session_state.exact_bunji and '번지' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]

    # 3. 수치 범위 (각 컬럼이 존재하는지 체크 후 필터링 -> 에러 원천 차단)
    if '보증금' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
    
    if '월차임' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        
    if '면적' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
        
    # [수정] 관리비 에러 해결: 컬럼 있을 때만 필터 적용
    if '관리비' in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered['관리비'] >= st.session_state.min_man) & (df_filtered['관리비'] <= st.session_state.max_man)]
        
    if '층' in df_filtered.columns:
         df_filtered = df_filtered[(df_filtered['층'] >= st.session_state.min_fl) & (df_filtered['층'] <= st.session_state.max_fl)]

    # 4. 권리금
    if '권리금' in df_filtered.columns:
        if is_no_kwon:
            df_filtered = df_filtered[df_filtered['권리금'] == 0]
        else:
            df_filtered = df_filtered[(df_filtered['권리금'] >= st.session_state.min_kwon) & (df_filtered['권리금'] <= st.session_state.max_kwon)]

    # ---------------------------------------------------------
    # [핵심] 슈퍼 옴니 서치 (Super Omni Search)
    # ---------------------------------------------------------
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        # '선택' 컬럼은 제외
        search_scope = df_filtered.drop(columns=['선택'], errors='ignore')
        
        # [수정] 모든 데이터를 문자열로 변환하여 안전하게 검색 (숫자, 날짜 포함)
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        
        df_filtered = df_filtered[mask]

    # ---------------------------------------------------------
    # [결과 출력]
    # ---------------------------------------------------------
    if len(df_filtered) == 0:
        st.warning(f"🔍 '{st.session_state.current_sheet}' 시트에서 조건에 맞는 매물을 찾을 수 없습니다.")
    else:
        st.info(f"📋 **{st.session_state.current_sheet}** 탭 검색 결과: **{len(df_filtered)}**건 (전체 {len(df_main)}건)")
    
    # ---------------------------------------------------------
    # [핵심] 리스트 수정 방지 (Read-only)
    # ---------------------------------------------------------
    disabled_cols = [col for col in df_filtered.columns if col != '선택']
    
    # key에 시트명을 넣어 강제 리프레시 (시트 전환 시 UI 꼬임 방지)
    editor_key = f"editor_{st.session_state.current_sheet}"
    
    st.data_editor(
        df_filtered,
        disabled=disabled_cols, # '선택' 빼고 전부 수정 불가
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "선택": st.column_config.CheckboxColumn(width="small"),
            "보증금": st.column_config.NumberColumn("보증금", format="%d만"),
            "월차임": st.column_config.NumberColumn("월세", format="%d만"),
            "권리금": st.column_config.NumberColumn("권리금", format="%d만"),
            "면적": st.column_config.NumberColumn("면적", format="%.1f평"),
            "층": st.column_config.NumberColumn("층", format="%d층"),
            "내용": st.column_config.TextColumn("특징", width="large"),
        },
        key=editor_key
    )

except Exception as e:
    st.error(f"🚨 시스템 에러: {e}")
    st.write("잠시 후 다시 시도하거나, [검색 조건 초기화] 버튼을 눌러주세요.")
