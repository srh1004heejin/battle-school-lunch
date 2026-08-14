class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def invalid_input(code: str, message: str, *, status_code: int = 400) -> AppError:
    return AppError(status_code, code, message)


class UpstreamBadResponse(AppError):
    def __init__(self, message: str = "NEIS가 유효하지 않은 응답을 반환했습니다.") -> None:
        super().__init__(502, "NEIS_BAD_RESPONSE", message)


class UpstreamUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__(
            503,
            "NEIS_UNAVAILABLE",
            "NEIS 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.",
        )


class UpstreamTimeout(AppError):
    def __init__(self) -> None:
        super().__init__(
            504,
            "NEIS_TIMEOUT",
            "NEIS 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
        )

