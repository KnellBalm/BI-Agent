import base64
import json
from typing import Any, Dict

class VisualDecoder:
    """
    BI 레포트의 `etc` 필드(Base64 인코딩된 JSON)를 디코딩하고 다시 인코딩하는 클래스
    """
    @staticmethod
    def decode_etc(base64_str: str) -> Dict[str, Any]:
        """
        Base64 문자열을 디코딩하여 Python 딕셔너리로 반환합니다.
        """
        if not base64_str:
            return {}
        
        try:
            decoded_bytes = base64.b64decode(base64_str)
            decoded_str = decoded_bytes.decode('utf-8')
            return json.loads(decoded_str)
        except Exception as e:
            print(f"Error decoding etc field: {e}")
            return {}

    @staticmethod
    def encode_etc(data: Dict[str, Any]) -> str:
        """
        Python 딕셔너리를 JSON 문자열로 변환 후 Base64로 인코딩합니다.
        """
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            encoded_bytes = base64.b64encode(json_str.encode('utf-8'))
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Error encoding etc field: {e}")
            return ""

if __name__ == "__main__":
    # 테스트
    test_data = {"size": {"width": 1450, "height": 0}, "isShowTitle": False}
    encoded = VisualDecoder.encode_etc(test_data)
    print(f"Encoded: {encoded}")
    decoded = VisualDecoder.decode_etc(encoded)
    print(f"Decoded: {decoded}")
