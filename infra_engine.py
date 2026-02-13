import requests
import pandas as pd
import re
import math

# ==========================================
# 1. API 환경 설정 (보안 및 VPC 규격 준수)
# ==========================================

# [NAVER Enterprise VPC 설정]
NAVER_VPC_CLIENT_ID = "j6kk02fqy0"
NAVER_VPC_CLIENT_SECRET = "Lm0UTMBLuPWeDQJ4OZNn3ec82tvgAvllqJ46ceuU"
NAVER_VPC_ENDPOINT = "https://maps.apigw.ntruss.com/"

NAVER_VPC_HEADERS = {
    "x-ncp-apigw-api-key-id": NAVER_VPC_CLIENT_ID,
    "x-ncp-apigw-api-key": NAVER_VPC_CLIENT_SECRET,
    "Content-Type": "application/json"
}

# [KAKAO REST API 설정]
KAKAO_REST_KEY = "72e1d9f46c8c70448510d2f6215ad512"
KAKAO_HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_REST_KEY}"
}

# 공통 설정
TIMEOUT_SEC = 2  # 모든 요청은 2초 내 응답 제한

# ==========================================
# 2. 유틸리티 함수 (내부 로직 - 방어적 코딩)
# ==========================================

def _call_kakao_local(endpoint, params):
    """카카오 로컬 API 호출 래퍼 (실패 시 빈 리스트 반환 보장)"""
    url = f"https://dapi.kakao.com/v2/local/search/{endpoint}.json"
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            return response.json().get('documents', [])
        return []
    except Exception:
        # 타임아웃, 연결 오류 등 모든 예외 상황에서 빈 리스트 반환
        return []

def _extract_exit_number(place_name):
    """정규표현식을 이용해 역 이름에서 출구 번호 추출 (Safe Handling)"""
    if not place_name or not isinstance(place_name, str):
        return ""
    try:
        # 예: "강남역 2호선 1번출구" -> "1번출구" 추출
        match = re.search(r'(\d+번\s?출구)', place_name)
        if match:
            return match.group(1)
    except Exception:
        pass
    return ""

def _calculate_walking_data(origin_x, origin_y, dest_x, dest_y):
    """
    도보 거리 및 시간 계산 (Zero-Failure)
    - 좌표 오류나 계산 오류 발생 시 0, 0 반환하여 로직 중단 방지
    """
    dist_m = 0
    time_min = 0

    # 좌표 유효성 검사
    if not (origin_x and origin_y and dest_x and dest_y):
        return 0, 0

    # 1. Mobility API (Directions) 시도
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{origin_x},{origin_y}",
        "destination": f"{dest_x},{dest_y}",
        "priority": "RECOMMEND",
        "car_type": 1 
    }
    
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            routes = response.json().get('routes', [])
            if routes:
                summary = routes[0].get('summary', {})
                dist_m = summary.get('distance', 0)
                time_min = round(dist_m / 67, 1) # 성인 평균 보폭 분속 67m
                return dist_m, time_min
    except Exception:
        pass # API 실패 시 조용히 Fallback으로 이동

    # 2. Fallback: 직선 거리 기반 보정 공식 적용
    try:
        dx = (float(dest_x) - float(origin_x)) * 88000  # 경도 1도 ≈ 88km
        dy = (float(dest_y) - float(origin_y)) * 111000 # 위도 1도 ≈ 111km
        straight_dist = math.sqrt(dx**2 + dy**2)
        
        # 보정 계수 1.25배 적용
        dist_m = int(straight_dist * 1.25)
        time_min = round(dist_m / 67, 1)
    except Exception:
        # 좌표 변환 실패 등 모든 계산 에러 시 0 반환
        return 0, 0

    return dist_m, time_min

# ==========================================
# 3. 핵심 분석 함수 (Zero-Failure 구조)
# ==========================================

def get_transport_analysis(lat, lng):
    """
    [섹션 1] 교통망 분석
    Returns: dict (Always contains keys: subway_station, exit_info, subway_dist, walk_time, bus_stop_count, details)
    """
    # 1. 초기값 선언 (에러 발생 시 반환될 안전장치)
    # details는 빈 DataFrame이라도 반드시 컬럼을 가지고 있어야 함
    default_details = pd.DataFrame(columns=['place_name', 'distance', 'phone'])
    result = {
        "subway_station": "정보 없음",
        "exit_info": "",
        "subway_dist": 0,
        "walk_time": 0,
        "bus_stop_count": 0,
        "details": default_details
    }

    try:
        if not lat or not lng:
            return result

        # 2. 지하철역 검색
        sub_params = {"category_group_code": "SW8", "x": lng, "y": lat, "radius": 500, "sort": "distance"}
        subways = _call_kakao_local("category", sub_params)

        # 데이터 존재 여부 확인 (AttributeError 방지)
        if subways:
            nearest = subways[0]
            station_base_name = nearest.get('place_name', '').split()[0]
            
            # 출구 정밀 검색
            exit_params = {"query": f"{station_base_name} 출구", "x": lng, "y": lat, "radius": 500, "sort": "distance"}
            exits = _call_kakao_local("keyword", exit_params)
            
            target_obj = nearest
            exit_name = ""

            if exits:
                target_obj = exits[0]
                exit_name = _extract_exit_number(target_obj.get('place_name', ''))
                if not exit_name:
                    exit_name = target_obj.get('place_name', '')
            
            # 도보 계산 (안전 함수 호출)
            dist, time = _calculate_walking_data(lng, lat, target_obj.get('x'), target_obj.get('y'))
            
            result["subway_station"] = station_base_name
            result["exit_info"] = exit_name
            result["subway_dist"] = dist
            result["walk_time"] = time
            
            # 상세 테이블 생성 (데이터 존재 시에만)
            if len(subways) > 0:
                df = pd.DataFrame(subways)
                # 필요한 컬럼만 안전하게 추출
                cols = [c for c in ['place_name', 'distance', 'phone'] if c in df.columns]
                result["details"] = df[cols].head(5)

        # 3. 버스 정류장 검색
        bus_params = {"query": "버스정류장", "x": lng, "y": lat, "radius": 200}
        buses = _call_kakao_local("keyword", bus_params)
        result["bus_stop_count"] = len(buses)

    except Exception as e:
        print(f"[Transport Analysis Error] {e}")
        # 에러 발생 시 초기 선언된 result 반환 (앱 중단 방지)
        return result

    return result

def get_commercial_analysis(lat, lng):
    """
    [섹션 2] 상권 인프라 분석
    Returns: dict (Always contains keys: counts, anchors)
    """
    # 1. 초기값 선언
    default_counts = {k: 0 for k in ["음식점", "카페", "편의점", "은행", "병원"]}
    default_anchors = pd.DataFrame(columns=["브랜드", "지점명", "거리(m)", "도보(분)"])
    
    result = {
        "counts": default_counts,
        "anchors": default_anchors
    }

    try:
        if not lat or not lng:
            return result

        # 2. 5대 업종 카운트
        categories = {
            "음식점": "FD6", "카페": "CE7", "편의점": "CS2",
            "은행": "BK9", "병원": "HP8"
        }
        
        current_counts = {}
        for name, code in categories.items():
            params = {"category_group_code": code, "x": lng, "y": lat, "radius": 300}
            data = _call_kakao_local("category", params)
            current_counts[name] = len(data)
        
        result["counts"] = current_counts

        # 3. 앵커 시설 스캔
        anchors_list = []
        target_anchors = ["스타벅스", "맥도날드", "올리브영"]
        
        for anchor in target_anchors:
            params = {"query": anchor, "x": lng, "y": lat, "radius": 1000, "sort": "distance"}
            data = _call_kakao_local("keyword", params)
            
            if data:
                nearest = data[0]
                dist = int(nearest.get('distance', 0))
                anchors_list.append({
                    "브랜드": anchor,
                    "지점명": nearest.get('place_name', '정보없음'),
                    "거리(m)": dist,
                    "도보(분)": round(dist / 67, 1)
                })
            else:
                anchors_list.append({
                    "브랜드": anchor,
                    "지점명": "없음",
                    "거리(m)": "-",
                    "도보(분)": "-"
                })
        
        result["anchors"] = pd.DataFrame(anchors_list)

    except Exception as e:
        print(f"[Commercial Analysis Error] {e}")
        return result

    return result

def get_demand_analysis(lat, lng):
    """
    [섹션 3] 업무/생활 수요 분석
    Returns: pd.DataFrame (Always returns valid DataFrame, even if empty)
    """
    # 1. 초기값 선언 (빈 DataFrame이라도 컬럼 구조 유지 필수)
    columns = ["구분", "시설명", "거리(m)"]
    default_df = pd.DataFrame(columns=columns)

    try:
        if not lat or not lng:
            return default_df

        demand_list = []
        seen_places = set()

        # 2. 오피스/지식산업센터
        office_kws = ["지식산업센터", "오피스", "빌딩"]
        for kw in office_kws:
            params = {"query": kw, "x": lng, "y": lat, "radius": 500}
            places = _call_kakao_local("keyword", params)
            for p in places:
                p_id = p.get('id')
                if p_id and p_id not in seen_places:
                    demand_list.append({
                        "구분": "업무시설",
                        "시설명": p.get('place_name', ''),
                        "거리(m)": int(p.get('distance', 0))
                    })
                    seen_places.add(p_id)

        # 3. 교육 시설
        edu_codes = {"학교": "SC4", "학원": "AC5"}
        for name, code in edu_codes.items():
            params = {"category_group_code": code, "x": lng, "y": lat, "radius": 500}
            places = _call_kakao_local("category", params)
            for p in places:
                p_id = p.get('id')
                if p_id and p_id not in seen_places:
                    demand_list.append({
                        "구분": f"교육({name})",
                        "시설명": p.get('place_name', ''),
                        "거리(m)": int(p.get('distance', 0))
                    })
                    seen_places.add(p_id)

        # 4. 행정 시설
        admin_kws = ["주민센터", "우체국", "구청", "경찰서"]
        for kw in admin_kws:
            params = {"query": kw, "x": lng, "y": lat, "radius": 800}
            places = _call_kakao_local("keyword", params)
            for p in places:
                p_id = p.get('id')
                if p_id and p_id not in seen_places:
                    demand_list.append({
                        "구분": "행정/공공",
                        "시설명": p.get('place_name', ''),
                        "거리(m)": int(p.get('distance', 0))
                    })
                    seen_places.add(p_id)

        # 데이터가 있으면 DataFrame 생성 및 정렬
        if demand_list:
            df = pd.DataFrame(demand_list)
            df = df.sort_values(by="거리(m)").head(15).reset_index(drop=True)
            return df
        else:
            return default_df

    except Exception as e:
        print(f"[Demand Analysis Error] {e}")
        return default_df
