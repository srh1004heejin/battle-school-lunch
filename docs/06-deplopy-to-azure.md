# Azure에 앱 배포하기

지금까지 구현한 앱은 로컬에서 잘 동작하는 것을 확인했습니다. 그렇다면, 이 앱을 클라우드로 배포할 순서입니다. 이 세션에서는 `azd` 명령어를 사용해서 로컬에서 Azure 클라우드로 배포하는 작업을 합니다.

> [!NOTE]
> 현재 보이는 스크린샷은 시간이 지나면서 UI 업데이트로 인해 현재 시점과 다를 수 있습니다.

## 직접 프롬프트 입력하기

1. Copilot app의 "Home" 탭에서 아래와 같이 직접 프롬프트를 입력합니다. 이 때 [Azure Skills](https://github.com/microsoft/azure-skills)를 사용하면 더욱 편리합니다. Azure Skills는 Copilot 앱에 기본 설치되어 있습니다. 일반적으로는 `/azure-prepare` 스킬을 사용하지 않아도 프롬프트의 맥락을 이해하고 자동으로 스킬을 호출하지만, 명시적으로 `/azure-prepare` 스킬을 호출해서 프롬프트를 작성해도 괜찮습니다.

    ```text
    현재 구현된 앱을 Azure 클라우드로 배포할 거야. `azd` CLI를 사용해서 배포할 계획이니 초기화 명령어를 통해 관련한 bicep 파일을 만들고 `azd` 명령어로 배포할 수 있도록 준비해 줘.
    ```

   또는 아래와 같이 `/azure-prepare` 스킬을 명시적으로 호출해 보세요.

    ```text
    /azure-prepare 현재 구현된 앱을 Azure 클라우드로 배포할 거야. `azd` CLI를 사용해서 배포할 계획이니 초기화 명령어를 통해 관련한 bicep 파일을 만들고 `azd` 명령어로 배포할 수 있도록 준비해 줘.
    ```

1. bicep 파일이 다 만들어지고 나면 아래 명령어를 이용해서 앱을 배포합니다.

    ```bash
    azd up
    ```

   ![`azd up` 명령어로 앱 배포하기](./images/06-deplopy-to-azure-01.jpg)

   또는 Azure Skills를 이용해서 프롬프트로 배포해도 됩니다. `/azure-deploy` 스킬을 사용합니다.

    ```text
    /azure-deploy
    ```

   ![`/azure-deploy` 스킬로 앱 배포하기](./images/06-deplopy-to-azure-02.jpg)

1. 앱 배포가 잘 된 것을 확인합니다. 만약 배포중 에러가 발생한다면 추가 프롬프트를 이용해서 배포 에러를 수정합니다.
1. "Create PR" 버튼을 클릭하여 변경 사항을 PR로 생성한 후 머지합니다.
1. 머지가 완료된 것을 확인합니다.

---

Azure 클라우드에 앱을 잘 배포했습니다. [GitHub Actions로 앱 테스트 및 배포 자동화하기](./07-generate-github-actions.md)로 넘어가세요.
