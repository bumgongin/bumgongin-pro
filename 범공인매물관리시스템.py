import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import time
import uuid

# [MODULE: SYSTEM SETUP]
# 1. 시스템 설정
st.set_page_config(
    page_title="범공인 Pro (v24.19.2)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [MODULE: STYLES & CSS]
# 2. 스타일 설정 (모바일 터치 최적화 & 깜빡임 방지)
st.markdown("""
    <style>
    /* 버튼 크기 및 터치 영역 확보 */
    .stButton button { 
        min-height: 50px !important; 
        font-size: 16px !important; 
        font-weight: bold !important; 
        width: 100%;
        border-radius: 8px;
    }
    
    /* 입력창 높이 확보 */
    input[type=number], input[type=text] { 
        min-height: 45px !important; 
        font-size: 16px !important; 
    }
    
    /* 셀렉트박스 터치 개선 */
    div[data-baseweb="select"] > div {
        min-height: 45px !important;
    }
    
    /* Expander 헤더 크기 증가 */
    div[data-testid="stExpander"] details summary p { 
        font-size: 1.1rem; 
        font-weight: 600; 
        padding: 10px 0;
    }
    
    /* 액션 버튼 스타일 구분 */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] { 
        border: 1px solid #e0e0e0; 
    }

    /* 모바일 리스트 폰트 및 높이 조정 */
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 14px !important; }
        h1 { font-size: 22px !important; }
        div[data-testid="column"] { margin-bottom: 8px; }
        /* 모바일에서 필터박스 간격 확보 */
        div.stSelectbox { margin-bottom: 5px; }
    }
    </style>
""", unsafe_allow_html=True)

# [MODULE: CONSTANTS]
# 3. 상수 및 매핑 (변수명 통합)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU"
SHEET_GIDS = {
    "임대": "2063575964", 
    "임대(종료)": "791354475", 
    "매매": "1833762712", 
    "매매(종료)": "1597438389",
    "임대브리핑": "982780192", 
    "매매브리핑": "807085458"
}
SHEET_NAMES = list(SHEET_GIDS.keys())

# [MODULE: UTILITIES]
# 4. 유틸리티 함수
def safe_reset():
    """세션 상태를 안전하게 초기화하고 앱을 리로드합니다."""
    for key in list(st.session_state.keys()):
        if key != 'current_sheet':
            del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

def standardize_columns(df):
    """헤더 공백 제거 및 표준명 매핑"""
    df.columns = df.columns.str.replace(' ', '').str.strip()
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
    return df

# [MODULE: DATA ENGINE]
# 5. 데이터 로드 엔진
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    
    # URL 통합 사용
    csv_url = f"{SHEET_URL}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(csv_url)
    except Exception:
        return None

    df = standardize_columns(df)

    # [수치 변환] 콤마, 지수 등 처리
    numeric_candidates = ["보증금", "월차임", "권리금", "관리비", "면적", "층", "매매가", "수익률", "대지면적", "연면적"]
    
    for col in numeric_candidates:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(',', ''), 
                errors='coerce'
            ).fillna(0)
    
    df = df.fillna("") 

    # IronID 생성 (내부 식별용)
    if '선택' in df.columns: df = df.drop(columns=['선택'])
    if 'IronID' in df.columns: df = df.drop(columns=['IronID'])
    
    df['IronID'] = [str(uuid.uuid4()) for _ in range(len(df))]
    df.insert(0, '선택', False)
    
    return df

# [MODULE: UPDATE ENGINE]
# 6. 데이터 쓰기 엔진 (정밀 매칭 강화)
def update_data(action_type, target_rows, source_sheet, target_sheet=None):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception:
        return False, "❌ 서비스 계정 연결 실패. secrets 설정을 확인하세요."
    
    try:
        # 1. 원본 데이터 확보
        src_df = conn.read(spreadsheet=SHEET_URL, worksheet=source_sheet, ttl=0)
        src_df = standardize_columns(src_df)
        
        # '선택' 및 'IronID' 제거
        target_rows_clean = target_rows.drop(columns=['선택', 'IronID'], errors='ignore')
        
        # 2. 정밀 매칭 (복합 키 + 내용 앞부분)
        match_cols = ['번지', '층', '면적', '보증금', '매매가', '월차임', '내용']
        valid_keys = [k for k in match_cols if k in src_df.columns and k in target_rows_clean.columns]
        
        if not valid_keys:
            return False, "❌ 데이터 식별 실패: 고유값 컬럼이 부족합니다."

        # 매칭용 임시 키 생성 함수
        def prepare_match_key(df):
            temp_df = df.copy()
            for k in valid_keys:
                # 내용은 앞 10글자만 따서 비교 (줄바꿈/공백 차이 완화)
                if k == '내용':
                    temp_df[k] = temp_df[k].astype(str).str.replace(r'\s+', '', regex=True).str[:10]
                else:
                    temp_df[k] = temp_df[k].astype(str).str.replace(',', '').str.strip()
            return temp_df

        src_prep = prepare_match_key(src_df)
        tgt_prep = prepare_match_key(target_rows_clean)
        
        # 3. 로직 분기
        if action_type == "delete" or action_type == "move":
            # 병합하여 삭제 대상 식별
            merged = src_prep.merge(
                tgt_prep[valid_keys], 
                on=valid_keys, 
                how='left', 
                indicator=True
            )
            
            # _merge == 'left_only' 인 행들만 남김 (삭제 대상 제외)
            rows_to_keep_mask = merged['_merge'] == 'left_only'
            new_src_df = src_df[rows_to_keep_mask]
            
            # 변화가 없으면 매칭 실패
            if len(new_src_df) == len(src_df):
                return False, "❌ 일치하는 데이터를 찾지 못했습니다. (데이터가 이미 변경되었을 수 있음)"

            # 이동: 타겟에 추가
            if action_type == "move" and target_sheet:
                tgt_df_remote = conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0)
                tgt_df_remote = standardize_columns(tgt_df_remote)
                new_tgt_df = pd.concat([tgt_df_remote, target_rows_clean], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt_df)
            
            # 원본 업데이트 (삭제)
            conn.update(spreadsheet=SHEET_URL, worksheet=source_sheet, data=new_src_df)
            action_name = "이동" if action_type == "move" else "삭제"
            return True, f"✅ {len(target_rows)}건 {action_name} 완료!"

        elif action_type == "copy":
            if not target_sheet: return False, "❌ 타겟 시트 오류"
            tgt_df_remote = conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0)
            tgt_df_remote = standardize_columns(tgt_df_remote)
            new_tgt_df = pd.concat([tgt_df_remote, target_rows_clean], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt_df)
            return True, f"✅ {len(target_rows)}건 복사 완료!"

        return False, "❌ 알 수 없는 작업"

    except Exception as e:
        return False, f"🚨 실행 오류: {str(e)}"

# [MODULE: MAIN UI]
# 7. 메인 인터페이스
st.title("🏙️ 범공인 매물장 (Pro)")

if 'current_sheet' not in st.session_state: st.session_state.current_sheet = SHEET_NAMES[0]
if 'action_status' not in st.session_state: st.session_state.action_status = None 

with st.sidebar:
    st.header("📂 작업 공간 선택")
    try: curr_idx = SHEET_NAMES.index(st.session_state.current_sheet)
    except: curr_idx = 0
    selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES, index=curr_idx)
    
    if selected_sheet != st.session_state.current_sheet:
        st.session_state.current_sheet = selected_sheet
        st.session_state.action_status = None 
        st.cache_data.clear()
        st.rerun()

    st.divider()
    if st.button("🔄 검색 조건 초기화", type="primary", use_container_width=True):
        safe_reset()
    st.caption("Developed by Gemini & Pro-Mode")

# 데이터 로드
df_main = load_data(st.session_state.current_sheet)
if df_main is None:
    st.error(f"🚨 '{st.session_state.current_sheet}' 로드 실패. GID를 확인하세요.")
    st.stop()

# [MODULE: FRAGMENT UI]
# 8. 메인 프래그먼트 (깜빡임 방지 핵심)
@st.fragment
def main_interface():
    # Helper Functions
    def get_max_if_exists(col):
        if col in df_main.columns and not df_main.empty:
            val = df_main[col].max()
            return float(val) if pd.notnull(val) and val > 0 else 0.0 # Fix: NaN/Empty -> 0.0
        return 0.0

    def sess(key, default):
        if key not in st.session_state: st.session_state[key] = default
        return st.session_state[key]

    is_sale_mode = "매매" in st.session_state.current_sheet

    # --- FILTER SECTION ---
    with st.expander("🔍 정밀 검색 및 제어판 (열기/닫기)", expanded=True):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 1])
        with c1: st.text_input("통합 검색", key='search_keyword', placeholder="내용, 건물명, 번지 등")
        with c2: st.text_input("번지 정밀검색", key='exact_bunji', placeholder="예: 50-1")
        
        with c3:
            unique_cat = ["전체"]
            if '구분' in df_main.columns: unique_cat += sorted(df_main['구분'].astype(str).unique().tolist())
            curr_cat = sess('selected_cat', '전체')
            cat_idx = unique_cat.index(curr_cat) if curr_cat in unique_cat else 0
            sel_cat = st.selectbox("구분", unique_cat, key='selected_cat', index=cat_idx)

        unique_gu = ["전체"]
        if '지역_구' in df_main.columns: unique_gu += sorted(df_main['지역_구'].astype(str).unique().tolist())
        with c4: 
            curr_gu = sess('selected_gu', '전체')
            gu_idx = unique_gu.index(curr_gu) if curr_gu in unique_gu else 0
            sel_gu = st.selectbox("지역 (구)", unique_gu, key='selected_gu', index=gu_idx)
            
        unique_dong = ["전체"]
        if '지역_동' in df_main.columns:
            if sel_gu == "전체": unique_dong += sorted(df_main['지역_동'].astype(str).unique().tolist())
            else: unique_dong += sorted(df_main[df_main['지역_구'] == sel_gu]['지역_동'].astype(str).unique().tolist())
        with c5: 
            curr_dong = sess('selected_dong', '전체')
            dong_idx = unique_dong.index(curr_dong) if curr_dong in unique_dong else 0
            sel_dong = st.selectbox("지역 (동)", unique_dong, key='selected_dong', index=dong_idx)

        st.divider()
        r1, r2, r3 = st.columns(3)
        LIMIT_HUGE = 100000000.0 

        if is_sale_mode:
            with r1:
                st.markdown("##### 💰 매매가 (만원)")
                max_price = get_max_if_exists("매매가")
                if max_price > 0:
                    c_a, c_b = st.columns(2)
                    c_a.number_input("최소", step=1000.0, key='min_price', value=sess('min_price', 0.0))
                    c_b.number_input("최대", step=1000.0, key='max_price', value=sess('max_price', max_price))
                else: st.caption("매매가 정보 없음")
            with r2:
                st.markdown("##### 📊 수익률(%)")
                max_yield = get_max_if_exists("수익률")
                if max_yield > 0:
                    c_a, c_b = st.columns(2)
                    c_a.number_input("최소", step=0.1, key='min_yield', value=sess('min_yield', 0.0))
                    c_b.number_input("최대", step=0.1, key='max_yield', value=sess('max_yield', 20.0))
                else: st.caption("수익률 정보 없음")
            with r3:
                st.markdown("##### 📐 대지/연면적 (평)")
                max_land = get_max_if_exists("대지면적")
                max_total = get_max_if_exists("연면적")
                c_a, c_b = st.columns(2)
                if max_land > 0: c_a.number_input("대지 최소", step=1.0, key='min_land', value=sess('min_land', 0.0))
                if max_land > 0: c_b.number_input("대지 최대", step=1.0, key='max_land', value=sess('max_land', max_land))
                c_c, c_d = st.columns(2)
                if max_total > 0: c_c.number_input("연면 최소", step=1.0, key='min_total', value=sess('min_total', 0.0))
                if max_total > 0: c_d.number_input("연면 최대", step=1.0, key='max_total', value=sess('max_total', max_total))
        else:
            with r1:
                st.markdown("##### 💰 보증금/월세 (만원)")
                max_dep = get_max_if_exists("보증금")
                max_rent = get_max_if_exists("월차임")
                c_a, c_b = st.columns(2)
                if max_dep > 0: c_a.number_input("보증금 최소", step=500.0, key='min_dep', value=sess('min_dep', 0.0))
                if max_dep > 0: c_b.number_input("보증금 최대", step=500.0, key='max_dep', value=sess('max_dep', max_dep))
                c_c, c_d = st.columns(2)
                if max_rent > 0: c_c.number_input("월세 최소", step=10.0, key='min_rent', value=sess('min_rent', 0.0))
                if max_rent > 0: c_d.number_input("월세 최대", step=10.0, key='max_rent', value=sess('max_rent', max_rent))
            with r2:
                st.markdown("##### 🔑 권리금/관리비")
                is_no_kwon = st.checkbox("무권리만", key='is_no_kwon')
                max_kwon = get_max_if_exists("권리금")
                max_man = get_max_if_exists("관리비")
                c_a, c_b = st.columns(2)
                if max_kwon > 0: c_a.number_input("권리금 최소", step=100.0, key='min_kwon', disabled=is_no_kwon, value=sess('min_kwon', 0.0))
                if max_kwon > 0: c_b.number_input("권리금 최대", step=100.0, key='max_kwon', disabled=is_no_kwon, value=sess('max_kwon', max_kwon))
                c_c, c_d = st.columns(2)
                if max_man > 0: c_c.number_input("관리비 최소", step=5.0, key='min_man', value=sess('min_man', 0.0))
                if max_man > 0: c_d.number_input("관리비 최대", step=5.0, key='max_man', value=sess('max_man', max_man))
            with r3:
                st.markdown("##### 📐 면적 (평)")
                max_area = get_max_if_exists("면적")
                c_a, c_b = st.columns(2)
                if max_area > 0: c_a.number_input("면적 최소", step=5.0, key='min_area', value=sess('min_area', 0.0))
                if max_area > 0: c_b.number_input("면적 최대", step=5.0, key='max_area', value=sess('max_area', max_area))

    # --- FILTER LOGIC ---
    df_filtered = df_main.copy()

    if '구분' in df_filtered.columns and sel_cat != "전체":
        df_filtered = df_filtered[df_filtered['구분'] == sel_cat]
    if '지역_구' in df_filtered.columns and sel_gu != "전체":
        df_filtered = df_filtered[df_filtered['지역_구'] == sel_gu]
    if '지역_동' in df_filtered.columns and sel_dong != "전체":
        df_filtered = df_filtered[df_filtered['지역_동'] == sel_dong]
    if '번지' in df_filtered.columns and st.session_state.exact_bunji:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]

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
        if '보증금' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
        if '월차임' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        if '면적' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['면적'] >= st.session_state.min_area) & (df_filtered['면적'] <= st.session_state.max_area)]
        if '관리비' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['관리비'] >= st.session_state.min_man) & (df_filtered['관리비'] <= st.session_state.max_man)]
        if '권리금' in df_filtered.columns:
            if st.session_state.is_no_kwon: df_filtered = df_filtered[df_filtered['권리금'] == 0]
            else: df_filtered = df_filtered[(df_filtered['권리금'] >= st.session_state.min_kwon) & (df_filtered['권리금'] <= st.session_state.max_kwon)]

    search_val = st.session_state.search_keyword.strip()
    if search_val:
        search_scope = df_filtered.drop(columns=['선택', 'IronID'], errors='ignore')
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]

    # --- LIST VIEW ---
    if len(df_filtered) == 0:
        st.warning("🔍 검색 결과가 없습니다.")
    else:
        st.info(f"📋 **{st.session_state.current_sheet}** 검색 결과: **{len(df_filtered)}**건")

    # [편집 권한 개방]
    editable_cols = ["내용", "보증금", "월차임", "매매가", "권리금", "관리비"]
    disabled_cols = [c for c in df_filtered.columns if c not in ['선택'] + editable_cols]
    
    # IronID 컬럼 숨기기 수정 (None 사용)
    col_cfg = {
        "선택": st.column_config.CheckboxColumn(width="small"),
        "IronID": None
    }
    
    if "매매가" in df_filtered.columns: col_cfg["매매가"] = st.column_config.NumberColumn("매매가(만)", format="%d")
    if "보증금" in df_filtered.columns: col_cfg["보증금"] = st.column_config.NumberColumn("보증금(만)", format="%d")
    if "월차임" in df_filtered.columns: col_cfg["월차임"] = st.column_config.NumberColumn("월세(만)", format="%d")
    if "권리금" in df_filtered.columns: col_cfg["권리금"] = st.column_config.NumberColumn("권리금(만)", format="%d")
    if "면적" in df_filtered.columns: col_cfg["면적"] = st.column_config.NumberColumn("면적(평)", format="%.1f")
    if "대지면적" in df_filtered.columns: col_cfg["대지면적"] = st.column_config.NumberColumn("대지(평)", format="%.1f")
    if "연면적" in df_filtered.columns: col_cfg["연면적"] = st.column_config.NumberColumn("연면(평)", format="%.1f")
    if "수익률" in df_filtered.columns: col_cfg["수익률"] = st.column_config.NumberColumn("수익률", format="%.2f%%")
    if "내용" in df_filtered.columns: col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")

    editor_key = f"editor_{st.session_state.current_sheet}"
    
    edited_df = st.data_editor(
        df_filtered,
        disabled=disabled_cols,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config=col_cfg,
        key=editor_key
    )

    # --- ACTION BAR ---
    st.divider()
    selected_rows = edited_df[edited_df['선택'] == True]
    selected_count = len(selected_rows)

    if selected_count > 0:
        st.success(f"✅ {selected_count}건 선택됨")
        
        ac1, ac2, ac3 = st.columns(3)
        
        current_tab = st.session_state.current_sheet
        base_tab = current_tab.replace("(종료)", "").replace("브리핑", "").strip()
        target_end_tab = f"{base_tab}(종료)"
        target_brief_tab = f"{base_tab}브리핑"
        
        with ac1:
            is_end_tab = "(종료)" in current_tab
            if st.button(f"🚀 종료 처리", use_container_width=True, disabled=is_end_tab):
                st.session_state.action_status = 'move_confirm'
        with ac2:
            is_brief_tab = "브리핑" in current_tab
            if st.button(f"📋 브리핑 복사", use_container_width=True, disabled=is_brief_tab):
                st.session_state.action_status = 'copy_confirm'
        with ac3:
            if st.button("🗑️ 영구 삭제", type="primary", use_container_width=True):
                st.session_state.action_status = 'delete_confirm'

        if st.session_state.action_status == 'move_confirm':
            with st.status(f"🚀 [이동] '{target_end_tab}'으로 보냅니다.", expanded=True) as status:
                st.warning("⚠️ 이동 후 원본에서는 삭제됩니다.")
                if st.button("확인 (이동)"):
                    success, msg = update_data("move", selected_rows, current_tab, target_end_tab)
                    if success:
                        status.update(label="완료", state="complete")
                        st.success(msg)
                        time.sleep(1.5)
                        st.session_state.action_status = None
                        st.cache_data.clear()
                        st.rerun()
                    else: st.error(msg)

        elif st.session_state.action_status == 'copy_confirm':
            with st.status(f"📋 [복사] '{target_brief_tab}'에 추가합니다.", expanded=True) as status:
                st.info("ℹ️ 원본은 유지됩니다.")
                if st.button("확인 (복사)"):
                    success, msg = update_data("copy", selected_rows, current_tab, target_brief_tab)
                    if success:
                        status.update(label="완료", state="complete")
                        st.success(msg)
                        time.sleep(1.5)
                        st.session_state.action_status = None
                    else: st.error(msg)

        elif st.session_state.action_status == 'delete_confirm':
            with st.status("🗑️ [삭제] 영구 삭제하시겠습니까?", expanded=True) as status:
                st.error("⚠️ 복구 불가능합니다.")
                if st.button("확인 (삭제)"):
                    success, msg = update_data("delete", selected_rows, current_tab)
                    if success:
                        status.update(label="완료", state="complete")
                        st.success(msg)
                        time.sleep(1.5)
                        st.session_state.action_status = None
                        st.cache_data.clear()
                        st.rerun()
                    else: st.error(msg)
    else:
        st.caption("👈 목록에서 '선택' 체크박스를 클릭하면 관리 버튼이 나타납니다.")
        st.session_state.action_status = None

# 프래그먼트 실행
main_interface()
