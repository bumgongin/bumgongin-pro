import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import urllib.parse
import time
import uuid
import re

# [MODULE: SYSTEM SETUP]
# 1. 시스템 설정
st.set_page_config(
    page_title="범공인 Pro (v24.20.1)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [MODULE: STYLES & CSS]
# 2. 스타일 설정 (모바일 터치 최적화 & 스크롤 고정)
st.markdown("""
    <style>
    /* 버튼 및 입력창 크기 확보 */
    .stButton button { 
        min-height: 45px !important; 
        font-size: 15px !important; 
        font-weight: 600 !important; 
        width: 100%;
        border-radius: 8px;
    }
    input[type=number], input[type=text] { 
        min-height: 40px !important; 
    }
    
    /* 멀티셀렉트 터치 영역 개선 */
    div[data-baseweb="select"] > div {
        min-height: 40px !important;
    }
    
    /* 사이드바 컨테이너 스타일 */
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 1rem;
    }
    
    /* 모바일 최적화 */
    @media (max-width: 768px) { 
        .stDataEditor { font-size: 13px !important; }
        h1 { font-size: 20px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# [MODULE: CONSTANTS]
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
    # 리스트 선택 상태 초기화 (전체 선택 해제)
    if 'select_all' in st.session_state: st.session_state.select_all = False
    if 'deselect_all' in st.session_state: st.session_state.deselect_all = False
    
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

def initialize_search_state():
    defaults = {
        'search_keyword': "", 'exact_bunji': "",
        'selected_cat': [], 'selected_gu': [], 'selected_dong': [],
        'is_no_kwon': False,
        'min_dep': 0.0, 'max_dep': 100000000.0,
        'min_rent': 0.0, 'max_rent': 10000000.0,
        'min_kwon': 0.0, 'max_kwon': 100000000.0,
        'min_man': 0.0, 'max_man': 1000000.0,
        'min_price': 0.0, 'max_price': 100000000.0,
        'min_yield': 0.0, 'max_yield': 100.0,
        'min_land': 0.0, 'max_land': 1000000.0,
        'min_total': 0.0, 'max_total': 1000000.0,
        'min_area': 0.0, 'max_area': 1000000.0,
        'min_fl': -20.0, 'max_fl': 100.0
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
    
    # 전체 선택/해제 상태 관리용
    if 'editor_key_version' not in st.session_state:
        st.session_state.editor_key_version = 0

# [MODULE: DATA ENGINE]
@st.cache_data(ttl=600) 
def load_data(sheet_name):
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    
    csv_url = f"{SHEET_URL}/export?format=csv&gid={gid}"
    
    try:
        df = pd.read_csv(csv_url)
    except Exception:
        return None

    df = standardize_columns(df)

    numeric_candidates = ["보증금", "월차임", "권리금", "관리비", "면적", "층", "매매가", "수익률", "대지면적", "연면적"]
    for col in numeric_candidates:
        if col in df.columns:
            try:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', '').str.strip(), 
                    errors='coerce'
                ).fillna(0)
            except:
                df[col] = 0

    str_cols = df.select_dtypes(include=['object']).columns
    for col in str_cols:
        try:
            df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
        except: pass

    df = df.fillna("") 

    if '선택' in df.columns: df = df.drop(columns=['선택'])
    if 'IronID' in df.columns: df = df.drop(columns=['IronID'])
    
    # 고유 ID 생성 (매번 로드 시 갱신됨을 주의 - 세션 유지 중요)
    df['IronID'] = [str(uuid.uuid4()) for _ in range(len(df))]
    df.insert(0, '선택', False)
    
    return df

# [MODULE: UPDATE ENGINE (REAL-TIME SYNC)]
def update_data(action_type, target_rows, source_sheet, target_sheet=None):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
    except Exception:
        return False, "❌ 서비스 계정 연결 실패."
    
    try:
        src_df = conn.read(spreadsheet=SHEET_URL, worksheet=source_sheet, ttl=0)
        src_df = standardize_columns(src_df)
        
        target_rows_clean = target_rows.drop(columns=['선택', 'IronID'], errors='ignore')
        
        match_cols = ['번지', '층', '면적', '보증금', '매매가', '월차임', '내용']
        valid_keys = [k for k in match_cols if k in src_df.columns and k in target_rows_clean.columns]
        
        if len(valid_keys) < 2:
            return False, "❌ 식별 키 부족."

        def create_match_signature(df_in):
            temp_df = df_in.copy()
            temp_df['_match_sig'] = ""
            for k in valid_keys:
                try:
                    if k in ["면적", "보증금", "매매가", "월차임", "대지면적", "연면적"]:
                        col_series = pd.to_numeric(temp_df[k].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                        col_str = col_series.round(1).astype(str).str.replace(r'\.0$', '', regex=True)
                        temp_df['_match_sig'] += col_str
                    else: 
                        if k == '내용': val_series = temp_df[k].astype(str).str[:20]
                        else: val_series = temp_df[k].astype(str)
                        clean_str = val_series.str.replace(r'[^가-힣a-zA-Z0-9]', '', regex=True)
                        temp_df['_match_sig'] += clean_str
                except: continue
            return temp_df

        src_w_sig = create_match_signature(src_df)
        tgt_w_sig = create_match_signature(target_rows_clean)
        signatures_to_process = tgt_w_sig['_match_sig'].tolist()
        
        if not signatures_to_process:
            return False, "❌ 키 생성 오류."

        if action_type in ["delete", "move", "restore"]:
            # 원본에서 제외할 행 필터링
            rows_to_keep = ~src_w_sig['_match_sig'].isin(signatures_to_process)
            new_src_df = src_df[rows_to_keep]
            
            deleted_count = len(src_df) - len(new_src_df)
            if deleted_count == 0:
                # 디버깅 정보: 첫 번째 실패 시그니처 예시 출력
                debug_info = f"Target Sig: {signatures_to_process[0] if signatures_to_process else 'None'}"
                return False, f"❌ 매칭 실패 (서버 데이터 불일치).\n{debug_info}"

            if action_type in ["move", "restore"] and target_sheet:
                try:
                    tgt_df_remote = conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0)
                    tgt_df_remote = standardize_columns(tgt_df_remote)
                    new_tgt_df = pd.concat([tgt_df_remote, target_rows_clean], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt_df)
                except: return False, "❌ 타겟 시트 업데이트 실패."
            
            conn.update(spreadsheet=SHEET_URL, worksheet=source_sheet, data=new_src_df)
            st.cache_data.clear() # [REAL-TIME] 즉시 캐시 삭제
            action_map = {"move": "종료", "delete": "삭제", "restore": "복구"}
            return True, f"✅ {deleted_count}건 {action_map[action_type]} 완료!"

        elif action_type == "copy":
            tgt_df_remote = conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0)
            tgt_df_remote = standardize_columns(tgt_df_remote)
            new_tgt_df = pd.concat([tgt_df_remote, target_rows_clean], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt_df)
            st.cache_data.clear() # [REAL-TIME] 즉시 캐시 삭제
            return True, f"✅ {len(target_rows)}건 복사 완료!"

        return False, "❌ 알 수 없는 작업"

    except Exception as e:
        return False, f"🚨 실행 오류: {str(e)}"

# [MODULE: MAIN UI]
st.title("🏙️ 범공인 매물장 (Pro)")

if 'current_sheet' not in st.session_state: st.session_state.current_sheet = SHEET_NAMES[0]
if 'action_status' not in st.session_state: st.session_state.action_status = None 

# ---------------------------------------------------------
# [SIDEBAR: 물리적 분리형 제어 센터]
# ---------------------------------------------------------
with st.sidebar:
    st.header("📂 관리 도구")
    
    # [시트 선택 구역]
    with st.container(border=True):
        try: curr_idx = SHEET_NAMES.index(st.session_state.current_sheet)
        except: curr_idx = 0
        selected_sheet = st.selectbox("데이터 시트", SHEET_NAMES, index=curr_idx)
        
        if selected_sheet != st.session_state.current_sheet:
            st.session_state.current_sheet = selected_sheet
            st.session_state.action_status = None 
            st.cache_data.clear()
            st.rerun()

    # 데이터 로드 (필터 옵션 구성을 위해 미리 로드)
    df_main = load_data(st.session_state.current_sheet)
    if df_main is None:
        st.error("데이터 로드 실패")
        st.stop()

    initialize_search_state()
    def sess(key): return st.session_state[key]

    st.write("") # 간격 확보

    # [1. 텍스트 검색 구역] - 터치 미스 방지용 분리
    with st.container(border=True):
        st.markdown("##### 🔍 키워드 검색")
        st.text_input("통합 검색 (내용, 건물명)", key='search_keyword')
        st.text_input("번지 정밀검색 (예: 50-1)", key='exact_bunji')

    st.write("") # 간격 확보

    # [2. 멀티 필터 구역] - 물리적 분리
    with st.container(border=True):
        st.markdown("##### 🏷️ 항목 필터링")
        
        unique_cat = []
        if '구분' in df_main.columns: unique_cat = sorted(df_main['구분'].astype(str).unique().tolist())
        st.multiselect("구분 (상가/사무실 등)", unique_cat, key='selected_cat')

        unique_gu = []
        if '지역_구' in df_main.columns: unique_gu = sorted(df_main['지역_구'].astype(str).unique().tolist())
        st.multiselect("지역 (구)", unique_gu, key='selected_gu')
        
        unique_dong = []
        if '지역_동' in df_main.columns:
            if st.session_state.selected_gu:
                unique_dong = sorted(df_main[df_main['지역_구'].isin(st.session_state.selected_gu)]['지역_동'].astype(str).unique().tolist())
            else:
                unique_dong = sorted(df_main['지역_동'].astype(str).unique().tolist())
        st.multiselect("지역 (동)", unique_dong, key='selected_dong')

    st.write("") # 간격 확보

    # [3. 수치 필터 구역]
    is_sale_mode = "매매" in st.session_state.current_sheet
    with st.expander("💰 상세 금액/면적 설정", expanded=False):
        if is_sale_mode:
            st.caption("매매가 (만원)")
            c1, c2 = st.columns(2)
            c1.number_input("최소", step=1000.0, key='min_price', value=sess('min_price'))
            c2.number_input("최대", step=1000.0, key='max_price', value=sess('max_price'))
            
            st.caption("대지면적 (평)")
            c3, c4 = st.columns(2)
            c3.number_input("최소", step=1.0, key='min_land', value=sess('min_land'))
            c4.number_input("최대", step=1.0, key='max_land', value=sess('max_land'))
        else:
            st.caption("보증금 (만원)")
            c1, c2 = st.columns(2)
            c1.number_input("최소", step=500.0, key='min_dep', value=sess('min_dep'))
            c2.number_input("최대", step=500.0, key='max_dep', value=sess('max_dep'))
            
            st.caption("월세 (만원)")
            c3, c4 = st.columns(2)
            c3.number_input("최소", step=10.0, key='min_rent', value=sess('min_rent'))
            c4.number_input("최대", step=10.0, key='max_rent', value=sess('max_rent'))

        st.caption("공통 조건")
        st.checkbox("무권리만 보기", key='is_no_kwon')
    
    st.divider()
    if st.button("🔄 검색 조건 초기화"):
        safe_reset()

# [MODULE: MAIN FRAGMENT]
@st.fragment
def main_content():
    # --- FILTERING LOGIC ---
    df_filtered = df_main.copy()

    # 1. Multi-select filters
    if '구분' in df_filtered.columns and st.session_state.selected_cat:
        df_filtered = df_filtered[df_filtered['구분'].isin(st.session_state.selected_cat)]
    if '지역_구' in df_filtered.columns and st.session_state.selected_gu:
        df_filtered = df_filtered[df_filtered['지역_구'].isin(st.session_state.selected_gu)]
    if '지역_동' in df_filtered.columns and st.session_state.selected_dong:
        df_filtered = df_filtered[df_filtered['지역_동'].isin(st.session_state.selected_dong)]
    
    # 2. Text filters
    if '번지' in df_filtered.columns and st.session_state.exact_bunji:
        df_filtered = df_filtered[df_filtered['번지'].astype(str).str.strip() == st.session_state.exact_bunji.strip()]
    
    search_val = st.session_state.search_keyword.strip()
    if search_val:
        search_scope = df_filtered.drop(columns=['선택', 'IronID'], errors='ignore')
        mask = search_scope.fillna("").astype(str).apply(lambda x: ' '.join(x), axis=1).str.contains(search_val, case=False)
        df_filtered = df_filtered[mask]

    # 3. Numeric filters
    if is_sale_mode:
        if '매매가' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['매매가'] >= st.session_state.min_price) & (df_filtered['매매가'] <= st.session_state.max_price)]
        if '대지면적' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['대지면적'] >= st.session_state.min_land) & (df_filtered['대지면적'] <= st.session_state.max_land)]
    else:
        if '보증금' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['보증금'] >= st.session_state.min_dep) & (df_filtered['보증금'] <= st.session_state.max_dep)]
        if '월차임' in df_filtered.columns:
            df_filtered = df_filtered[(df_filtered['월차임'] >= st.session_state.min_rent) & (df_filtered['월차임'] <= st.session_state.max_rent)]
        if '권리금' in df_filtered.columns and st.session_state.is_no_kwon:
            df_filtered = df_filtered[df_filtered['권리금'] == 0]

    # --- MASS ACTION LOGIC (전체 선택/해제) ---
    c_sel, c_desel, c_dummy = st.columns([1, 1, 2])
    
    # 세션 상태에 필터링된 IronID 목록 저장 (data_editor 키 갱신용)
    filtered_ids = df_filtered['IronID'].tolist()
    
    # 전체 선택 로직
    if c_sel.button("✅ 전체 선택"):
        # 현재 필터링된 모든 행의 '선택' 값을 True로 설정하는 로직
        # st.data_editor는 session_state를 직접 수정한다고 반영되지 않으므로,
        # key를 변경하여 컴포넌트를 리로드하는 방식을 사용
        st.session_state[f"editor_{st.session_state.current_sheet}_data"] = {
            row_id: {"선택": True} for row_id in filtered_ids
        }
        # 강제 리로드 트리거 (이 부분은 Streamlit 구조상 한계로 완벽하지 않을 수 있음, 
        # 대신 원본 데이터프레임의 값을 바꿔서 재로드)
        for idx in df_filtered.index:
            df_filtered.at[idx, '선택'] = True
        st.session_state.editor_key_version += 1
        st.rerun()

    # 전체 해제 로직
    if c_desel.button("⬜ 전체 해제"):
        for idx in df_filtered.index:
            df_filtered.at[idx, '선택'] = False
        st.session_state.editor_key_version += 1
        st.rerun()

    # --- LIST VIEW ---
    if len(df_filtered) == 0:
        st.warning("🔍 검색 결과가 없습니다.")
    else:
        st.info(f"📋 **{st.session_state.current_sheet}** 검색 결과: **{len(df_filtered)}**건")

    editable_cols = ["내용", "보증금", "월차임", "매매가", "권리금", "관리비"]
    disabled_cols = [c for c in df_filtered.columns if c not in ['선택'] + editable_cols]
    
    col_cfg = {
        "선택": st.column_config.CheckboxColumn(width="small"),
        "IronID": None
    }
    
    # 동적 포맷팅
    format_map = {
        "매매가": "%d", "보증금": "%d", "월차임": "%d", "권리금": "%d",
        "면적": "%.1f", "대지면적": "%.1f", "연면적": "%.1f", "수익률": "%.2f%%"
    }
    for col, fmt in format_map.items():
        if col in df_filtered.columns:
            col_cfg[col] = st.column_config.NumberColumn(col, format=fmt)
    
    if "내용" in df_filtered.columns: 
        col_cfg["내용"] = st.column_config.TextColumn("특징", width="large")

    # 리로드용 동적 키 생성
    editor_key = f"editor_{st.session_state.current_sheet}_{st.session_state.editor_key_version}"
    
    # [SCROLL LOCK] 리스트 영역 높이 고정 (700px)
    with st.container(height=700):
        edited_df = st.data_editor(
            df_filtered,
            disabled=disabled_cols,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            key=editor_key
        )

    # --- ACTION BAR ---
    st.divider()
    selected_rows = edited_df[edited_df['선택'] == True]
    selected_count = len(selected_rows)

    if selected_count > 0:
        st.success(f"✅ {selected_count}건 선택됨")
        
        current_tab = st.session_state.current_sheet
        is_ended = "(종료)" in current_tab
        is_briefing = "브리핑" in current_tab
        base_tab_name = current_tab.replace("(종료)", "").replace("브리핑", "").strip()
        
        ac1, ac2, ac3 = st.columns(3)
        
        with ac1:
            if is_briefing: pass
            elif is_ended:
                target_restore = base_tab_name
                if st.button(f"♻️ 복구 ({target_restore})", type="primary", use_container_width=True):
                    st.session_state.action_status = 'restore_confirm'
            else:
                target_end = f"{base_tab_name}(종료)"
                if st.button(f"🚀 종료 ({target_end})", use_container_width=True):
                    st.session_state.action_status = 'move_confirm'

        with ac2:
            if not is_briefing:
                target_brief = f"{base_tab_name}브리핑"
                if st.button(f"📋 복사 ({target_brief})", use_container_width=True):
                    st.session_state.action_status = 'copy_confirm'

        with ac3:
            if st.button("🗑️ 삭제", type="primary", use_container_width=True):
                st.session_state.action_status = 'delete_confirm'

        # Action Confirmation
        if st.session_state.action_status == 'move_confirm':
            target_end = f"{base_tab_name}(종료)"
            with st.status(f"🚀 [종료] {selected_count}건을 이동합니다.", expanded=True) as status:
                if st.button("확인 (이동)"):
                    success, msg = update_data("move", selected_rows, current_tab, target_end)
                    if success:
                        st.success(msg)
                        time.sleep(1.0)
                        st.session_state.action_status = None
                        st.cache_data.clear()
                        st.rerun()
                    else: st.error(msg)

        elif st.session_state.action_status == 'restore_confirm':
            target_restore = base_tab_name
            with st.status(f"♻️ [복구] {selected_count}건을 되돌립니다.", expanded=True) as status:
                if st.button("확인 (복구)"):
                    success, msg = update_data("restore", selected_rows, current_tab, target_restore)
                    if success:
                        st.success(msg)
                        time.sleep(1.0)
                        st.session_state.action_status = None
                        st.cache_data.clear()
                        st.rerun()
                    else: st.error(msg)

        elif st.session_state.action_status == 'copy_confirm':
            target_brief = f"{base_tab_name}브리핑"
            with st.status(f"📋 [복사] {selected_count}건을 추가합니다.", expanded=True) as status:
                if st.button("확인 (복사)"):
                    success, msg = update_data("copy", selected_rows, current_tab, target_brief)
                    if success:
                        st.success(msg)
                        time.sleep(1.0)
                        st.session_state.action_status = None
                    else: st.error(msg)

        elif st.session_state.action_status == 'delete_confirm':
            with st.status(f"🗑️ [삭제] {selected_count}건을 영구 삭제합니다.", expanded=True) as status:
                st.error("⚠️ 복구할 수 없습니다.")
                if st.button("확인 (삭제)"):
                    success, msg = update_data("delete", selected_rows, current_tab)
                    if success:
                        st.success(msg)
                        time.sleep(1.0)
                        st.session_state.action_status = None
                        st.cache_data.clear()
                        st.rerun()
                    else: st.error(msg)

# 실행
main_content()
