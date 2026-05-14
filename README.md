# Part 1 — UMC 지수 구축

> **언어**: R + QGIS
> **목적**: 서울 25개 자치구별 UMC(Universal Meaningful Connectivity) 종합지수 및 6개 차원별 점수 산출

## 폴더 구조

```
Part 1/
├── data/
│   ├── raw/            # 원시 데이터 (서울서베이, 디지털역량, 인구통계)
│   ├── processed/      # 전처리 중간 데이터
│   └── gis/            # Shapefile, QGIS 프로젝트
├── script/             # R 스크립트, Jupyter 노트북
├── output/
│   ├── figures/        # 차트 (히트맵, 바차트, 레이더 등)
│   ├── gis/            # GIS 결과 지도 (차원별 JPEG)
│   └── tables/         # 결과 테이블 (UMC 점수 CSV)
└── Part 1.Rproj
```

## 주요 산출물

| 파일 | 설명 |
|---|---|
| `output/tables/seoul_umc_scores.csv` | **25개구 UMC 종합점수** (Part 3 입력으로 사용) |
| `output/tables/seoul_umc_indicators.csv` | 개별 지표 점수 |
| `output/figures/fig_01~06_*.png` | 6종 시각화 |
| `output/gis/*.jpeg` | 6개 차원 GIS 지도 |

## 스크립트 실행 순서

1. `preprocess_connectivity.R` — 연결성 변수 전처리
2. `calculate_umc_scores.R` — UMC 지수 산출
3. `visualize_umc.R` — 시각화 생성
4. `03_affordability_eda.ipynb` — Affordability 탐색 분석
