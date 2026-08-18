# 보안 정책

## 인증 정보 저장

Smart Solity 계정 비밀번호는 저장하지 않습니다. 로그인 후 발급된 이메일, 세션
토큰, 토큰 비밀번호와 로컬 기기 식별값만 Home Assistant의 로컬 config entry에
저장합니다. 이 값은 Smart Solity API 인증에만 사용되며 GitHub, GitHub Actions,
분석 서비스 또는 로그로 전송되지 않습니다.

실제 Home Assistant 설정 파일, `.storage`, `secrets.yaml`, `configuration.yaml`,
환경 변수 파일과 로그는 `.gitignore`에서 제외합니다. 보안 문제를 발견하면 실제
토큰, 비밀번호 또는 PIN을 GitHub Issue에 첨부하지 마세요.

## 취약점 신고

공개 Issue에는 재현 절차와 민감정보를 제거한 로그만 작성해 주세요. 실제 자격
증명이 노출됐다면 먼저 Smart Solity 계정 비밀번호를 변경하고 통합을 재인증하세요.

---

# Security policy

## Credential storage

The Smart Solity account password is never stored. Only the email, issued session
tokens, token password, and local device identifier are stored in Home Assistant's
local config entry. They are used only to authenticate with the Smart Solity API
and are not sent to GitHub, GitHub Actions, analytics services, or logs.

Real Home Assistant configuration files, `.storage`, `secrets.yaml`,
`configuration.yaml`, environment files, and logs are excluded by `.gitignore`.
Never attach real tokens, passwords, or PINs to a GitHub issue.

## Reporting a vulnerability

Public issues should contain only reproduction steps and redacted logs. If a real
credential was exposed, change the Smart Solity account password and reauthenticate
the integration first.
