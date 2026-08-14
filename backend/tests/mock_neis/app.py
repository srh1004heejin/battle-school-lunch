from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def create_mock_neis_app() -> FastAPI:
    app = FastAPI(title="Controlled NEIS Mock", docs_url=None, redoc_url=None)
    app.state.requests = []

    @app.middleware("http")
    async def record_request(request: Request, call_next):
        app.state.requests.append(
            {
                "path": request.url.path,
                "query": dict(request.query_params),
            }
        )
        return await call_next(request)

    @app.get("/hub/schoolInfo")
    async def school_info(request: Request):
        query = request.query_params.get("SCHUL_NM")
        office_code = request.query_params.get("ATPT_OFCDC_SC_CODE")
        school_code = request.query_params.get("SD_SCHUL_CODE")

        if query == "학교검색장애":
            return JSONResponse({"RESULT": {"CODE": "ERROR-500", "MESSAGE": "서버 오류입니다."}})

        if query == "잘못된응답학교":
            return JSONResponse({"schoolInfo": [{"head": [{"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}}]}]})

        if query:
            rows = [row for row in _school_rows() if query in row["SCHUL_NM"]]
        elif office_code and school_code:
            rows = [
                row
                for row in _school_rows()
                if row["ATPT_OFCDC_SC_CODE"] == office_code and row["SD_SCHUL_CODE"] == school_code
            ]
        else:
            rows = list(_school_rows())

        if not rows:
            return JSONResponse(
                {
                    "schoolInfo": [
                        {"head": [{"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}]},
                    ]
                }
            )

        page_index = int(request.query_params.get("pIndex", "1"))
        page_size = int(request.query_params.get("pSize", "100"))
        page_rows = _paginate(rows, page_index, page_size)

        return JSONResponse(
            {
                "schoolInfo": [
                    {
                        "head": [
                            {"list_total_count": len(rows)},
                            {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                        ]
                    },
                    {"row": page_rows},
                ]
            }
        )

    @app.get("/hub/mealServiceDietInfo")
    async def meal_service_diet_info(request: Request):
        school_code = request.query_params.get("SD_SCHUL_CODE")
        meal_code = request.query_params.get("MMEAL_SC_CODE")

        if meal_code != "2":
            return JSONResponse({"RESULT": {"CODE": "ERROR-300", "MESSAGE": "필수 값이 누락되어 있습니다."}})

        if school_code == "9999999":
            return JSONResponse({"RESULT": {"CODE": "ERROR-500", "MESSAGE": "서버 오류입니다."}})

        if school_code == "8888888":
            return JSONResponse({"mealServiceDietInfo": [{"head": [{"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}}]}]})

        if school_code == "7777777":
            return JSONResponse({"mealServiceDietInfo": {"invalid": True}})

        rows = [row for row in _meal_rows() if row["SD_SCHUL_CODE"] == school_code]
        from_date = request.query_params.get("MLSV_FROM_YMD")
        to_date = request.query_params.get("MLSV_TO_YMD")

        if from_date and to_date:
            rows = [
                row
                for row in rows
                if from_date <= row["MLSV_YMD"] <= to_date
            ]

        if not rows:
            return JSONResponse(
                {
                    "mealServiceDietInfo": [
                        {"head": [{"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}}]},
                    ]
                }
            )

        page_index = int(request.query_params.get("pIndex", "1"))
        page_size = int(request.query_params.get("pSize", "100"))
        page_rows = _paginate(rows, page_index, page_size)

        return JSONResponse(
            {
                "mealServiceDietInfo": [
                    {
                        "head": [
                            {"list_total_count": len(rows)},
                            {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다."}},
                        ]
                    },
                    {"row": page_rows},
                ]
            }
        )

    return app


def _paginate(rows: list[dict[str, str]], page_index: int, page_size: int) -> list[dict[str, str]]:
    start_index = (page_index - 1) * page_size
    end_index = start_index + page_size
    return rows[start_index:end_index]


def _school_rows() -> Iterable[dict[str, str]]:
    yield {
        "ATPT_OFCDC_SC_CODE": "B10",
        "ATPT_OFCDC_SC_NM": "서울특별시교육청",
        "SD_SCHUL_CODE": "7010570",
        "SCHUL_NM": "한국중학교",
        "ENG_SCHUL_NM": "Korea Middle School",
        "SCHUL_KND_SC_NM": "중학교",
        "LCTN_SC_NM": "서울",
        "JU_ORG_NM": "중부교육지원청",
        "FOND_SC_NM": "공립",
        "ORG_RDNZC": "04567",
        "ORG_RDNMA": "서울특별시 중구 예시로 10",
        "ORG_RDNDA": "",
        "ORG_TELNO": "02-111-2222",
        "HMPG_ADRES": "https://example.school",
        "COEDU_SC_NM": "남여공학",
        "ORG_FAXNO": "02-111-3333",
        "HS_SC_NM": "",
        "INDST_SPECL_CCCCL_EXST_YN": "N",
        "HS_GNRL_BUSNS_SC_NM": "",
        "SPCLY_PURPS_HS_ORD_NM": "",
        "ENE_BFE_SEHF_SC_NM": "",
        "DGHT_SC_NM": "",
        "FOND_YMD": "20000101",
        "FOAS_MEMRD": "20000302",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }
    yield {
        "ATPT_OFCDC_SC_CODE": "C10",
        "ATPT_OFCDC_SC_NM": "부산광역시교육청",
        "SD_SCHUL_CODE": "7010571",
        "SCHUL_NM": "한국중학교",
        "ENG_SCHUL_NM": "Korea Middle School Busan",
        "SCHUL_KND_SC_NM": "중학교",
        "LCTN_SC_NM": "부산",
        "JU_ORG_NM": "중부교육지원청",
        "FOND_SC_NM": "공립",
        "ORG_RDNZC": "48900",
        "ORG_RDNMA": "부산광역시 중구 예시로 11",
        "ORG_RDNDA": "",
        "ORG_TELNO": "051-111-2222",
        "HMPG_ADRES": "https://busan.school",
        "COEDU_SC_NM": "남여공학",
        "ORG_FAXNO": "051-111-3333",
        "HS_SC_NM": "",
        "INDST_SPECL_CCCCL_EXST_YN": "N",
        "HS_GNRL_BUSNS_SC_NM": "",
        "SPCLY_PURPS_HS_ORD_NM": "",
        "ENE_BFE_SEHF_SC_NM": "",
        "DGHT_SC_NM": "",
        "FOND_YMD": "20010101",
        "FOAS_MEMRD": "20010302",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }
    yield {
        "ATPT_OFCDC_SC_CODE": "G10",
        "ATPT_OFCDC_SC_NM": "광주광역시교육청",
        "SD_SCHUL_CODE": "0000000",
        "SCHUL_NM": "빈급식학교",
        "ENG_SCHUL_NM": "Empty Meals School",
        "SCHUL_KND_SC_NM": "중학교",
        "LCTN_SC_NM": "광주",
        "JU_ORG_NM": "광주교육지원청",
        "FOND_SC_NM": "공립",
        "ORG_RDNZC": "61111",
        "ORG_RDNMA": "광주광역시 북구 예시로 12",
        "ORG_RDNDA": "",
        "ORG_TELNO": "062-111-2222",
        "HMPG_ADRES": "https://empty.school",
        "COEDU_SC_NM": "남여공학",
        "ORG_FAXNO": "062-111-3333",
        "HS_SC_NM": "",
        "INDST_SPECL_CCCCL_EXST_YN": "N",
        "HS_GNRL_BUSNS_SC_NM": "",
        "SPCLY_PURPS_HS_ORD_NM": "",
        "ENE_BFE_SEHF_SC_NM": "",
        "DGHT_SC_NM": "",
        "FOND_YMD": "20020101",
        "FOAS_MEMRD": "20020302",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }
    yield {
        "ATPT_OFCDC_SC_CODE": "D10",
        "ATPT_OFCDC_SC_NM": "대전광역시교육청",
        "SD_SCHUL_CODE": "9999999",
        "SCHUL_NM": "장애학교",
        "ENG_SCHUL_NM": "Failure School",
        "SCHUL_KND_SC_NM": "중학교",
        "LCTN_SC_NM": "대전",
        "JU_ORG_NM": "대전교육지원청",
        "FOND_SC_NM": "공립",
        "ORG_RDNZC": "34111",
        "ORG_RDNMA": "대전광역시 서구 예시로 13",
        "ORG_RDNDA": "",
        "ORG_TELNO": "042-111-2222",
        "HMPG_ADRES": "https://failure.school",
        "COEDU_SC_NM": "남여공학",
        "ORG_FAXNO": "042-111-3333",
        "HS_SC_NM": "",
        "INDST_SPECL_CCCCL_EXST_YN": "N",
        "HS_GNRL_BUSNS_SC_NM": "",
        "SPCLY_PURPS_HS_ORD_NM": "",
        "ENE_BFE_SEHF_SC_NM": "",
        "DGHT_SC_NM": "",
        "FOND_YMD": "20030101",
        "FOAS_MEMRD": "20030302",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }
    yield {
        "ATPT_OFCDC_SC_CODE": "D10",
        "ATPT_OFCDC_SC_NM": "대전광역시교육청",
        "SD_SCHUL_CODE": "8888888",
        "SCHUL_NM": "잘못된응답학교",
        "ENG_SCHUL_NM": "Bad Payload School",
        "SCHUL_KND_SC_NM": "중학교",
        "LCTN_SC_NM": "대전",
        "JU_ORG_NM": "대전교육지원청",
        "FOND_SC_NM": "공립",
        "ORG_RDNZC": "34112",
        "ORG_RDNMA": "대전광역시 서구 예시로 14",
        "ORG_RDNDA": "",
        "ORG_TELNO": "042-111-2223",
        "HMPG_ADRES": "https://bad.school",
        "COEDU_SC_NM": "남여공학",
        "ORG_FAXNO": "042-111-3334",
        "HS_SC_NM": "",
        "INDST_SPECL_CCCCL_EXST_YN": "N",
        "HS_GNRL_BUSNS_SC_NM": "",
        "SPCLY_PURPS_HS_ORD_NM": "",
        "ENE_BFE_SEHF_SC_NM": "",
        "DGHT_SC_NM": "",
        "FOND_YMD": "20040101",
        "FOAS_MEMRD": "20040302",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }


def _meal_rows() -> Iterable[dict[str, str]]:
    yield {
        "ATPT_OFCDC_SC_CODE": "B10",
        "ATPT_OFCDC_SC_NM": "서울특별시교육청",
        "SD_SCHUL_CODE": "7010570",
        "SCHUL_NM": "한국중학교",
        "MMEAL_SC_CODE": "2",
        "MMEAL_SC_NM": "중식",
        "MLSV_YMD": "20260802",
        "MLSV_FGR": "500",
        "DDISH_NM": "잡곡밥 (5.6.)<br/>된장찌개 (5.6.)",
        "ORPLC_INFO": "쌀: 국내산",
        "CAL_INFO": "710.2 Kcal",
        "NTR_INFO": "탄수화물: 98.3g<br/>단백질: 25.1g",
        "MLSV_FROM_YMD": "20260801",
        "MLSV_TO_YMD": "20260802",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }
    yield {
        "ATPT_OFCDC_SC_CODE": "B10",
        "ATPT_OFCDC_SC_NM": "서울특별시교육청",
        "SD_SCHUL_CODE": "7010570",
        "SCHUL_NM": "한국중학교",
        "MMEAL_SC_CODE": "2",
        "MMEAL_SC_NM": "중식",
        "MLSV_YMD": "20260801",
        "MLSV_FGR": "500",
        "DDISH_NM": "현미밥<br/>순두부찌개 (5.6.)",
        "ORPLC_INFO": "",
        "CAL_INFO": "",
        "NTR_INFO": "",
        "MLSV_FROM_YMD": "20260801",
        "MLSV_TO_YMD": "20260802",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }
    yield {
        "ATPT_OFCDC_SC_CODE": "B10",
        "ATPT_OFCDC_SC_NM": "서울특별시교육청",
        "SD_SCHUL_CODE": "7010570",
        "SCHUL_NM": "한국중학교",
        "MMEAL_SC_CODE": "2",
        "MMEAL_SC_NM": "중식",
        "MLSV_YMD": "20260801",
        "MLSV_FGR": "500",
        "DDISH_NM": "현미밥<br/>순두부찌개 (5.6.)",
        "ORPLC_INFO": "",
        "CAL_INFO": "",
        "NTR_INFO": "",
        "MLSV_FROM_YMD": "20260801",
        "MLSV_TO_YMD": "20260802",
        "LOAD_DTM": datetime.utcnow().isoformat(),
    }


app = create_mock_neis_app()
