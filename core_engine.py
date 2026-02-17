# core_engine.py
# 범공인 Pro v24 Enterprise - Core Data Engine Module (v24.96 Final)
# Feature: Advanced ID Matching, Robust Data Sanitization, Dual-Layer Update

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import time
import uuid
import re
import traceback

# ==============================================================================
# [SECTION 1: GLOBAL CONFIGURATION]
# ==============================================================================

# 구글 시트 URL (상수)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1bmTnLu-vMvlAGRSsCI4a8lk00U38covWl5Wfn9JZYVU"

# 시트 GID 매핑
SHEET_GIDS = {
    "임대": "2063575964", "임대(종료)": "791354475", 
    "매매": "1833762712", "매매(종료)": "1597438389",
    "임대브리핑": "982780192", "매매브리핑": "807085458"
}
SHEET_NAMES = list(SHEET_GIDS.keys())

# 데이터 타입 정의 (건물명 제외, 매물특징 통합)
NUMERIC_COLS = ["보증금", "월차임", "권리금", "관리비", "매매가", "수익률", "면적", "대지면적", "연면적", "층"]
STRING_COLS = ["구분", "지역_구", "지역_동", "번지", "매물특징", "비고", "호실"]
REQUIRED_COLS = ["번지"] # 최소한 번지는 있어야 데이터로 인정

# ==============================================================================
# [SECTION 2: DATA SANITIZATION ENGINE]
# ==============================================================================

def normalize_headers(df):
    """
    구글 시트 헤더를 표준화합니다. (공백 제거 및 동의어 매핑)
    """
    # 1. 헤더 공백 제거
    df.columns = df.columns.str.replace(' ', '').str.strip()
    
    # 2. 동의어 매핑 (실무 용어 대응 - 건물명 삭제, 매물특징 통합)
    synonym_map = {
        "보증금": ["보증금(만원)", "기보증금(만원)", "기보증금", "보증금", "보증", "보"],
        "월차임": ["월차임(만원)", "기월세(만원)", "월세(만원)", "월세", "기월세", "차임", "월"],
        "권리금": ["권리금_입금가(만원)", "권리금(만원)", "권리금", "권리", "시설권리", "권"],
        "관리비": ["관리비(만원)", "관리비", "관"],
        "매매가": ["매매가(만원)", "매매금액(만원)", "매매금액", "매매가", "매가", "매매"],
        "면적": ["전용면적(평)", "실평수", "전용면적", "면적", "평수", "실면적"],
        "대지면적": ["대지면적(평)", "대지", "대지면적"],
        "연면적": ["연면적(평)", "연면적"],
        "수익률": ["수익률(%)", "수익률"],
        "층": ["해당층", "층", "지상층", "층수", "해당"],
        "매물특징": ["매물특징", "특징", "비고", "내용", "상세내용"],
        "번지": ["지번", "번지", "지역_번지", "주소2", "세부주소"],
        "구분": ["매물구분", "구분", "항목", "종류"],
        "지역_구": ["지역_구", "구", "시군구"],
        "지역_동": ["지역_동", "동", "읍면동"],
        "연락처": ["연락처", "전화번호", "임대인연락처", "주인번호"],
        "호실": ["호실", "호"]
    }
    
    # 역방향 매핑 (별칭 -> 표준명)
    for standard, aliases in synonym_map.items():
        for alias in aliases:
            clean_alias = alias.replace(' ', '')
            if clean_alias in df.columns:
                df.rename(columns={clean_alias: standard}, inplace=True)
                break 
    return df

def sanitize_dataframe(df):
    """
    데이터프레임 값을 정제하여 분석 가능한 형태로 변환합니다.
    """
    # 1. 숫자 컬럼 정제
    for col in NUMERIC_COLS:
        if col in df.columns:
            try:
                val_str = df[col].astype(str)
                
                if col == '층':
                    # 층수: 음수(-) 기호, 숫자, 소수점만 허용 (예: -1, 3, 3.5)
                    cleaned_series = val_str.str.extract(r'(-?[\d.]+)')[0]
                    df[col] = pd.to_numeric(cleaned_series, errors='coerce').fillna(1)
                else:
                    # 금액/면적: 숫자와 소수점만 남김 (음수 없음)
                    cleaned_series = val_str.str.replace(r'[^0-9.]', '', regex=True)
                    # NaN을 0으로 바꾸고 float 변환
                    df[col] = pd.to_numeric(cleaned_series, errors='coerce').fillna(0.0)
            except: 
                df[col] = 0.0
                
    # 2. 문자열 컬럼 정제
    for col in STRING_COLS:
        if col in df.columns:
            try:
                # 연속 공백을 하나로 줄이고 앞뒤 공백 제거
                df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
                # 'nan' 문자열 처리
                df[col] = df[col].replace('nan', '')
            except: 
                df[col] = ""
                
    return df.fillna("")

def validate_data_integrity(df):
    """
    필수 컬럼 존재 여부 및 데이터 무결성을 검증합니다.
    """
    errors = []
    # 필수 컬럼이 아예 없는 경우
    for col in REQUIRED_COLS:
        if col not in df.columns: 
            errors.append(f"필수 컬럼 누락: {col}")
        # 필수 컬럼 값이 비어있는 행이 있는 경우 (경고 수준)
        elif df[col].astype(str).str.strip().eq("").any():
            pass 
    
    if errors: 
        return False, "\n".join(errors)
    return True, "Integrity Check Passed"

# ==============================================================================
# [SECTION 3: CORE LOAD ENGINE]
# ==============================================================================

def initialize_search_state():
    """
    앱 실행 시 세션 상태(검색 필터 등)를 초기화합니다.
    """
    if 'editor_key_version' not in st.session_state:
        st.session_state.editor_key_version = 0
        
    defaults = {
        'search_keyword': "", 'exact_bunji': "", 'selected_cat': [], 
        'selected_gu': [], 'selected_dong': [], 'is_no_kwon': False,
        'min_price': 0.0, 'max_price': 10000000.0, 
        'min_dep': 0.0, 'max_dep': 1000000.0,
        'min_rent': 0.0, 'max_rent': 10000.0, 
        'min_kwon': 0.0, 'max_kwon': 100000.0,
        'min_area': 0.0, 'max_area': 10000.0, 
        'min_land': 0.0, 'max_land': 10000.0,
        'min_total': 0.0, 'max_total': 10000.0, 
        'min_fl': -10.0, 'max_fl': 100.0
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def safe_reset():
    """
    필터 관련 세션 상태를 초기화하고 리런합니다.
    """
    for key in list(st.session_state.keys()):
        # 시스템 핵심 변수는 유지
        if key not in ['current_sheet', 'editor_key_version', 'view_mode', 'page_num']:
            del st.session_state[key]
    
    st.session_state.editor_key_version += 1
    st.cache_data.clear()

@st.cache_data(ttl=60) # 캐시 주기를 짧게 잡아 최신성 유지
def load_sheet_data(sheet_name):
    """
    구글 시트에서 데이터를 로드하고 전처리합니다. (IronID 무적화 및 자동 저장)
    """
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    
    # CSV 형태로 내보내기 URL 생성
    csv_url = f"{SHEET_URL}/export?format=csv&gid={gid}"
    
    # 데이터 로드 및 ID 생성용 커넥션 (저장이 필요할 수 있으므로)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        # 1. 데이터 로드
        df = pd.read_csv(csv_url)
        df = normalize_headers(df)
        df = sanitize_dataframe(df)
        
        # 2. [IronID 무적화 로직] - ID가 없으면 생성하고 시트에 즉시 반영
        needs_save = False
        if 'IronID' not in df.columns:
            df['IronID'] = [str(uuid.uuid4()) for _ in range(len(df))]
            needs_save = True
        else:
            # ID 컬럼이 있지만 비어있는 행 찾기
            empty_id_mask = df['IronID'].isna() | (df['IronID'].astype(str).str.strip() == "")
            if empty_id_mask.any():
                df.loc[empty_id_mask, 'IronID'] = [str(uuid.uuid4()) for _ in range(empty_id_mask.sum())]
                needs_save = True
        
        # 3. 변경 사항이 있으면 즉시 시트에 저장 (식별 불가 방지)
        if needs_save:
            try:
                conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=df)
                st.toast("✅ 데이터 식별자(ID)를 자동으로 생성하여 저장했습니다.", icon="ℹ️")
            except Exception as e:
                st.error(f"ID 자동 저장 실패: {e}")

        # 4. '선택' 컬럼 초기화 (UI용)
        if '선택' in df.columns: df = df.drop(columns=['선택'])
        df.insert(0, '선택', False)
        
        return df
    except Exception as e:
        print(f"[Load Error] {e}")
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None

# ==============================================================================
# [SECTION 4: MATCHING ENGINE]
# ==============================================================================

def create_match_signature(df, keys):
    """
    데이터 매칭을 위한 고유 서명(Signature)을 생성합니다.
    """
    temp_df = df.copy()
    temp_df['_match_sig'] = ""
    
    for k in keys:
        try:
            if k in NUMERIC_COLS:
                val_str = temp_df[k].astype(str)
                if k == '층':
                    val_str = val_str.str.extract(r'(-?[\d.]+)')[0]
                else:
                    val_str = val_str.str.replace(r'[^0-9.]', '', regex=True)
                
                val = pd.to_numeric(val_str, errors='coerce').fillna(0)
                temp_df['_match_sig'] += val.round(1).astype(str).str.replace(r'\.0$', '', regex=True) + "|"
            else:
                # 텍스트는 20자까지만
                val = temp_df[k].astype(str).str[:20] if k == '매물특징' else temp_df[k].astype(str)
                temp_df['_match_sig'] += val.str.replace(r'[^가-힣a-zA-Z0-9]', '', regex=True) + "|"
        except: continue
        
    return temp_df

# ==============================================================================
# [SECTION 5: UPDATE ENGINE (FULL LOGIC)]
# ==============================================================================

def update_single_row(updated_row, sheet_name):
    """
    [Phase 4] IronID를 기준으로 단일 행을 즉시 업데이트합니다.
    ID 매칭 실패 시 '세컨드 매칭(번지+층+면적+호실)'으로 재시도하여 저장을 보장합니다.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 서버 데이터 최신 로드 (캐시 무시 ttl=0)
        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        # 2. 고유 식별자(IronID) 확인
        target_id = updated_row.get('IronID')
        
        # IronID 컬럼이 없는 경우 생성 (서버 데이터 보정)
        if 'IronID' not in sheet_data.columns:
            sheet_data['IronID'] = [str(uuid.uuid4()) for _ in range(len(sheet_data))]
        
        row_idx = None
        
        # 3-A. [1차 시도] IronID로 매칭
        if target_id:
            match_list = sheet_data.index[sheet_data['IronID'].astype(str) == str(target_id)].tolist()
            if match_list:
                row_idx = match_list[0]
        
        # 3-B. [2차 시도] 세컨드 매칭 (번지 + 층 + 면적 + 호실) - 건물명 제외하고 4가지로 찾음
        if row_idx is None:
            cond_addr = sheet_data['번지'].astype(str) == str(updated_row.get('번지', ''))
            cond_floor = sheet_data['층'].astype(str) == str(updated_row.get('층', ''))
            cond_area = sheet_data['면적'].astype(str) == str(updated_row.get('면적', ''))
            cond_ho = sheet_data['호실'].astype(str) == str(updated_row.get('호실', ''))
            
            # 호실이 비어있을 수도 있으니 호실 조건은 값이 있을 때만
            if updated_row.get('호실'):
                backup_match = sheet_data[cond_addr & cond_floor & cond_area & cond_ho].index.tolist()
            else:
                backup_match = sheet_data[cond_addr & cond_floor & cond_area].index.tolist()

            if backup_match:
                row_idx = backup_match[0]
                # 매칭된 행에 IronID가 없다면 현재 ID를 부여하여 동기화
                sheet_data.at[row_idx, 'IronID'] = str(target_id) if target_id else str(uuid.uuid4())

        if row_idx is None:
            return False, "❌ 원본 데이터를 찾을 수 없습니다. (ID 및 상세주소 매칭 실패)"
        
        # 4. 값 덮어쓰기 (선택 컬럼 제외)
        for k, v in updated_row.items():
            if k in sheet_data.columns and k not in ['선택']:
                # 숫자 컬럼 처리
                if k in NUMERIC_COLS:
                    try:
                        # 정규식으로 숫자만 추출하되 마이너스, 소수점 허용
                        val_str = re.sub(r'[^0-9.-]', '', str(v)) if v else "0"
                        v = float(val_str) if val_str else 0.0
                    except: v = 0.0
                sheet_data.at[row_idx, k] = v
        
        # 5. 구글 시트에 저장
        conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
        return True, "✅ 정보가 안전하게 저장되었습니다."
        
    except Exception as e:
        return False, f"저장 실패: {str(e)}"

def save_updates_to_sheet(edited_df, original_df, sheet_name):
    """
    [Phase 1] 리스트 뷰(data_editor)의 대량 수정 사항을 저장합니다.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 변경된 행 추출
        df_org = original_df.set_index('IronID')
        df_new = edited_df.set_index('IronID')
        
        changed_ids = []
        for iid in df_org.index.intersection(df_new.index):
            # '선택' 컬럼을 제외하고 내용 비교
            row_org = df_org.loc[iid].drop(['선택'], errors='ignore').astype(str)
            row_new = df_new.loc[iid].drop(['선택'], errors='ignore').astype(str)
            if not row_org.equals(row_new):
                changed_ids.append(iid)
        
        if not changed_ids:
            return True, "변경 사항 없음"
            
        # 2. 서버 데이터 로드
        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        # 3. 업데이트 실행
        update_cnt = 0
        for iid in changed_ids:
            # 서버 데이터에서 ID 매칭
            match_idx = sheet_data.index[sheet_data['IronID'].astype(str) == str(iid)].tolist()
            if match_idx:
                t_idx = match_idx[0]
                # 변경된 컬럼만 업데이트
                new_row = df_new.loc[iid]
                for col in sheet_data.columns:
                    if col in new_row.index and col not in ['선택', 'IronID']:
                        sheet_data.at[t_idx, col] = new_row[col]
                update_cnt += 1
                
        # 4. 저장
        conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
        return True, f"✅ {update_cnt}건 일괄 저장 완료"
        
    except Exception as e:
        return False, f"일괄 저장 실패: {str(e)}"

def execute_transaction(action_type, target_rows, source_sheet, target_sheet=None):
    """
    [Phase 2] 이동(Move), 복구(Restore), 복사(Copy), 삭제(Delete) 트랜잭션 처리
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        if target_rows.empty: return False, "대상 없음", None
        
        # 1. 소스 데이터 로드
        src_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=source_sheet, ttl=0))
        target_ids = target_rows['IronID'].astype(str).tolist()
        
        # 2. 처리할 행 식별 (IronID 기준)
        # 서버 데이터에 해당 ID가 있는지 확인
        mask = src_df['IronID'].astype(str).isin(target_ids)
        rows_to_process = src_df[mask]
        
        if rows_to_process.empty:
            return False, "❌ 서버에서 대상을 찾을 수 없습니다. (이미 삭제됨?)", None
            
        # 3. 액션 분기
        if action_type in ["move", "restore", "delete"]:
            # 소스에서 제거할 데이터 (남길 데이터 = mask의 반대)
            new_src = src_df[~mask]
            
            # 이동/복구인 경우 타겟에 추가
            if action_type in ["move", "restore"] and target_sheet:
                tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
                # 타겟 시트와 컬럼 맞추기 (공통 컬럼만)
                common_cols = [c for c in rows_to_process.columns if c in tgt_df.columns]
                # 데이터 병합
                new_tgt = pd.concat([tgt_df, rows_to_process[common_cols]], ignore_index=True)
                # 타겟 시트 저장
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt)
            
            # 소스 시트 업데이트 (삭제 반영)
            conn.update(spreadsheet=SHEET_URL, worksheet=source_sheet, data=new_src)
            return True, f"✅ {len(rows_to_process)}건 처리 완료 ({action_type})", None
            
        elif action_type == "copy":
            # 복사 (소스 유지, 타겟 추가)
            if target_sheet:
                tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
                common_cols = [c for c in rows_to_process.columns if c in tgt_df.columns]
                new_tgt = pd.concat([tgt_df, rows_to_process[common_cols]], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt)
                return True, f"✅ {len(rows_to_process)}건 복사 완료", None
                
        return False, "알 수 없는 명령", None

    except Exception as e:
        return False, f"트랜잭션 오류: {str(e)}", traceback.format_exc()
