# core_engine.py
# 범공인 Pro v24 Enterprise - Core Data Engine Module (v24.99 Final Secure)
# Feature: Session Protection, Cache Purge, Precision Matching, Append New Row

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

# 데이터 타입 정의 (매물특징 통합)
NUMERIC_COLS = ["보증금", "월차임", "권리금", "관리비", "매매가", "수익률", "면적", "대지면적", "연면적", "층"]
STRING_COLS = ["구분", "지역_구", "지역_동", "번지", "매물특징", "비고", "호실"]
REQUIRED_COLS = ["번지"] 

# ==============================================================================
# [SECTION 2: DATA SANITIZATION ENGINE]
# ==============================================================================

def normalize_headers(df):
    """
    구글 시트 헤더를 표준화합니다. (공백 제거 및 용어 통합)
    '내용', '특징' 등을 '매물특징'으로 강제 통합합니다.
    """
    # 1. 헤더 공백 제거
    df.columns = df.columns.str.replace(' ', '').str.strip()
    
    # 2. 동의어 매핑 (매물특징 통합, 건물명 삭제)
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
        # [핵심] 모든 유사 용어를 '매물특징'으로 통일
        "매물특징": ["매물특징", "특징", "비고", "내용", "상세내용", "메모"],
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
                    # 층수: 음수(-) 기호 보존 (예: -1, 3, 3.5)
                    cleaned_series = val_str.str.extract(r'(-?[\d.]+)')[0]
                    df[col] = pd.to_numeric(cleaned_series, errors='coerce').fillna(1)
                else:
                    # 금액/면적: 숫자와 소수점만 남김
                    cleaned_series = val_str.str.replace(r'[^0-9.]', '', regex=True)
                    # NaN을 0.0으로 변환 (필수)
                    df[col] = pd.to_numeric(cleaned_series, errors='coerce').fillna(0.0)
            except: 
                df[col] = 0.0
                
    # 2. 문자열 컬럼 정제
    for col in STRING_COLS:
        if col in df.columns:
            try:
                df[col] = df[col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
                df[col] = df[col].replace('nan', '')
            except: 
                df[col] = ""
                
    return df.fillna("")

def validate_data_integrity(df):
    """
    필수 컬럼 존재 여부 및 데이터 무결성을 검증합니다.
    """
    errors = []
    for col in REQUIRED_COLS:
        if col not in df.columns: 
            errors.append(f"필수 컬럼 누락: {col}")
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
        'min_price': 0.0, 'max_price': 100000000.0, 
        'min_dep': 0.0, 'max_dep': 100000000.0,
        'min_rent': 0.0, 'max_rent': 100000000.0, 
        'min_kwon': 0.0, 'max_kwon': 100000000.0,
        'min_area': 0.0, 'max_area': 100000000.0, 
        'min_land': 0.0, 'max_land': 100000000.0,
        'min_yield': 0.0, 'max_yield': 100.0,
        'min_fl': -10.0, 'max_fl': 100.0
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

def safe_reset():
    """
    필터 관련 세션 상태를 초기화하고 캐시를 파괴합니다.
    [수정됨] auth_status를 보호하여 로그아웃 되는 것을 방지합니다.
    """
    # 보호할 시스템 변수 목록 (로그인 상태 포함)
    protected_keys = ['current_sheet', 'editor_key_version', 'view_mode', 'page_num', 'auth_status']
    
    for key in list(st.session_state.keys()):
        if key not in protected_keys:
            del st.session_state[key]
    
    st.session_state.editor_key_version += 1
    # [Cache Purge] 메모리 캐시 삭제로 데이터 갱신 보장
    st.cache_data.clear()

@st.cache_data(ttl=60) 
def load_sheet_data(sheet_name):
    """
    구글 시트에서 데이터를 로드하고 전처리합니다. (IronID 무적화)
    """
    gid = SHEET_GIDS.get(sheet_name)
    if not gid: return None
    
    csv_url = f"{SHEET_URL}/export?format=csv&gid={gid}"
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        df = pd.read_csv(csv_url)
        df = normalize_headers(df)
        df = sanitize_dataframe(df)
        
        needs_save = False
        if 'IronID' not in df.columns:
            df['IronID'] = [str(uuid.uuid4()) for _ in range(len(df))]
            needs_save = True
        else:
            empty_id_mask = df['IronID'].isna() | (df['IronID'].astype(str).str.strip() == "")
            if empty_id_mask.any():
                df.loc[empty_id_mask, 'IronID'] = [str(uuid.uuid4()) for _ in range(empty_id_mask.sum())]
                needs_save = True
        
        if needs_save:
            try:
                conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=df)
                st.toast("✅ 데이터 식별자(ID)를 자동으로 생성하여 저장했습니다.", icon="ℹ️")
            except Exception as e:
                st.error(f"ID 자동 저장 실패: {e}")

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
                val = temp_df[k].astype(str).str[:20] if k == '매물특징' else temp_df[k].astype(str)
                temp_df['_match_sig'] += val.str.replace(r'[^가-힣a-zA-Z0-9]', '', regex=True) + "|"
        except: continue
        
    return temp_df

# ==============================================================================
# [SECTION 5: UPDATE ENGINE (FULL LOGIC + APPEND)]
# ==============================================================================

def add_new_row(new_data, sheet_name):
    """
    [Phase 5] 신규 매물을 시트 맨 마지막에 추가(Append)합니다. (IronID 자동 생성)
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 딕셔너리를 데이터프레임으로 변환
        df_new = pd.DataFrame([new_data])
        
        # 2. 필수 ID 생성
        df_new['IronID'] = str(uuid.uuid4())
        
        # 3. 데이터 정제 (숫자, 문자 타입 맞춤)
        # 중요: sanitize_dataframe은 전체 컬럼을 검사하므로 누락된 컬럼은 빈 값으로 처리됨
        df_new = normalize_headers(df_new)
        df_new = sanitize_dataframe(df_new)
        
        # 4. 서버 데이터 로드 (컬럼 구조 맞추기 위해)
        # ttl=0으로 최신 상태 가져옴
        df_server = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        # 5. 컬럼 매핑 (서버에 있는 컬럼만 남기고 순서 맞춤)
        # 서버에 없는 컬럼은 버리고, 서버에 있는데 새 데이터에 없는건 빈 값으로
        common_cols = [c for c in df_server.columns if c in df_new.columns or c not in df_new.columns]
        
        # 새 데이터프레임을 서버 구조에 맞게 재편성
        df_final_new = pd.DataFrame(columns=df_server.columns)
        for col in df_server.columns:
            if col in df_new.columns:
                df_final_new[col] = df_new[col]
            else:
                df_final_new[col] = "" # 없는 컬럼은 빈 값
        
        # 6. 데이터 병합 (Append)
        # ignore_index=True로 인덱스 재설정
        df_updated = pd.concat([df_server, df_final_new], ignore_index=True)
        
        # 7. 저장 및 캐시 파괴
        conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=df_updated)
        st.cache_data.clear() # [핵심] 목록 즉시 갱신
        
        return True, "✅ 신규 매물이 성공적으로 등록되었습니다."
        
    except Exception as e:
        return False, f"신규 등록 실패: {str(e)}"

def update_single_row(updated_row, sheet_name):
    """
    [Phase 4] IronID를 기준으로 단일 행을 업데이트합니다.
    캐시 파괴(Cache Purge)를 통해 즉시 반영을 보장합니다.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # 1. 서버 데이터 로드 (캐시 무시)
        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        target_id = updated_row.get('IronID')
        
        # IronID 컬럼 생성
        if 'IronID' not in sheet_data.columns:
            sheet_data['IronID'] = [str(uuid.uuid4()) for _ in range(len(sheet_data))]
        
        row_idx = None
        
        # 3-A. [1차 시도] IronID로 매칭
        if target_id:
            match_list = sheet_data.index[sheet_data['IronID'].astype(str) == str(target_id)].tolist()
            if match_list:
                row_idx = match_list[0]
        
        # 3-B. [2차 시도] 세컨드 매칭 (번지 + 층 + 면적 + 호실) - 소수점 보정 포함
        if row_idx is None:
            u_addr = str(updated_row.get('번지', '')).strip()
            u_floor = str(updated_row.get('층', '')).strip()
            u_ho = str(updated_row.get('호실', '')).strip()
            
            try:
                u_area = round(float(updated_row.get('면적', 0)), 1)
            except: u_area = 0.0

            s_addr = sheet_data['번지'].astype(str).str.strip()
            s_floor = sheet_data['층'].astype(str).str.strip()
            s_ho = sheet_data['호실'].astype(str).str.strip() if '호실' in sheet_data.columns else ""
            
            try:
                s_area = pd.to_numeric(sheet_data['면적'], errors='coerce').fillna(0.0).round(1)
            except:
                s_area = 0.0

            cond = (s_addr == u_addr) & (s_floor == u_floor) & (s_area == u_area)
            if u_ho: cond = cond & (s_ho == u_ho)
            
            backup_match = sheet_data[cond].index.tolist()

            if backup_match:
                row_idx = backup_match[0]
                sheet_data.at[row_idx, 'IronID'] = str(target_id) if target_id else str(uuid.uuid4())

        if row_idx is None:
            return False, "❌ 원본 데이터를 찾을 수 없습니다. (ID 및 상세 조건 불일치)"
        
        # 4. 값 덮어쓰기
        for k, v in updated_row.items():
            if k in sheet_data.columns and k not in ['선택']:
                if k in NUMERIC_COLS:
                    try:
                        val_str = re.sub(r'[^0-9.-]', '', str(v)) if v else "0"
                        v = float(val_str) if val_str else 0.0
                    except: v = 0.0
                sheet_data.at[row_idx, k] = v
        
        # 5. 저장 및 캐시 파괴
        conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
        st.cache_data.clear() # [핵심] 캐시 파괴로 즉시 갱신 보장
        
        return True, "✅ 정보가 안전하게 저장되었습니다."
        
    except Exception as e:
        return False, f"저장 실패: {str(e)}"

def save_updates_to_sheet(edited_df, original_df, sheet_name):
    """
    [Phase 1] 리스트 뷰 대량 수정 저장 (캐시 파괴 포함)
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_org = original_df.set_index('IronID')
        df_new = edited_df.set_index('IronID')
        
        changed_ids = []
        for iid in df_org.index.intersection(df_new.index):
            row_org = df_org.loc[iid].drop(['선택'], errors='ignore').astype(str)
            row_new = df_new.loc[iid].drop(['선택'], errors='ignore').astype(str)
            if not row_org.equals(row_new):
                changed_ids.append(iid)
        
        if not changed_ids: return True, "변경 사항 없음", None

        sheet_data = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0))
        
        update_cnt = 0
        for iid in changed_ids:
            match_idx = sheet_data.index[sheet_data['IronID'].astype(str) == str(iid)].tolist()
            if match_idx:
                t_idx = match_idx[0]
                new_row = df_new.loc[iid]
                for col in sheet_data.columns:
                    if col in new_row.index and col not in ['선택', 'IronID']:
                        sheet_data.at[t_idx, col] = new_row[col]
                update_cnt += 1
                
        conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=sheet_data)
        st.cache_data.clear() # [핵심] 캐시 파괴
        
        return True, f"✅ {update_cnt}건 일괄 저장 완료", None
        
    except Exception as e:
        return False, f"일괄 저장 실패: {str(e)}", None

def execute_transaction(action_type, target_rows, source_sheet, target_sheet=None):
    """
    [Phase 2] 트랜잭션 처리 (캐시 파괴 포함)
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        if target_rows.empty: return False, "대상 없음", None
        
        src_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=source_sheet, ttl=0))
        target_ids = target_rows['IronID'].astype(str).tolist()
        
        mask = src_df['IronID'].astype(str).isin(target_ids)
        rows_to_process = src_df[mask]
        
        if rows_to_process.empty:
            return False, "❌ 대상을 찾을 수 없습니다.", None
            
        if action_type in ["move", "restore", "delete"]:
            new_src = src_df[~mask]
            
            if action_type in ["move", "restore"] and target_sheet:
                tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
                common_cols = [c for c in rows_to_process.columns if c in tgt_df.columns]
                new_tgt = pd.concat([tgt_df, rows_to_process[common_cols]], ignore_index=True)
                
                is_valid, msg = validate_data_integrity(new_tgt)
                if not is_valid: return False, msg, None
                
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt)
            
            conn.update(spreadsheet=SHEET_URL, worksheet=source_sheet, data=new_src)
            st.cache_data.clear() # [핵심] 캐시 파괴
            return True, f"✅ {len(rows_to_process)}건 처리 완료 ({action_type})", None
            
        elif action_type == "copy":
            if target_sheet:
                tgt_df = normalize_headers(conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet, ttl=0))
                common_cols = [c for c in rows_to_process.columns if c in tgt_df.columns]
                new_tgt = pd.concat([tgt_df, rows_to_process[common_cols]], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet, data=new_tgt)
                st.cache_data.clear() # [핵심] 캐시 파괴
                return True, f"✅ {len(rows_to_process)}건 복사 완료", None
                
        return False, "알 수 없는 명령", None

    except Exception as e:
        return False, f"트랜잭션 오류: {str(e)}", traceback.format_exc()
