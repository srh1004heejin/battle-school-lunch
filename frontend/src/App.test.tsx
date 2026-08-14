import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

const school = {
  educationOfficeCode: "B10",
  schoolCode: "7010057",
  name: "서울고등학교",
  region: "서울특별시",
  address: "서울특별시 서초구",
};

afterEach(() => {
  vi.restoreAllMocks();
});

it("학교 검색부터 급식 결과 확인까지 진행한다", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ schools: [school] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({
      school,
      from: "2026-08-14",
      to: "2026-08-14",
      meals: [{
        date: "2026-08-14",
        mealType: "lunch",
        menu: ["현미밥", "된장찌개"],
        calories: "712 Kcal",
      }],
    }), { status: 200 }));

  render(<App />);
  await user.type(screen.getByLabelText("학교 이름"), "서울고");
  await user.click(screen.getByRole("button", { name: /학교 찾기/ }));
  await user.click(await screen.findByRole("button", { name: /서울고등학교/ }));
  await user.click(screen.getByRole("button", { name: /급식 조회/ }));

  expect(await screen.findByText("현미밥")).toBeInTheDocument();
  expect(screen.getByText("712 Kcal")).toBeInTheDocument();
  expect(globalThis.fetch).toHaveBeenCalledTimes(2);

  await user.type(screen.getByLabelText("학교 이름"), " 변경");
  expect(screen.queryByText("현미밥")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /급식 조회/ })).toBeDisabled();
});

it("학교 검색 결과 없음과 요청 실패를 구분한다", async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ schools: [] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({
      error: { code: "UPSTREAM_UNAVAILABLE", message: "NEIS를 사용할 수 없습니다." },
    }), { status: 503 }));

  render(<App />);
  const input = screen.getByLabelText("학교 이름");
  await user.type(input, "없는학교");
  await user.click(screen.getByRole("button", { name: /학교 찾기/ }));
  expect(await screen.findByText("일치하는 학교가 없어요.")).toBeInTheDocument();

  await user.clear(input);
  await user.type(input, "오류학교");
  await user.click(screen.getByRole("button", { name: /학교 찾기/ }));
  expect(await screen.findByText("NEIS를 사용할 수 없습니다.")).toBeInTheDocument();
});

it("잘못된 날짜 범위에서는 급식 요청을 보내지 않는다", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ schools: [school] }), { status: 200 }));

  render(<App />);
  await user.type(screen.getByLabelText("학교 이름"), "서울고");
  await user.click(screen.getByRole("button", { name: /학교 찾기/ }));
  await user.click(await screen.findByRole("button", { name: /서울고등학교/ }));
  await user.clear(screen.getByLabelText("시작일"));
  await user.type(screen.getByLabelText("시작일"), "2026-08-20");
  await user.clear(screen.getByLabelText("종료일"));
  await user.type(screen.getByLabelText("종료일"), "2026-08-14");

  expect(screen.getByRole("alert")).toHaveTextContent("시작일은 종료일보다 늦을 수 없어요.");
  expect(screen.getByRole("button", { name: /급식 조회/ })).toBeDisabled();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
});
