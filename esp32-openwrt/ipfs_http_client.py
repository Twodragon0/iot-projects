#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPFS HTTP Client
IPFS 네트워크에 데이터를 업로드하는 클라이언트 스크립트.

보안 고려사항:
- 파일 경로 검증
- 에러 처리 및 로깅
- 리소스 정리
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

try:
    import ipfshttpclient
except ImportError:
    print("ipfshttpclient가 설치되지 않았습니다.")
    print("설치 방법: pip3 install ipfshttpclient")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 설정 상수
DEFAULT_DATA_DIR = Path('data')
DEFAULT_IPFS_HOST = '/ip4/127.0.0.1/tcp/5001'


def validate_data_directory(data_dir: Path) -> bool:
    """
    데이터 디렉토리 유효성 검증
    
    Args:
        data_dir: 검증할 디렉토리 Path
        
    Returns:
        유효하면 True, 그렇지 않으면 False
    """
    if not data_dir.exists():
        logger.error(f"데이터 디렉토리가 존재하지 않습니다: {data_dir}")
        return False
    
    if not data_dir.is_dir():
        logger.error(f"데이터 디렉토리가 디렉토리가 아닙니다: {data_dir}")
        return False
    
    return True


def upload_to_ipfs(data_dir: Path, ipfs_host: Optional[str] = None) -> Optional[str]:
    """
    데이터 디렉토리를 IPFS에 업로드합니다.
    
    Args:
        data_dir: 업로드할 데이터 디렉토리 Path
        ipfs_host: IPFS 호스트 주소 (기본값: 로컬 IPFS 노드)
        
    Returns:
        IPFS 해시 문자열 또는 None (실패 시)
    """
    if not validate_data_directory(data_dir):
        return None
    
    ipfs_host = ipfs_host or os.getenv('IPFS_HOST', DEFAULT_IPFS_HOST)
    
    try:
        logger.info(f"IPFS 연결 시도: {ipfs_host}")
        logger.info(f"업로드 디렉토리: {data_dir.absolute()}")
        
        # IPFS 클라이언트 연결 (컨텍스트 매니저 사용)
        with ipfshttpclient.connect(ipfs_host) as client:
            # IPFS 노드 연결 확인
            try:
                client.version()
                logger.info("IPFS 노드 연결 성공")
            except Exception as e:
                logger.error(f"IPFS 노드 연결 실패: {e}")
                logger.error("IPFS daemon이 실행 중인지 확인하세요: ipfs daemon")
                return None
            
            # 데이터 디렉토리 업로드
            logger.info("데이터 업로드 중...")
            result = client.add(str(data_dir), recursive=True)
            
            if not result:
                logger.error("업로드 결과가 비어있습니다")
                return None
            
            # 마지막 항목의 해시 가져오기 (디렉토리 업로드 시)
            ipfs_hash = result[-1]['Hash']
            logger.info(f"IPFS 해시: {ipfs_hash}")
            
            # 업로드된 데이터 통계 확인
            try:
                stat = client.stat(ipfs_hash)
                logger.info(f"업로드된 데이터 크기: {stat.get('CumulativeSize', 'N/A')} bytes")
            except Exception as e:
                logger.warning(f"통계 조회 실패: {e}")
            
            return ipfs_hash
            
    except ipfshttpclient.exceptions.ConnectionError as e:
        logger.error(f"IPFS 연결 오류: {e}")
        logger.error("IPFS daemon이 실행 중인지 확인하세요: ipfs daemon")
        return None
    except Exception as e:
        logger.error(f"IPFS 업로드 중 오류: {e}")
        return None


class IPFSClient:
    """
    IPFS 클라이언트 클래스
    세션을 유지하면서 여러 작업을 수행할 때 사용
    """
    
    def __init__(self, ipfs_host: Optional[str] = None):
        """
        IPFS 클라이언트 초기화
        
        Args:
            ipfs_host: IPFS 호스트 주소
        """
        self.ipfs_host = ipfs_host or os.getenv('IPFS_HOST', DEFAULT_IPFS_HOST)
        self._client: Optional[ipfshttpclient.Client] = None
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self._client = ipfshttpclient.connect(self.ipfs_host, session=True)
        logger.info(f"IPFS 세션 시작: {self.ipfs_host}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if self._client:
            self._client.close()
            logger.info("IPFS 세션 종료")
    
    def upload(self, data_path: Path) -> Optional[str]:
        """
        데이터를 IPFS에 업로드
        
        Args:
            data_path: 업로드할 파일/디렉토리 Path
            
        Returns:
            IPFS 해시 또는 None
        """
        if not self._client:
            raise RuntimeError("IPFS 클라이언트가 초기화되지 않았습니다")
        
        try:
            result = self._client.add(str(data_path), recursive=True)
            if result:
                ipfs_hash = result[-1]['Hash']
                logger.info(f"업로드 완료: {ipfs_hash}")
                return ipfs_hash
        except Exception as e:
            logger.error(f"업로드 실패: {e}")
            return None
    
    def get_stat(self, ipfs_hash: str) -> Optional[dict]:
        """
        IPFS 해시의 통계 정보 조회
        
        Args:
            ipfs_hash: IPFS 해시
            
        Returns:
            통계 정보 딕셔너리 또는 None
        """
        if not self._client:
            raise RuntimeError("IPFS 클라이언트가 초기화되지 않았습니다")
        
        try:
            return self._client.stat(ipfs_hash)
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return None


def main() -> None:
    """메인 함수"""
    # 환경 변수에서 데이터 디렉토리 읽기
    data_dir = Path(os.getenv('DATA_DIR', DEFAULT_DATA_DIR))
    
    # IPFS 업로드
    ipfs_hash = upload_to_ipfs(data_dir)
    
    if ipfs_hash:
        print(f"\n✅ 업로드 성공!")
        print(f"IPFS 해시: {ipfs_hash}")
        print(f"IPFS Gateway URL: https://ipfs.io/ipfs/{ipfs_hash}")
    else:
        print("\n❌ 업로드 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
