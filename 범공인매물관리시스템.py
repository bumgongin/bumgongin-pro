import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# [1. 시스템 설정]
st.set_page_config(
    page_title="범공인 Pro (v24.15)",
    layout="wide",
    initial_sidebar_state="expanded"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"

# 💡 [핵심] 사장님 요청에 맞춘 6개 시트 확장 (실제 탭 이름과 일치해야 함)
SHEET_NAMES = ["임대", "매매", "상가", "토지", "공장", "종료"]

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

# [3. 유틸리티: 명시적(Explicit) 초기화 함수]
# 시트가 바뀌거나 초기화 버튼 클릭 시, 해당 시트의 데이터 범위에 맞춰 필터를 리셋
def reset_all_filters(defaults):
    # 텍스트 입력창 초기화
    st.session_state['search_keyword'] = ""
    st.session_state['exact_bunji'] = ""
    
    # 셀렉트박스 초기화
    st.session_state['selected_gu_box'] = "전체"
    st.session_state['selected_dong_box'] = "전체"
    
    # 숫자형 필터 초기화 (범위: Min=0, Max=현재 시트 데이터의 최대값)
    st.session_state['min_dep'] = 0.0
    st.session_state['max_dep'] = defaults['max_dep']
    st.session_state['min_rent'] = 0.0
    st.session_state['max_rent'] = defaults['max_rent']
    st.session_state['min_kwon'] = 0.0
    st.session_state['max_kwon'] = defaults['max_kwon']
    st.session_state['min_man'] = 0.0
    st.session_state['max_man'] = defaults['max_man']
    st.session_state['min_area'] = 0.0
    st.session_state['max_area'] = defaults['max_area']
    st.session_state['min_fl'] = -20.0 # 지하 20층까지 검색 가능
    st.session_state['max_fl'] = defaults['max_fl']
    
    # 체크박스 초기화
    st.session_state['is_no_kwon'] = False

# [4. 데이터 로드 엔진]
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # worksheet 파라미터로 해당 탭의 데이터를 읽어옴
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
    except Exception:
        # 에러 발생 시 (탭 이름 불일치 등) 기본 동작
        st.warning(f"⚠️ '{sheet_name}' 탭을 찾을 수 없어 기본 데이터를 로드합니다.")
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        
    df.columns = df.columns.str.strip()
    
    # 컬럼명 매핑 (유연한 처리를 위해 핵심 컬럼 위주로 매핑)
    mapping = {
        "보증금(만원)": "보증금", "월차임(만원)": "월차임", "권리금_입금가(만원)": "권리금",
        "전용면적(평)": "면적", "매물 특징": "내용", "지역_번지": "번지",
        "관리비(만원)": "관리비", "해당층": "층", "매물 구분": "구분", "건물명": "건물명"
    }
    df = df.rename(columns=mapping)
    df = df.fillna("") 
    
    # 숫자형 데이터 안전 변환 (오류 발생 시 0으로 처리)
    numeric_cols = ["보증금", "월차임", "면적", "권리금", "관리비", "층"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # '선택' 컬럼 초기화 (기존에 있으면 삭제 후 재생성)
    if '선택' in df.columns: df = df.drop(columns=['선택'])
    df.insert(0, '선택', False)
    return df

# [5. 메인 실행 로직]
st.title("🏙️ 범공인 매물장 (Pro)")

# [A] 데이터 로드 및 시트 관리
# 세션에 현재 시트 정보가 없으면 첫 번째 시트로 초기화
if 'current_sheet' not in st.session_state:
    st.session_state.current_sheet = SHEET_NAMES[0]

with st.sidebar:
    st.header("📂 작업 공간 선택")
    
    # 시트 선택 (UI)
    # index를 세션 상태와 일치시켜 UI 잔상 방지
    try:
        current_idx = SHEET_NAMES.index(st.session_state.current_sheet)
    except ValueError:
        current_idx = 0
        
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES, index=current_idx)
    
    # [핵심] 시트 변경 감지 및 로직 실행
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet # 상태 업데이트
        st.cache_data.clear()   # 이전 시트 데이터 캐시 삭제 (중요)
        st.rerun()              # 앱 재시작하여 새 데이터 로드

    st.divider()
    
    # 리셋 버튼
    reset_clicked = st.button("🔄 검색 조건 초기화", type="primary", use_container_width=True)
    
    st.caption("Developed by Gemini & Pro-Mode")

# 데이터 불러오기
try:
    df_main = load_data(st.session_state.current_sheet)

    # ---------------------------------------------------------
    # [스마트 기본값 계산]
    # 시트가 바뀔 때마다 해당 데이터의 최대값을 계산하여 필터 범위(defaults)를 설정
    # ---------------------------------------------------------
    def get_max_val(col):
        if col in df_main.columns and not df_main.empty:
            return float(df_main[col].max())
        return 0.0

    defaults = {
        'max_dep': get_max_val("보증금") if get_max_val("보증금") > 0 else 10000.0,
        'max_rent': get_max_val("월차임") if get_max_val("월차임") > 0 else 500.0,
        'max_kwon': get_max_val("권리금") if get_max_val("권리금") > 0 else 5000.0,
        'max_man': get_max_val("관리비") if get_max_val("관리비") > 0 else 50.0,
        'max_area': get_max_val("면적") if get_max_val("면적") > 0 else 100.0,
        'max_fl': get_max_val("층") if get_max_val("층") > 0 else 50.0
    }
    
    # 입력 가능한 절대 한계치 (1조 원)
    LIMIT_HUGE = 100000000.0 
    LIMIT_RENT = 1000000.0

    # [리셋 버튼 동작]
    # 버튼 클릭 또는 앱 최초 실행 시(검색어 키가 없을 때) 초기화 수행
    if reset_clicked or 'search_keyword' not in st.session_state:
        reset_all_filters(defaults)
        if reset_clicked:
            st.rerun()

    # ---------------------------------------------------------
    # [모듈 2: 필터 엔진] (UI 바인딩)
    # ---------------------------------------------------------
    with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
        # 1. 텍스트 검색
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        with c1: 
            st.text_input("통합 검색", key='search_keyword', placeholder="모든 항목 검색 (비고, 연락처, 메모 포함)")
        with c2: 
            st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
        
        # 2. 지역 선택 (데이터 기반 동적 생성)
        unique_gu = ["전체"] + sorted(df_main['지역_구'].unique().tolist())
        with c3: 
            # 세션 값이 현재 리스트에 없으면 '전체'로 안전하게 변경
            if st.session_state.selected_gu_box not in unique_gu:
                st.session_state.selected_gu_box = "전체"
            selected_gu = st.selectbox("지역 (구)", unique_gu, key='selected_gu_box')
            
        if selected_gu == "전체":
            unique_dong = ["전체"] + sorted(df_main['지역_동'].unique().tolist())
        else:
            unique_dong = ["전체"] + sorted(df_main[df_main['지역_구'] == selected_gu]['지역_동'].unique().tolist())
            
        with c4: 
            if st.session_state.selected_dong_box not in unique_dong:
                st.session_state.selected_dong_box = "전체"
            selected_dong = st.selectbox("지역 (동)", unique_dong, key='selected_dong_box')

        st.divider()

        # 3. 수치 입력 (세션 상태와 완벽 동기화)
        r1_col1, r1_col2, r1_col3 = st.columns(3)

        with r1_col1:
            st.markdown("##### 💰 금액 조건 (단위: 만원)")
            c_d1, c_d2 = st.columns(2)
            c_d1.number_input("보증금(최소)", step=1000.0, key='min_dep')
            c_d2.number_input("보증금(최대)", max_value=LIMIT_HUGE, step=1000.0, key='max_dep')
            
            c_r1, c_r2 = st.columns(2)
            c_r1.number_input("월세(최소)", step=100.0, key='min_rent')
            c_r2.number_input("월세(최대)", max_value=LIMIT_RENT, step=100.0, key='max_rent')

        with r1_col2:
            st.markdown("##### 🔑 권리금/관리비")
            is_no_kwon = st.checkbox("무권리 매물만 보기", key='is_no_kwon')
            c_k1, c_k2 = st.columns(2)
            c_k1.number_input("권리금(최소)", step=500.0, key='min_kwon', disabled=is_no_kwon)
            c_k2.number_input("권리금(최대)", max_value=LIMIT_HUGE, step=500.0, key='max_kwon', disabled=is_no_kwon)

            c_m1, c_m2 = st.columns(2)
            c_m1.number_input("관리비(최소)", step=5.0, key='min_man')
            c_m2.number_input("관리비(최대)", max_value=LIMIT_RENT, step=5.0, key='max_man')

        with r1_col3:
            st.markdown("##### 📐 면적/층수")
            c_a1, c_a2 = st.columns(2)
            c_a1.number_input("면적(최소)", step=10.0, key='min_area')
            c_a2.number_input("면적(최대)", max_value=LIMIT_HUGE, step=10.0, key='max_area')
            
            c_f1, c_f2 = st.columns(2)
            c_f1.number_input("층(최저)", min_value=-20.0, step=1.0, key='min_fl')
            c_f2.number_input("층(최고)", max_value=100.0, step=1.0, key='max_fl')

    # ---------------------------------------------------------
    # [필터링 로직: 안전성 & 범위 확장]
    # ---------------------------------------------------------
    df_filtered = df_main.copy()

    # 1. 지역
    if selected_gu != "전체":
        df_filtered = df_filtered[df_filtered['지역_구'] == selected_gu]
    if selected_dong != "전체":
        df_filtered = df_filtered[df_filtered['지역_동'] == selected_dong]

    # 2. 번지 (정밀)
    if st.session_state.exact_bunji:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]

    # 3. 수치 범위
    df_filtered = df_filtered[
        (df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep) &
        (df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent) &
        (df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area) &
        (df_filtered['관리비'] >= st.session_state.min_man) & (df_filtered['관리비'] <= st.session_state.max_man)
    ]
    
    if '층' in df_filtered.columns:
         df_filtered = df_filtered[
            (df_filtered['층'] >= st.session_state.min_fl) & (df_filtered['층'] <= st.session_state.max_fl)
         ]

    # 4. 권리금
    if is_no_kwon:
        df_filtered = df_filtered[df_filtered['권리금'] == 0]
    else:
        df_filtered = df_filtered[
            (df_filtered['권리금'] >= st.session_state.min_kwon) & (df_filtered['권리금'] <= st.session_state.max_kwon)
        ]

    # ---------------------------------------------------------
    # [핵심] 슈퍼 옴니 서치 (Super Omni Search)
    # ---------------------------------------------------------
    search_val = st.session_state.search_keyword.strip() # 공백 제거 전처리
    if search_val:
        # '선택' 컬럼은 제외하고 나머지 모든 컬럼을 대상으로 함
        search_scope = df_filtered.drop(columns=['선택'], errors='ignore')
        
        # 모든 컬럼을 문자열로 변환하고 가로로 합침(join) -> 해당 문자열에 검색어가 있는지 확인
        # 이 방식을 사용하면 '비고', '연락처' 등 화면에 안 보이는 컬럼도 모두 검색됨
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
    # '선택' 컬럼을 제외한 모든 컬럼을 비활성화(disabled) 처리
    # ---------------------------------------------------------
    disabled_cols = [col for col in df_filtered.columns if col != '선택']
    
    # key에 시트명을 넣어 강제 리프레시 (시트 전환 시 잔상 제거)
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
