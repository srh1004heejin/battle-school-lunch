# GitHub Actions 활용한 CI/CD 파이프라인 구현하기

azd CLI를 활용해서 앱을 배포할 수 있는 CI/CD 파이프라인을 구현합니다. 여기에는 Bicep 파일 생성을 통한 Azure 인프라 구성도 포함합니다.

## 인수 조건

- [ ] Pull Request 및 기본 브랜치 push 시 프론트엔드와 백엔드의 포맷팅, 린트, 타입 검사, 테스트 및 빌드를 수행하는 GitHub Actions CI 워크플로가 구성되어 있다.
- [ ] 애플리케이션 실행에 필요한 Azure 리소스가 재사용 가능한 Bicep 파일과 환경별 매개변수로 정의되어 있으며 Bicep 유효성 검사를 통과한다.
- [ ] `azure.yaml`에 프론트엔드와 백엔드 서비스, 빌드 산출물 및 Bicep 기반 인프라 구성이 정의되어 있고 로컬에서 `azd provision`과 `azd deploy`를 실행할 수 있다.
- [ ] 배포 워크플로가 GitHub OIDC와 Azure federated credentials를 사용해 비밀 키 없이 인증하며, 필요한 권한과 환경 변수는 GitHub Environments 및 Secrets로 관리된다.
- [ ] CI 검증 성공 후에만 `azd`를 통한 배포가 실행되며, 수동 실행, 환경별 승인, 동시 배포 방지 및 배포 실패 시 명확한 오류 보고가 구성되어 있다.