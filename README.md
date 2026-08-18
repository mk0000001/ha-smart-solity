# Home Assistant용 Smart Solity

Smart Solity 모바일 앱에 등록된 도어락을 Home Assistant에서 사용하는 비공식
사용자 통합 구성 요소입니다.

> 이 프로젝트는 Solity의 공식 프로젝트가 아니며, 문서화되지 않은 Smart Solity
> 클라우드 API를 사용합니다.

## 주요 기능

- 잠금 엔티티에서 잠금 및 잠금 해제
- 30초 간격 상태 확인
- 배터리 잔량 센서
- 한 계정에 등록된 여러 도어락 지원
- 만료된 세션의 자동 재발급 및 토큰 교체
- 한국어 및 영어 설정 화면
- 사용자 목록 조회 및 관리자/구성원 초대
- 기간제, 요일 반복, 일회용 방문자 비밀번호 생성
- 최근 출입 및 경보 기록 조회
- PIN, 카드, 지문, 얼굴, 이중 인증 지원 여부 표시

## HACS 설치

1. HACS의 **통합 구성 요소**에서 **사용자 지정 저장소**를 엽니다.
2. `https://github.com/mk0000001/ha-smart-solity`를 **통합 구성 요소** 유형으로
   추가합니다.
3. **Smart Solity**를 설치하고 Home Assistant를 재시작합니다.
4. **설정 → 기기 및 서비스 → 통합 구성 요소 추가**에서 **Smart Solity**를
   검색한 뒤 모바일 앱과 같은 계정으로 로그인합니다.

## 수동 설치

`custom_components/smart_solity` 폴더를 Home Assistant 설정 디렉터리의
`custom_components`에 복사하고 Home Assistant를 재시작합니다.

## 인증 정보와 개인정보

- 이메일, 세션 토큰, 토큰 비밀번호 및 로컬 기기 식별값은 Home Assistant의 로컬
  config entry에만 저장됩니다.
- 계정 비밀번호는 로그인 요청에만 사용되며 통합에서 저장하지 않습니다.
- 인증 값은 Smart Solity API 인증에만 사용되며, 저장소·GitHub Actions·분석
  서비스 또는 로그로 보내는 코드는 없습니다.
- Home Assistant 백업에는 로컬 config entry가 포함될 수 있으므로 백업 파일을
  안전하게 보관하세요.
- 방문자 PIN은 통합에서 저장하지 않지만 자동화·스크립트 추적 기록에는 입력값이
  남을 수 있습니다. 민감한 PIN은 수동 실행하거나 추적 보존을 제한하세요.

자세한 내용은 [보안 정책](SECURITY.md)을 확인하세요.

---

# Smart Solity for Home Assistant

An unofficial Home Assistant custom integration for door locks registered in the
Smart Solity mobile app.

> This project is not affiliated with Solity and uses an undocumented Smart
> Solity cloud API.

## Features

- Lock and unlock from a Home Assistant lock entity
- Door-lock state polling every 30 seconds
- Battery percentage sensor
- Multiple locks on one Smart Solity account
- Automatic session reissue and token rotation
- Korean and English setup UI
- List users and invite managers or members
- Create date-range, weekly, and one-time visitor PINs
- Retrieve recent access and alarm events
- Capability attributes for PIN, card, fingerprint, face, and dual authentication

## Install with HACS

1. In HACS **Integrations**, open **Custom repositories**.
2. Add `https://github.com/mk0000001/ha-smart-solity` with the **Integration**
   category.
3. Install **Smart Solity** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, search for
   **Smart Solity**, and sign in with the same account as the mobile app.

## Manual installation

Copy `custom_components/smart_solity` into the `custom_components` directory in
your Home Assistant configuration directory, then restart Home Assistant.

## Credentials and privacy

- Email, session tokens, token password, and the local device identifier stay in
  the local Home Assistant config entry.
- The account password is used only for the login request and is never stored by
  the integration.
- Credentials are used only to authenticate with the Smart Solity API. No code
  uploads them to the repository, GitHub Actions, analytics services, or logs.
- Home Assistant backups may contain the local config entry; protect backup files.
- Visitor PINs are not stored by the integration, but automation and script traces
  may retain inputs. Run sensitive PIN actions manually or limit trace retention.

See [SECURITY.md](SECURITY.md) for details.
