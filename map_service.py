def fetch_map_image(lat, lng, zoom_level=16, height=300):
    """
    위도, 경도, 줌 레벨, 높이를 받아 정적 지도 이미지(Binary)를 반환합니다.
    """
    if not lat or not lng:
        return None
    
    # VPC Endpoint 강제 적용
    url = "https://maps.apigw.ntruss.com/map-static/v2/raster"
    
    headers = {
        "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
        "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET
    }
    
    # [안전장치] 네이버 API 최대 한계치인 1024를 넘지 않도록 조정
    safe_height = min(int(height), 1024)
    
    # 지도 옵션 설정 (가로 너비도 1000으로 확장하여 더 시원하게 출력)
    params = {
        "w": "1000",
        "h": str(safe_height), 
        "center": f"{lng},{lat}",
        "level": str(zoom_level),
        "markers": f"type:t|size:mid|pos:{lng} {lat}|label:매물",
        "scale": "2" # 고해상도 디스플레이 대응
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"Naver Static Map API Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Map Fetch Internal Error: {e}")
        return None
