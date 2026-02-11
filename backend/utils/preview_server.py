"""
PreviewServer - 로컬 웹 대시보드 미리보기 서버

Step 13: Draft Briefing의 핵심 컴포넌트
Flask 기반 localhost:5000 서버로 생성된 HTML 대시보드를 서빙합니다.
"""

import os
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any
from flask import Flask, render_template_string, send_file, jsonify
import threading
import logging
from backend.utils.path_config import path_manager


# Flask 로깅 레벨 설정
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


class PreviewServer:
    """
    로컬 HTTP 서버로 대시보드 미리보기 제공

    주요 기능:
    1. Flask 서버 기동 (localhost:5000)
    2. 생성된 HTML 대시보드 서빙
    3. 자동 브라우저 오픈
    4. 리포트 목록 관리
    """

    def __init__(self, host: str = "localhost", port: int = 5000):
        """
        Args:
            host: 서버 호스트 (기본: localhost)
            port: 서버 포트 (기본: 5000)
        """
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.reports: Dict[str, str] = {}  # report_id -> file_path
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False

        self._setup_routes()

    def _setup_routes(self):
        """Flask 라우트 설정"""

        @self.app.route('/')
        def index():
            """메인 페이지: 리포트 목록"""
            report_list = [
                {"id": rid, "path": path, "name": os.path.basename(path)}
                for rid, path in self.reports.items()
            ]

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>BI-Agent Preview Server</title>
                <meta charset="utf-8">
                <style>
                    :root {{
                        --bg: #0f172a;
                        --card: #1e293b;
                        --accent: #38bdf8;
                        --text: #f8fafc;
                        --text-dim: #94a3b8;
                    }}
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: var(--bg);
                        color: var(--text);
                        padding: 60px 40px;
                        margin: 0;
                    }}
                    .container {{ max-width: 1200px; margin: auto; }}
                    h1 {{
                        color: var(--accent);
                        font-size: 2.5rem;
                        margin-bottom: 10px;
                        font-weight: 700;
                    }}
                    .subtitle {{
                        color: var(--text-dim);
                        font-size: 1.1rem;
                        margin-bottom: 40px;
                    }}
                    .report-card {{
                        background: var(--card);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 12px;
                        padding: 24px;
                        margin-bottom: 20px;
                        transition: all 0.2s;
                        cursor: pointer;
                    }}
                    .report-card:hover {{
                        border-color: var(--accent);
                        transform: translateY(-2px);
                        box-shadow: 0 8px 20px rgba(56, 189, 248, 0.15);
                    }}
                    .report-name {{
                        color: var(--accent);
                        font-size: 1.3rem;
                        font-weight: 600;
                        margin-bottom: 8px;
                    }}
                    .report-id {{
                        color: var(--text-dim);
                        font-size: 0.9rem;
                        font-family: monospace;
                    }}
                    .empty-state {{
                        text-align: center;
                        padding: 80px 20px;
                        color: var(--text-dim);
                    }}
                    .empty-state svg {{
                        width: 120px;
                        height: 120px;
                        margin-bottom: 20px;
                        opacity: 0.3;
                    }}
                    .badge {{
                        display: inline-block;
                        padding: 6px 12px;
                        background: rgba(56, 189, 248, 0.1);
                        color: var(--accent);
                        border-radius: 6px;
                        font-size: 0.85rem;
                        font-weight: 600;
                        margin-bottom: 30px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <span class="badge">🚀 RUNNING ON {self.host}:{self.port}</span>
                    <h1>📊 BI-Agent Preview Server</h1>
                    <p class="subtitle">생성된 분석 리포트를 미리보기 할 수 있습니다</p>

                    {''.join([f'''
                    <div class="report-card" onclick="window.location.href='/preview/{r["id"]}'">
                        <div class="report-name">{r["name"]}</div>
                        <div class="report-id">ID: {r["id"]}</div>
                    </div>
                    ''' for r in report_list]) if report_list else '''
                    <div class="empty-state">
                        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                        <h2>리포트가 아직 없습니다</h2>
                        <p>TUI에서 분석을 실행하면 여기에 표시됩니다</p>
                    </div>
                    '''}
                </div>
            </body>
            </html>
            """
            return render_template_string(html)

        @self.app.route('/preview/<report_id>')
        def preview_report(report_id: str):
            """특정 리포트 미리보기"""
            if report_id not in self.reports:
                return jsonify({"error": "Report not found"}), 404

            file_path = self.reports[report_id]
            if not os.path.exists(file_path):
                return jsonify({"error": "Report file not found"}), 404

            return send_file(file_path)

        @self.app.route('/api/reports')
        def list_reports():
            """리포트 목록 API"""
            return jsonify({
                "reports": [
                    {"id": rid, "path": path, "name": os.path.basename(path)}
                    for rid, path in self.reports.items()
                ]
            })

    def register_report(self, report_id: str, file_path: str) -> str:
        """
        리포트 등록

        Args:
            report_id: 리포트 고유 ID
            file_path: HTML 파일 경로

        Returns:
            미리보기 URL
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Report file not found: {file_path}")

        self.reports[report_id] = file_path
        return f"http://{self.host}:{self.port}/preview/{report_id}"

    def start(self, open_browser: bool = False, daemon: bool = True):
        """
        서버 시작

        Args:
            open_browser: 시작 시 브라우저 자동 오픈 여부
            daemon: 데몬 스레드로 실행 여부
        """
        if self.is_running:
            print(f"[PreviewServer] Already running on http://{self.host}:{self.port}")
            return

        def run_server():
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )

        self.server_thread = threading.Thread(target=run_server, daemon=daemon)
        self.server_thread.start()
        self.is_running = True

        print(f"[PreviewServer] Started at http://{self.host}:{self.port}")

        if open_browser:
            self.open_browser()

    def open_browser(self, report_id: Optional[str] = None):
        """
        브라우저 오픈

        Args:
            report_id: 특정 리포트 ID (None이면 메인 페이지)
        """
        if report_id:
            url = f"http://{self.host}:{self.port}/preview/{report_id}"
        else:
            url = f"http://{self.host}:{self.port}/"

        try:
            webbrowser.open(url)
            print(f"[PreviewServer] Opened browser: {url}")
        except Exception as e:
            print(f"[PreviewServer] Failed to open browser: {e}")

    def stop(self):
        """서버 중지"""
        # Flask 서버는 데몬 스레드로 실행되므로 메인 프로세스 종료 시 자동 종료
        self.is_running = False
        print("[PreviewServer] Stopped")

    def get_url(self, report_id: Optional[str] = None) -> str:
        """
        URL 반환

        Args:
            report_id: 리포트 ID (None이면 메인 페이지)

        Returns:
            URL 문자열
        """
        if report_id:
            return f"http://{self.host}:{self.port}/preview/{report_id}"
        return f"http://{self.host}:{self.port}/"


# 글로벌 싱글톤 인스턴스
_preview_server_instance: Optional[PreviewServer] = None


def get_preview_server() -> PreviewServer:
    """
    PreviewServer 싱글톤 인스턴스 반환

    Returns:
        PreviewServer 인스턴스
    """
    global _preview_server_instance
    if _preview_server_instance is None:
        _preview_server_instance = PreviewServer()
    return _preview_server_instance


# 사용 예시
if __name__ == "__main__":
    # 테스트용 코드
    server = get_preview_server()
    server.start(open_browser=True)

    # 임시 리포트 등록 (실제로는 DashboardGenerator가 생성한 파일 사용)
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head><title>Test Report</title></head>
        <body>
            <h1>테스트 리포트</h1>
            <p>이것은 테스트 리포트입니다.</p>
        </body>
        </html>
        """)
        temp_path = f.name

    url = server.register_report("test-001", temp_path)
    print(f"Report URL: {url}")

    # 서버 실행 유지 (Ctrl+C로 종료)
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        os.unlink(temp_path)
