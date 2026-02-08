# Current Session

## 상태: M4 완료, M5 대기

## 완료된 작업
- [x] 아이디어 검증 (Phase 1-6)
- [x] Obsidian 프로젝트 명세 작성
- [x] GitHub 리포 생성 (public)
- [x] Python 프로젝트 구조 세팅 (pyproject.toml)
- [x] claude-discord-bot 코드 분석 → Python 코어 모듈 포팅
- [x] Config 로딩 시스템 (.env + python-dotenv)
- [x] Claude CLI runner (claude -p subprocess)
- [x] Session store, message splitter, file handler, security
- [x] Discord bot (SecondBrainBot + ChatCog + AdminCog)
- [x] CI/CD 설정 (GitHub Actions: ruff + mypy)
- [x] 코어 모듈 유닛 테스트 72개 작성 (6개 모듈 커버)
- [x] __main__.py 추가
- [x] 봇 실행 테스트 (로컬 환경)
- [x] Claude CLI 연동 검증 (메시지 → Claude → 응답 루프)
- [x] 응답 로깅 추가
- [x] CLI 타임아웃/에러 핸들링 강화
- [x] 메시지 분할 검증 (2000자 제한, 코드블록 존중)
- [x] 파일 첨부/전송 검증
- [x] 테스트 수정
- [x] Vault 매니저: Note dataclass + VaultManager (read/write/list)
- [x] YAML frontmatter 파싱/생성 (pyyaml)
- [x] 검색 기능 (파일명/태그/전문 검색, find_by_tags)
- [x] all_tags(): vault 전체 태그 빈도 맵
- [x] auto_tag(): Claude 기반 자동 태그 제안
- [x] VaultCog: /search, /notes, /tags, /save, /autotag 슬래시 커맨드
- [x] Vault 테스트 36개 (전체 108개, 모두 통과)
- [x] MCPServerDef 데이터 클래스 + 3개 MCP 레지스트리 (Google Calendar, Todoist, RSS Reader)
- [x] MCPManager: ~/.claude.json mcpServers 읽기/쓰기/설치/제거
- [x] MCPCog: /mcp list, /mcp install, /mcp remove, /mcp status 슬래시 커맨드 (autocomplete 포함)
- [x] MCP 테스트 28개 (전체 136개, 모두 통과)

## 기술 결정
- Python 유지 (기존 claude-discord-bot과 동일 스택)
- Claude Code CLI만 사용 (Anthropic SDK 제거 — vault/MCP 접근에 CLI 필수)
- 기존 봇은 개인 개발용으로 유지, 코어만 second-brain-kit으로 포팅
- auto_tag은 haiku 모델로 비용 최소화
- VaultManager는 동기 I/O (vault 크기가 작으므로 충분)
- MCP "설치"는 실제 npm install이 아닌 ~/.claude.json에 엔트리 추가 (npx -y로 온디맨드 실행)
- MCP 설정 위저드는 Discord slash command의 optional env 파라미터로 구현

## 다음 작업
- [ ] M5: CLI 인스톨러 (Linux, Obsidian 설치 확인, vault 구조 생성, systemd 등록)

## 주의사항
- Claude Code CLI가 로컬에 설치되어 있어야 동작
- Owner-only 보안 모델 (단일 사용자)
- auto_tag은 Claude API 호출 → haiku 사용으로 비용 최소화했지만 빈번 사용 시 비용 주의
- MCP install은 ~/.claude.json을 수정 → Claude Code 재시작 필요
