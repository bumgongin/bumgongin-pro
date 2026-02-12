import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
import time
from difflib import get_close_matches

# ==========================================
# [1. 시스템 설정 및 표준 스타일]
# ==========================================
st.set_page_config(
    page_title="범공인 Pro (Skeleton)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------
# [필수] API 및 환경 상수
# ------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU/edit"
# ------------------------------------------
# [스타일] 모바일 반응형 & 경고 차단 CSS
# ------------------------------------------
st.markdown("""
    <style>
    /* 전체 폰트 및 배경: Pretendard 적용 */
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif !important; }
    .stApp { background-color: #f8f9fa; }
    
    /* [버튼] 터치 최적화 (높이 60px) */
    .stButton button { 
        min-height: 60px !important; 
        font-weight: 700 !important; 
        font-size: 16px !important;
        border-radius: 12px !important;
        border: 1px solid #dee2e6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    .stButton button:active { transform: scale(0.98); background-color: #e9ecef; }
    
    /* [컨테이너] 카드 스타일 */
    .css-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* [반응형 처리] 모바일 (768px 이하) */
    @media (max-width: 768px) {
        /* 사이드바가 모바일에서 너무 좁아지지 않게 */
        section[data-testid="stSidebar"] { width: 80% !important; }
        
        /* 폰트 사이즈 조정 */
        h1 { font-size: 22px !important; }
        h2, h3 { font-size: 18px !important; }
        .stMarkdown p { font-size: 14px !important; }
        
        /* 모바일에서 필터 컨테이너 패딩 축소 */
        .css-card { padding: 15px; }
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# [2. 데이터 엔진: 지능형 로더 (Intelligent Loader)]
# ==========================================

class DataEngine:
    """데이터 로드, 매핑, 정제를 담당하는 핵심 엔진"""
    
    # 시스템 표준 컬럼 정의 (이 이름으로 내부 관리)
    STANDARD_COLS = [
        "선택", "__IRON_ID__", # 시스템 관리용
        "구분", "지역_구", "지역_동", "번지", "건물명", "주소",  # 위치 정보
        "매매가", "보증금", "월차임", "권리금", "수익률",       # 가격 정보
        "대지면적", "연면적", "건축면적", "층수", "면적",       # 건물 정보
        "내용", "위도", "경도"                                # 상세 정보
    ]

    @staticmethod
    def fuzzy_match_cols(df_columns):
        """
        [지능형 매핑] 시트의 컬럼명이 코드와 달라도 자동으로 찾아내는 함수
        예: '지역 구' -> '지역_구', '매매금액' -> '매매가'
        """
        mapping = {}
        df_cols_list = df_columns.tolist()
        
        for std_col in DataEngine.STANDARD_COLS:
            if std_col in ["선택", "__IRON_ID__"]: continue # 시스템 컬럼 제외
            
            # 1. 완전 일치 확인
            if std_col in df_cols_list:
                mapping[std_col] = std_col
                continue
                
            # 2. 유사도 매칭 (60% 이상 일치 시 채택)
            matches = get_close_matches(std_col, df_cols_list, n=1, cutoff=0.6)
            if matches:
                mapping[std_col] = matches[0]
            else:
                mapping[std_col] = None # 매칭 실패 (나중에 빈 칸 생성)
        
        return mapping

    @staticmethod
    def clean_data(df):
        """[데이터 세척] 모든 데이터를 문자열로 변환하고 NaN 제거"""
        return df.astype(str).replace(["nan", "None", "NaN", "<NA>"], "").apply(lambda x: x.str.strip())

    @staticmethod
    def generate_iron_id(prefix):
        """[Iron-ID] 중복 없는 고유 ID 생성"""
        return f"{prefix}_{int(time.time()*1000)}_{str(uuid.uuid4())[:6]}"


# ==========================================
# [3. 세션 및 데이터 로드 컨트롤러]
# ==========================================

if 'data_store' not in st.session_state:
    st.session_state.data_store = {}
    st.session_state.is_loaded = False

@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def load_all_data():
    """모든 시트 데이터를 로드하고 표준화하여 세션에 저장"""
    conn = get_conn()
    sheets = ["임대", "매매", "임대(종료)", "매매(종료)", "임대브리핑", "매매브리핑"]
    
    with st.status("🚀 데이터 엔진 가동 중...", expanded=True) as status:
        for sheet_name in sheets:
            try:
                st.write(f"📂 [{sheet_name}] 시트 연결 중...")
                
                # 1. Raw 데이터 로드
                df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
                df = DataEngine.clean_data(df)
                
                # 2. 컬럼 매핑 수행
                col_map = DataEngine.fuzzy_match_cols(df.columns)
                
                # 3. 표준 포맷으로 변환
                new_df = pd.DataFrame()
                for std, src in col_map.items():
                    if src:
                        new_df[std] = df[src]
                    else:
                        new_df[std] = "" # 매칭 안된 컬럼은 빈 값 처리
                
                # 4. 시스템 컬럼 주입
                # Iron-ID (기존 값이 있으면 유지, 없으면 생성)
                if '__IRON_ID__' not in df.columns:
                    new_df['__IRON_ID__'] = [DataEngine.generate_iron_id(sheet_name) for _ in range(len(new_df))]
                else:
                    # 기존 ID가 있다면 가져오되, 빈 값은 채움
                    existing_ids = df['__IRON_ID__'] if '__IRON_ID__' in df.columns else []
                    filled_ids = []
                    for eid in existing_ids:
                        if not eid: filled_ids.append(DataEngine.generate_iron_id(sheet_name))
                        else: filled_ids.append(eid)
                    new_df['__IRON_ID__'] = filled_ids

                # 선택 체크박스 (항상 False로 초기화)
                new_df.insert(0, '선택', False)
                
                # 5. 세션 저장
                st.session_state.data_store[sheet_name] = new_df
                
            except Exception as e:
                st.error(f"❌ [{sheet_name}] 로드 실패: {e}")
                # 실패 시 빈 프레임 생성 (시스템 다운 방지)
                st.session_state.data_store[sheet_name] = pd.DataFrame(columns=DataEngine.STANDARD_COLS)
        
        st.session_state.is_loaded = True
        status.update(label="✅ 데이터 로드 완료!", state="complete", expanded=False)

# 앱 시작 시 자동 로드
if not st.session_state.is_loaded:
    load_all_data()


# ==========================================
# [4. UI 레이아웃: 사이드바 & 헤더]
# ==========================================

with st.sidebar:
    st.header("🏗️ 범공인 Pro")
    st.caption("v24.14 | Phase 1: Skeleton")
    
    # 4-1. 시트 선택
    current_sheet = st.selectbox("📂 작업 시트", list(st.session_state.data_store.keys()))
    
    # 4-2. 데이터 현황판 (Debug Info)
    if current_sheet in st.session_state.data_store:
        count = len(st.session_state.data_store[current_sheet])
        st.info(f"데이터: {count}건 로드됨")
    
    st.markdown("---")
    
    # 4-3. 컨트롤 버튼 (박제)
    col_sb1, col_sb2 = st.columns(2)
    if col_sb1.button("🔄 새로고침"):
        st.cache_resource.clear()
        st.session_state.is_loaded = False
        st.rerun()
        
    if col_sb2.button("💾 저장"):
        st.toast("⚠️ 아직 기능이 구현되지 않은 단계입니다.")


# ==========================================
# [5. 메인 작업 공간 (조립식 구조)]
# ==========================================

st.title(f"🏙️ {current_sheet} 관리 모드")

# 현재 작업 데이터 가져오기
df_work = st.session_state.data_store[current_sheet]

# 5-1. [MODULE: FILTER_SECTION] - 자리 잡기
with st.container():
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.markdown("### 🔍 상세 필터 (준비 중)")
    st.info("다음 단계에서 [임대/매매 정밀 필터 모듈]이 이곳에 조립됩니다.")
    
    # 모바일 반응형 테스트를 위한 더미 버튼
    cols = st.columns(4) # PC: 4열
    cols[0].button("필터 테스트 1")
    cols[1].button("필터 테스트 2")
    
    st.markdown('</div>', unsafe_allow_html=True)


# 5-2. [MODULE: LIST_SECTION] - 기본 뼈대
with st.container():
    st.subheader(f"📋 매물 리스트 ({len(df_work)}건)")
    
    # Selection Mode를 쓰지 않는 표준 데이터 에디터
    # CheckboxColumn을 사용하여 안정성 확보
    st.data_editor(
        df_work,
        key=f"editor_{current_sheet}",
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "선택": st.column_config.CheckboxColumn(width="small"),
            "__IRON_ID__": None, # ID 숨김
            "위도": None, "경도": None
        },
        disabled=["__IRON_ID__"]
    )


# 5-3. [MODULE: ACTION_PANEL] - 자리 잡기
st.divider()
st.subheader("🎮 액션 패널")
st.warning("🚧 [이동/복사/삭제 트랜잭션 모듈]이 조립될 위치입니다.")


# 5-4. [MODULE: DETAIL_VIEW] - 자리 잡기
st.divider()
st.subheader("📝 상세 정보 및 지도")

st.warning("🚧 [네이버 지도 및 상세 수정 모듈]이 조립될 위치입니다.")
