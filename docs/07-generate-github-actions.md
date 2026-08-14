# GitHub Actions로 앱 테스트 및 배포 자동화하기

Azure 클라우드에 `azd up` 명령어로 앱을 배포할 수 있게 됐습니다. 이 앱 배포 절차를 GitHub Actions 워크플로우에 포함시키면 코드 커밋만으로 앱 배포까지 자동으로 이루어집니다. 이 세션에서는 `.github/workflows/ci.yml` 파일을 수정해서 앱 배포까지 자동화하는 작업을 합니다.

> [!NOTE]
> 현재 보이는 스크린샷은 시간이 지나면서 UI 업데이트로 인해 현재 시점과 다를 수 있습니다.

> [!IMPORTANT]
> [이전 세션](./06-deplopy-to-azure.md)에서 작업했던 터미널을 그대로 활용합니다.

## GitHub Actions 파이프라인 구성하기

1. 터미널에서 아래 명령어를 입력하여 GitHub Actions 워크플로우를 구성합니다.

    ```bash
    azd pipeline config
    ```

   화면의 프롬프트를 따라 구성을 완료합니다. 그러면 `.github/workflows` 디렉토리 아래 새 `azure-dev.yml` 파일이 만들어집니다.

## 직접 프롬프트 입력하기

1. 아래와 같이 직접 프롬프트를 입력합니다.

    ```text
    앱 배포를 위해 `.github/workflows/ci.yml`과 `.github/workflows/azure-dev.yml` 파일을 합쳐줘
    ```

1. 두 파일이 하나로 `.github/workflows/ci.yml` 파일에 합쳐진 것을 확인합니다.
1. 아래 프롬프트를 통해 PR을 생성합니다.

    ```text
    새 PR을 만들어서 방금 작업한 GitHub Actions 워크플로우를 추가해 줘
    ```

1. PR 생성을 확인한 후 머지합니다.
1. 머지가 완료된 것을 확인합니다.

---

GitHub Actions 워크플로우를 수정해서 Azure 클라우드 앱 배포 자동화를 완성했습니다. [MCP 서버 구현하기](./08-implement-mcp.md)로 넘어가세요.
