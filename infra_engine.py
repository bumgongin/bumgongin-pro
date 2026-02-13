import requests
import pandas as pd
import re
import math

# ==========================================
# 1. API 환경 설정 (보안 및 VPC 규격 준수)
# ==========================================

# [NAVER Enterprise VPC 설정]
# 일반 공공 API와 달리 VPC 게이트웨이는 헤더 대소문자를 엄격하게 구분할 수 있으므로 소문자 강제 적용
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
# 2. 유틸리티 함수 (내부 로직)
# ==========================================

def _call_kakao_local(endpoint, params):
    """카카오 로컬 API 호출 래퍼 (예외 처리 및 타임아웃 적용)"""
    url = f"https://dapi.kakao.com/v2/local/search/{endpoint}.json"
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            return response.json().get('documents', [])
        return []
    except Exception:
        # 연결 실패, 타임아웃 등 모든 에러에 대해 빈 리스트 반환하여 앱 멈춤 방지
        return []

def _extract_exit_number(place_name):
    """정규표현식을 이용해 역 이름에서 출구 번호 추출"""
    if not place_name:
        return ""
    # 예: "강남역 2호선 1번출구" -> "1번출구" 추출
    match = re.search(r'(\d+번\s?출구)', place_name)
    if match:
        return match.group(1)
    return ""

def _calculate_walking_data(origin_x, origin_y, dest_x, dest_y):
    """
    도보 거리 및 시간 계산 로직
    1. 카카오 Mobility API 시도
    2. 실패 시 직선 거리 기반 보정 공식(1.25배) 적용 (Fallback)
    """
    # 1. Mobility API (Directions) 시도
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    params = {
        "origin": f"{origin_x},{origin_y}",
        "destination": f"{dest_x},{dest_y}",
        "priority": "RECOMMEND",
        "car_type": 1  # 도보 전용 옵션이 없으므로 최단 경로 참조용
    }
    
    dist_m = 0
    time_min = 0
    
    try:
        response = requests.get(url, headers=KAKAO_HEADERS, params=params, timeout=TIMEOUT_SEC)
        if response.status_code == 200:
            routes = response.json().get('routes', [])
            if routes:
                summary = routes[0].get('summary', {})
                dist_m = summary.get('distance', 0)
                # 자동차 기준이라도 경로 거리는 유의미함, 도보 속도로 재환산
                # 성인 평균 보폭 분속 67m
                time_min = round(dist_m / 67, 1)
                return dist_m, time_min
    except Exception:
        pass # 실패 시 아래 Fallback 로직 수행

    # 2. Fallback: 직선 거리 기반 보정 공식 적용
    # 간단한 유클리드 거리 근사치 계산 (대한민국 위도 기준 약식)
    # 카카오에서 제공하는 직선거리(distance 필드)가 있다면 그것을 쓰는 것이 좋으나,
    # 좌표만으로 계산해야 할 경우를 대비해 Haversine 대신 약식 계산
    try:
        dx = (float(dest_x) - float(origin_x)) * 88000  # 경도 1도 ≈ 88km (서울 기준)
        dy = (float(dest_y) - float(origin_y)) * 111000 # 위도 1도 ≈ 111km
        straight_dist = math.sqrt(dx**2 + dy**2)
        
        # 보정 계수 1.25배 적용 (도로 굴곡 반영)
        dist_m = int(straight_dist * 1.25)
        time_min = round(dist_m / 67, 1) # 67m/min
    except Exception:
        dist_m, time_min = 0, 0

    return dist_m, time_min

# ==========================================
# 3. 핵심 분석 함수 (온디맨드)
# ==========================================

def get_transport_analysis(lat, lng):
    """
    [섹션 1] 교통망 분석
    - 지하철역(SW8) 및 출구 번호 파싱
    - 도보 시간 및 거리 계산
    - 버스 정류장 밀집도
    """
    result = {
        "subway_station": "정보 없음",
        "exit_info": "",
        "subway_dist": 0,
        "walk_time": 0,
        "bus_stop_count": 0,
        "details": pd.DataFrame()
    }

    try:
        # 1. 지하철역 검색 (반경 500m)
        sub_params = {"category_group_code": "SW8", "x": lng, "y": lat, "radius": 500, "sort": "distance"}
        subways = _call_kakao_local("category", sub_params)

        if subways:
            nearest = subways[0]
            # 출구 정보 파싱 시도 (이름에 포함되어 있는지 확인)
            # 만약 역 이름만 있고 출구가 없다면, 가장 가까운 출구를 찾기 위해 키워드 재검색 가능하나
            # 성능을 위해 현재 결과의 place_name 분석을 우선함
            station_base_name = nearest['place_name'].split()[0] # "강남역"
            
            # 정밀한 출구 검색을 위해 키워드 검색 추가 실행 (예: 강남역 출구)
            exit_params = {"query": f"{station_base_name} 출구", "x": lng, "y": lat, "radius": 500, "sort": "distance"}
            exits = _call_kakao_local("keyword", exit_params)
            
            target_obj = nearest
            exit_name = ""

            if exits:
                # 가장 가까운 것이 '출구' 데이터라면 교체
                target_obj = exits[0]
                exit_name = _extract_exit_number(target_obj['place_name'])
                if not exit_name: # 정규식 실패 시 이름 그대로 사용
                    exit_name = target_obj['place_name']
            
            # 도보 계산
            dist, time = _calculate_walking_data(lng, lat, target_obj['x'], target_obj['y'])
            
            result["subway_station"] = station_base_name
            result["exit_info"] = exit_name
            result["subway_dist"] = dist
            result["walk_time"] = time
            
            # 상세 테이블
            df = pd.DataFrame(subways)
            if not df.empty:
                result["details"] = df[['place_name', 'distance', 'phone']].head(5)

        # 2. 버스 정류장 검색 (반경 200m)
        bus_params = {"query": "버스정류장", "x": lng, "y": lat, "radius": 200}
        buses = _call_kakao_local("keyword", bus_params)
        result["bus_stop_count"] = len(buses)

    except Exception as e:
        print(f"[Transport Error] {e}")

    return result

def get_commercial_analysis(lat, lng):
    """
    [섹션 2] 상권 인프라 분석
    - 5대 업종(음식, 카페, 편의점, 은행, 병원) 수량
    - 주요 앵커 시설 거리 (스타벅스, 맥도날드, 올리브영)
    """
    counts = {}
    anchors = []

    try:
        # 1. 5대 업종 카운트 (반경 300m - 상권 밀집도)
        categories = {
            "음식점": "FD6", "카페": "CE7", "편의점": "CS2",
            "은행": "BK9", "병원": "HP8"
        }
        
        for name, code in categories.items():
            params = {"category_group_code": code, "x": lng, "y": lat, "radius": 300}
            data = _call_kakao_local("category", params)
            counts[name] = len(data)

        # 2. 앵커 시설 스캔 (반경 1km)
        target_anchors = ["스타벅스", "맥도날드", "올리브영"]
        for anchor in target_anchors:
            params = {"query": anchor, "x": lng, "y": lat, "radius": 1000, "sort": "distance"}
            data = _call_kakao_local("keyword", params)
            
            if data:
                nearest = data[0]
                dist = int(nearest.get('distance', 0))
                anchors.append({
                    "브랜드": anchor,
                    "지점명": nearest['place_name'],
                    "거리(m)": dist,
                    "도보(분)": round(dist / 67, 1) # 단순 계산
                })
            else:
                anchors.append({
                    "브랜드": anchor,
                    "지점명": "없음",
                    "거리(m)": "-",
                    "도보(분)": "-"
                })

    except Exception as e:
        print(f"[Commercial Error] {e}")

    return {
        "counts": counts,
        "anchors": pd.DataFrame(anchors)
    }

def get_demand_analysis(lat, lng):
    """
    [섹션 3] 업무/생활 수요 분석
    - 오피스/지식산업센터 (직장인 수요)
    - 교육 및 행정 시설 (유동 인구)
    """
    demand_list = []

    try:
        # 1. 오피스/지식산업센터/빌딩 (반경 500m)
        office_kws = ["지식산업센터", "오피스", "빌딩"]
        seen_places = set() # 중복 제거용

        for kw in office_kws:
            params = {"query": kw, "x": lng, "y": lat, "radius": 500}
            places = _call_kakao_local("keyword", params)
            for p in places:
                if p['id'] not in seen_places:
                    demand_list.append({
                        "구분": "업무시설",
                        "시설명": p['place_name'],
                        "거리(m)": int(p['distance'])
                    })
                    seen_places.add(p['id'])

        # 2. 교육 시설 (학교 SC4, 학원 AC5)
        edu_codes = {"학교": "SC4", "학원": "AC5"}
        for name, code in edu_codes.items():
            params = {"category_group_code": code, "x": lng, "y": lat, "radius": 500}
            places = _call_kakao_local("category", params)
            for p in places:
                if p['id'] not in seen_places:
                    demand_list.append({
                        "구분": f"교육({name})",
                        "시설명": p['place_name'],
                        "거리(m)": int(p['distance'])
                    })
                    seen_places.add(p['id'])

        # 3. 행정 시설 (주민센터, 우체국, 구청) - 반경 800m
        admin_kws = ["주민센터", "우체국", "구청", "경찰서"]
        for kw in admin_kws:
            params = {"query": kw, "x": lng, "y": lat, "radius": 800}
            places = _call_kakao_local("keyword", params)
            for p in places:
                if p['id'] not in seen_places:
                    demand_list.append({
                        "구분": "행정/공공",
                        "시설명": p['place_name'],
                        "거리(m)": int(p['distance'])
                    })
                    seen_places.add(p['id'])

    except Exception as e:
        print(f"[Demand Error] {e}")

    # DataFrame 변환 및 거리순 정렬
    df = pd.DataFrame(demand_list)
    if not df.empty:
        df = df.sort_values(by="거리(m)").head(15).reset_index(drop=True)
    
    return df
