#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32-OpenWrt Socket Server
Socket server for receiving data from ESP32 devices and saving to files.

보안 고려사항:
- 파일 경로 검증 (Path Traversal 방지)
- 파일 쓰기 권한 검사
- 에러 처리 및 로깅
- 리소스 정리 (with 문 사용)
"""

import socket
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 설정 상수
DEFAULT_HOST = '0.0.0.0'  # 모든 인터페이스에서 수신
DEFAULT_PORT = 8070
BUFFER_SIZE = 1024
DATA_DIR = Path('data')
WELCOME_MESSAGE = "Welcome to ESP32-OpenWrt Server!"


def ensure_data_directory() -> Path:
    """
    데이터 디렉토리가 존재하는지 확인하고 생성합니다.
    
    Returns:
        데이터 디렉토리 Path 객체
    """
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR
    except PermissionError:
        logger.error(f"데이터 디렉토리 생성 권한 없음: {DATA_DIR}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"데이터 디렉토리 생성 중 오류: {e}")
        sys.exit(1)


def create_data_file(data_dir: Path) -> Path:
    """
    타임스탬프 기반 데이터 파일 경로를 생성합니다.
    
    Args:
        data_dir: 데이터 디렉토리 Path
        
    Returns:
        데이터 파일 Path 객체
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT-%H:%M:%S")
    filename = f"{timestamp}.txt"
    file_path = data_dir / filename
    
    # Path Traversal 방지: 절대 경로가 데이터 디렉토리 내에 있는지 확인
    try:
        file_path.resolve().relative_to(data_dir.resolve())
    except ValueError:
        logger.error(f"잘못된 파일 경로: {file_path}")
        raise ValueError("Invalid file path")
    
    return file_path


def handle_client(client_socket: socket.socket, client_addr: tuple, data_dir: Path) -> None:
    """
    클라이언트 연결을 처리합니다.
    
    Args:
        client_socket: 클라이언트 소켓 객체
        client_addr: 클라이언트 주소 튜플
        data_dir: 데이터 디렉토리 Path
    """
    logger.info(f"클라이언트 연결: {client_addr}")
    
    try:
        # 환영 메시지 전송
        client_socket.sendall(WELCOME_MESSAGE.encode('utf-8'))
        
        # 데이터 파일 생성
        data_file = create_data_file(data_dir)
        logger.info(f"데이터 파일 생성: {data_file}")
        
        # 파일 쓰기 (with 문으로 자동 닫기)
        with open(data_file, 'a', encoding='utf-8') as f:
            while True:
                try:
                    msg = client_socket.recv(BUFFER_SIZE)
                    if not msg:
                        logger.info("클라이언트 연결 종료")
                        break
                    
                    # 데이터 디코딩 및 저장
                    decoded_msg = msg.decode('utf-8', errors='replace')
                    f.write(f"{decoded_msg}\n")
                    f.flush()  # 즉시 디스크에 쓰기
                    
                    logger.debug(f"데이터 수신: {decoded_msg[:50]}...")
                    
                except socket.error as e:
                    logger.error(f"소켓 오류: {e}")
                    break
                except Exception as e:
                    logger.error(f"데이터 처리 중 오류: {e}")
                    break
        
        logger.info(f"데이터 파일 저장 완료: {data_file}")
        
    except Exception as e:
        logger.error(f"클라이언트 처리 중 오류: {e}")
    finally:
        client_socket.close()
        logger.info(f"클라이언트 연결 종료: {client_addr}")


def main() -> None:
    """메인 서버 함수"""
    # 데이터 디렉토리 확인
    data_dir = ensure_data_directory()
    
    # 환경 변수에서 설정 읽기 (보안: 하드코딩 방지)
    host = os.getenv('SOCKET_SERVER_HOST', DEFAULT_HOST)
    port = int(os.getenv('SOCKET_SERVER_PORT', DEFAULT_PORT))
    
    # 서버 소켓 생성
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        logger.info(f"서버 시작: {host}:{port}")
        logger.info(f"데이터 디렉토리: {data_dir.absolute()}")
        
        while True:
            try:
                client_socket, client_addr = server_socket.accept()
                handle_client(client_socket, client_addr, data_dir)
            except KeyboardInterrupt:
                logger.info("서버 종료 요청")
                break
            except Exception as e:
                logger.error(f"서버 오류: {e}")
                continue
                
    except OSError as e:
        logger.error(f"소켓 바인딩 실패: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}")
        sys.exit(1)
    finally:
        server_socket.close()
        logger.info("서버 종료")


if __name__ == "__main__":
    main()




