library(tidyverse)
library(haven)
library(readxl)

# ============================================================
# 서울특별시 구별 UMC Score 산출 (v6 — ITU IDI 2023 비판적 감사 반영)
#
# 6개 차원 (ITU UMC Framework 기반, 14개 지표):
#   1) Connectivity (2): DL속도(+), DL레이턴시(-)
#      → IDI p.15 "speed... relevant to include" + p.6 "fast and reliable"
#      → v5 대비: UL/평균지연 제거 (중복성 + 파생값)
#   2) Available for Use (2): 노인WiFi, 인터넷이용률  ★추후 기지국 적정성으로 교체 예정
#      → ITU Universal Connectivity pillar 로컬 프록시
#   3) Affordability (2): 상권분석 월소득(+), SKT 연체율(-)
#      → ITU IPB "affordability = relative burden of ICT prices"
#   4) Devices (2): 핵심디지털기기(Q1K2 core), 가구핵심기기(Q1K1 core)
#      → IDI p.17 "ownership of a smartphone" 확장
#      → v5 대비: 전체합산→핵심기기(PC/노트북/스마트폰/태블릿)만 카운트
#   5) Digital Skills (4): Q4 + Q5B + Q6B + Q7(비판적 정보이해)
#      → ITU 5개 카테고리 중 information/data literacy = Q7 추가
#      → IDI p.17-18 "activities in five categories"
#   6) Safety (2): 보안행동(Q10_1~7), 보안인식(Q10_8~10)
#      → ITU가 GCI를 거부한 이유: "input vs output" → output(행동) 강조
#      → v5 대비: 단일지표→행동/인식 2개 분리
# ============================================================


# ============================================================
# 0. 기존 데이터 (Connectivity, Available for Use)
# ============================================================

old <- read.csv("result/seoul_umc_scores.csv", fileEncoding = "EUC-KR")

base_vars <- old %>%
  select(district_code, district,
         download_speed, upload_speed, download_latency, upload_latency, avg_delay,
         wifi_per_1k_total, internet_freq_rate)

if ("avg_loss_rate" %in% names(old)) {
  base_vars$avg_loss_rate <- old$avg_loss_rate
} else {
  base_vars$avg_loss_rate <- NA_real_
}


# ============================================================
# 0-1. Affordability 데이터 로드
#      (a) 구별 월평균 소득 — 구매력(capacity)
#      (b) SKT 요금 연체 비율 — 가격부담(burden)
# ============================================================

# (a) 소득 데이터
aff <- read_xlsx("raw/03_affordability_result.xlsx", sheet = "구별_부담률순위")
cat("[Affordability] 소득 데이터 로드:", nrow(aff), "행\n")

aff_clean <- aff %>%
  select(district = 구이름, avg_income = 월_평균_소득_금액) %>%
  mutate(avg_income = as.numeric(avg_income))

# (b) SKT 요금 연체 비율 (행정동 × 성별 × 연령대 → 구별 인구가중 평균)
skt_files <- list.files("C:/woo/data/UMC/raw/통신정보", pattern = "\\.xlsx$", full.names = TRUE)
cat("[Affordability] SKT 통신정보 파일:", length(skt_files), "개\n")

# 2024년 파일들로 연 평균 산출
skt_2024 <- skt_files[grepl("2024", skt_files)]
cat("[Affordability] 2024년 파일:", length(skt_2024), "개\n")

delinquency_list <- list()
for (f in skt_2024) {
  df <- read_xlsx(f)
  df$pop <- as.numeric(df$총인구수)
  df$delinq <- as.numeric(df$`최근 3개월 내 요금 연체 비율`)

  by_gu <- df %>%
    group_by(자치구) %>%
    summarise(delinq_rate = weighted.mean(delinq, pop, na.rm = TRUE),
              .groups = "drop")
  delinquency_list[[basename(f)]] <- by_gu
}

# 12개월 평균
delinq_all <- bind_rows(delinquency_list) %>%
  group_by(자치구) %>%
  summarise(delinq_rate = mean(delinq_rate, na.rm = TRUE),
            .groups = "drop") %>%
  rename(district = 자치구)

cat("[Affordability] 구별 요금 연체 비율 (2024 평균):\n")
print(delinq_all %>% arrange(desc(delinq_rate)), n = 25)

# 소득 + 연체율 병합
aff_clean <- aff_clean %>%
  left_join(delinq_all, by = "district")

cat("[Affordability] 구별 월평균 소득 + 연체율:\n")
print(aff_clean %>% arrange(avg_income), n = 25)


# ============================================================
# 1. SAV 로드
# ============================================================

sav <- read_sav("raw/Seoul_digital_2023.SAV")
cat("\nSAV 차원:", dim(sav), "\n")

gu_labels <- c(
  "1"="종로구","2"="중구","3"="용산구","4"="성동구","5"="광진구",
  "6"="동대문구","7"="중랑구","8"="성북구","9"="강북구","10"="도봉구",
  "11"="노원구","12"="은평구","13"="서대문구","14"="마포구","15"="양천구",
  "16"="강서구","17"="구로구","18"="금천구","19"="영등포구","20"="동작구",
  "21"="관악구","22"="서초구","23"="강남구","24"="송파구","25"="강동구"
)

sav <- sav %>%
  mutate(gu_code = as.numeric(SQ1),
         gu_name = gu_labels[as.character(gu_code)],
         wt      = as.numeric(WT))


# ============================================================
# 2. Devices — 핵심 디지털 기기 다양성 (v6 재가공)
# ============================================================
# 기존: 전체 기기 수 단순 합산 → 문제: TV=노트북 동일 가중치
# 변경: 핵심 디지털 접근 기기만 카운트
#   Q1K1 core (가구): _1 데스크탑, _2 노트북, _5 태블릿PC  → 0~3
#   Q1K2 core (개인): _1 데스크탑, _2 노트북, _3 스마트폰, _7 태블릿PC  → 0~4
#   제외: 일반TV, 스마트TV, 피처폰, 스마트워치, AI스피커, VR/AR

# --- 가정 보유 (핵심) ---
q1k1_vars <- paste0("Q1K1_", 1:7)
q1k1_exist <- q1k1_vars[q1k1_vars %in% names(sav)]
cat("\n[Devices] 가정보유 Q1K1:", length(q1k1_exist), "개\n")

sav <- sav %>% mutate(across(all_of(q1k1_exist), ~ as.numeric(.)))

for (v in q1k1_exist) {
  sav[[paste0(v, "_bin")]] <- ifelse(!is.na(sav[[v]]) & sav[[v]] != 9998, 1, 0)
}

# 핵심 기기: Q1K1_1(데스크탑), Q1K1_2(노트북), Q1K1_5(태블릿)
q1k1_core <- c("Q1K1_1_bin", "Q1K1_2_bin", "Q1K1_5_bin")
q1k1_core <- q1k1_core[q1k1_core %in% names(sav)]
sav$device_home_core <- rowSums(sav[q1k1_core], na.rm = TRUE)

devices_home <- sav %>%
  group_by(gu_code, gu_name) %>%
  summarise(device_home_core = round(weighted.mean(device_home_core, wt, na.rm = TRUE), 3),
            .groups = "drop")

# --- 본인 사용 (핵심) ---
q1k2_vars <- paste0("Q1K2_", 1:10)
q1k2_exist <- q1k2_vars[q1k2_vars %in% names(sav)]
cat("[Devices] 본인사용 Q1K2:", length(q1k2_exist), "개\n")

sav <- sav %>% mutate(across(all_of(q1k2_exist), ~ as.numeric(.)))

for (v in q1k2_exist) {
  sav[[paste0(v, "_bin")]] <- ifelse(!is.na(sav[[v]]) & sav[[v]] != 9998, 1, 0)
}

# 핵심 기기: Q1K2_1(데스크탑), Q1K2_2(노트북), Q1K2_3(스마트폰), Q1K2_7(태블릿)
q1k2_core <- c("Q1K2_1_bin", "Q1K2_2_bin", "Q1K2_3_bin", "Q1K2_7_bin")
q1k2_core <- q1k2_core[q1k2_core %in% names(sav)]
sav$device_use_core <- rowSums(sav[q1k2_core], na.rm = TRUE)

devices_use <- sav %>%
  group_by(gu_code, gu_name) %>%
  summarise(device_use_core = round(weighted.mean(device_use_core, wt, na.rm = TRUE), 3),
            .groups = "drop")


# ============================================================
# 3. Digital Skills — 4개 개별 지표 (v6: Q7 추가)
# ============================================================
# Q4_1~6:   스마트기기 사용 능력      (6문항 × 4점 = 24점)
# Q5B_1~10: 디지털 서비스 이용 능력   (10문항 × 4점 = 40점)
# Q6B_1~7:  스마트기기 활동 능숙도    (7문항 × 4점 = 28점)
# Q7_1~5:   비판적 정보이해           (5문항 × 4점 = 20점)  ← NEW
#   → ITU "information/data literacy" 카테고리 대응 (IDI p.17-18)

q4_vars  <- paste0("Q4_", 1:6);   q4_max  <- 24
q5b_vars <- paste0("Q5B_", 1:10); q5b_max <- 40
q6b_vars <- paste0("Q6B_", 1:7);  q6b_max <- 28
q7_vars  <- paste0("Q7_", 1:5);   q7_max  <- 20

q4_exist  <- q4_vars[q4_vars %in% names(sav)]
q5b_exist <- q5b_vars[q5b_vars %in% names(sav)]
q6b_exist <- q6b_vars[q6b_vars %in% names(sav)]
q7_exist  <- q7_vars[q7_vars %in% names(sav)]

cat("\n[Skills] Q4:", length(q4_exist), "/ 6")
cat(" | Q5B:", length(q5b_exist), "/ 10")
cat(" | Q6B:", length(q6b_exist), "/ 7")
cat(" | Q7:", length(q7_exist), "/ 5\n")

sav <- sav %>%
  mutate(across(any_of(c(q4_exist, q5b_exist, q6b_exist, q7_exist)), ~ as.numeric(.)))

if (length(q4_exist) == 6)   sav$skill_q4_ratio  <- rowSums(sav[q4_exist],  na.rm = FALSE) / q4_max
if (length(q5b_exist) == 10) sav$skill_q5b_ratio <- rowSums(sav[q5b_exist], na.rm = FALSE) / q5b_max
if (length(q6b_exist) == 7)  sav$skill_q6b_ratio <- rowSums(sav[q6b_exist], na.rm = FALSE) / q6b_max
if (length(q7_exist) == 5)   sav$skill_q7_ratio  <- rowSums(sav[q7_exist],  na.rm = FALSE) / q7_max

skills_by_gu <- sav %>%
  group_by(gu_code, gu_name) %>%
  summarise(
    skill_q4  = round(weighted.mean(skill_q4_ratio,  wt, na.rm = TRUE), 3),
    skill_q5b = round(weighted.mean(skill_q5b_ratio, wt, na.rm = TRUE), 3),
    skill_q6b = round(weighted.mean(skill_q6b_ratio, wt, na.rm = TRUE), 3),
    skill_q7  = round(weighted.mean(skill_q7_ratio,  wt, na.rm = TRUE), 3),
    .groups = "drop"
  )

cat("[Digital Skills] 구별 영역별 가중평균 (0~1):\n")
print(skills_by_gu, n = 25)


# ============================================================
# 4. Safety — 행동/인식 2개 하위지표 (v6 분리)
# ============================================================
# Q10_1~7:  보안 행동 (악성코드검사, OS업데이트, 피싱삭제, 개인정보주의,
#           암호변경, 접근권한설정, 백업)  → 7문항 × 4점 = 28점
# Q10_8~10: 보안 인식 (사이버권리침해신고인지, 사이버폭력신고인지,
#           사이버범죄대응인지)            → 3문항 × 4점 = 12점
# ITU: GCI 거부 이유 "input vs output" → output(행동)을 주 지표로 강조

q10_vars  <- paste0("Q10_", 1:10)
q10_exist <- q10_vars[q10_vars %in% names(sav)]
cat("\n[Safety] Q10:", length(q10_exist), "/ 10\n")

sav <- sav %>% mutate(across(all_of(q10_exist), ~ as.numeric(.)))

# 행동 (Q10_1~7, 28점 만점)
q10_behavior <- paste0("Q10_", 1:7)
q10_behavior <- q10_behavior[q10_behavior %in% names(sav)]
sav$safety_behavior <- rowSums(sav[q10_behavior], na.rm = FALSE) / 28

# 인식 (Q10_8~10, 12점 만점)
q10_awareness <- paste0("Q10_", 8:10)
q10_awareness <- q10_awareness[q10_awareness %in% names(sav)]
sav$safety_awareness <- rowSums(sav[q10_awareness], na.rm = FALSE) / 12

safety_by_gu <- sav %>%
  group_by(gu_code, gu_name) %>%
  summarise(
    safety_behavior  = round(weighted.mean(safety_behavior,  wt, na.rm = TRUE), 3),
    safety_awareness = round(weighted.mean(safety_awareness, wt, na.rm = TRUE), 3),
    .groups = "drop"
  )


# ============================================================
# 5. 병합
# ============================================================

code_to_gu <- data.frame(
  district_code = c(11010,11020,11030,11040,11050,11060,11070,11080,11090,
                    11100,11110,11120,11130,11140,11150,11160,11170,11180,
                    11190,11200,11210,11220,11230,11240,11250),
  gu_code = 1:25
)

result <- base_vars %>% left_join(code_to_gu, by = "district_code")

# Affordability (구이름 기준 join)
result <- result %>%
  left_join(aff_clean, by = "district")

# Devices (v6: core만)
result <- result %>%
  left_join(devices_home %>% select(gu_code, device_home_core), by = "gu_code") %>%
  left_join(devices_use  %>% select(gu_code, device_use_core),  by = "gu_code")

# Digital Skills (v6: Q7 추가)
result <- result %>%
  left_join(skills_by_gu %>% select(gu_code, skill_q4, skill_q5b, skill_q6b, skill_q7), by = "gu_code")

# Safety (v6: 행동/인식 분리)
result <- result %>%
  left_join(safety_by_gu %>% select(gu_code, safety_behavior, safety_awareness), by = "gu_code")

result <- result %>% select(-gu_code)

# Affordability join 확인
cat("\n[Affordability] join 결과 — avg_income NA:", sum(is.na(result$avg_income)),
    "/ delinq_rate NA:", sum(is.na(result$delinq_rate)), "\n")


# ============================================================
# 6. Min-Max 정규화 & Score 산출
# ============================================================

normalize_pos <- function(x) {
  rng <- range(x, na.rm = TRUE)
  if (rng[2] == rng[1]) return(rep(0.5, length(x)))
  (x - rng[1]) / (rng[2] - rng[1])
}
normalize_neg <- function(x) {
  rng <- range(x, na.rm = TRUE)
  if (rng[2] == rng[1]) return(rep(0.5, length(x)))
  (rng[2] - x) / (rng[2] - rng[1])
}

result <- result %>%
  mutate(
    # Connectivity (v6: DL속도 + DL레이턴시만)
    n_download_speed   = normalize_pos(download_speed),
    n_download_latency = normalize_neg(download_latency),

    # Available for Use (★추후 기지국 적정성으로 교체 예정)
    n_wifi_per_1k_total = normalize_pos(wifi_per_1k_total),
    n_internet_freq_rate  = normalize_pos(internet_freq_rate),

    # Affordability
    n_avg_income   = normalize_pos(avg_income),
    n_delinq_rate  = normalize_neg(delinq_rate),

    # Devices (v6: 핵심 디지털 기기만)
    n_device_home_core = normalize_pos(device_home_core),
    n_device_use_core  = normalize_pos(device_use_core),

    # Digital Skills (v6: Q7 추가 → 4개)
    n_skill_q4  = normalize_pos(skill_q4),
    n_skill_q5b = normalize_pos(skill_q5b),
    n_skill_q6b = normalize_pos(skill_q6b),
    n_skill_q7  = normalize_pos(skill_q7),

    # Safety (v6: 행동/인식 분리 → 2개)
    n_safety_behavior  = normalize_pos(safety_behavior),
    n_safety_awareness = normalize_pos(safety_awareness)
  )

# ── 차원별 Score (동일 가중) ────────────────────────────────
result <- result %>%
  mutate(
    score_Connectivity      = rowMeans(pick(n_download_speed, n_download_latency)),
    score_Available_for_Use = rowMeans(pick(n_wifi_per_1k_total, n_internet_freq_rate)),
    score_Affordability     = rowMeans(pick(n_avg_income, n_delinq_rate)),
    score_Devices           = rowMeans(pick(n_device_home_core, n_device_use_core)),
    score_Digital_Skills    = rowMeans(pick(n_skill_q4, n_skill_q5b, n_skill_q6b, n_skill_q7)),
    score_Safety            = rowMeans(pick(n_safety_behavior, n_safety_awareness)),

    # 종합 UMC Score (6개 차원 동일 가중)
    score_UMC = rowMeans(pick(score_Connectivity, score_Available_for_Use,
                              score_Affordability, score_Devices,
                              score_Digital_Skills, score_Safety)),
    rank_UMC  = rank(-score_UMC, ties.method = "min")
  )


# ============================================================
# 7. 반올림 + 저장
# ============================================================

result <- result %>%
  mutate(across(where(is.numeric) & !starts_with("district"), ~ round(., 3))) %>%
  arrange(rank_UMC)

cat("\n=== 차원별 Score + 종합 UMC Score (v6, 14개 지표) ===\n")
result %>%
  select(district, score_Connectivity, score_Available_for_Use,
         score_Affordability, score_Devices, score_Digital_Skills, score_Safety,
         score_UMC, rank_UMC) %>%
  as_tibble() %>%
  print(n = 25)

cat("\n=== Digital Skills 영역 상세 (Q4+Q5B+Q6B+Q7) ===\n")
result %>%
  select(district, skill_q4, skill_q5b, skill_q6b, skill_q7,
         n_skill_q4, n_skill_q5b, n_skill_q6b, n_skill_q7, score_Digital_Skills) %>%
  as_tibble() %>%
  print(n = 25)

cat("\n=== Safety 영역 상세 (행동 + 인식) ===\n")
result %>%
  select(district, safety_behavior, safety_awareness,
         n_safety_behavior, n_safety_awareness, score_Safety) %>%
  as_tibble() %>%
  print(n = 25)

cat("\n=== Devices 영역 상세 (핵심기기) ===\n")
result %>%
  select(district, device_home_core, device_use_core,
         n_device_home_core, n_device_use_core, score_Devices) %>%
  as_tibble() %>%
  print(n = 25)

write.csv(result,
          file = "result/seoul_umc_scores.csv",
          row.names = FALSE,
          fileEncoding = "EUC-KR")

cat("\n✅ 저장 완료: result/seoul_umc_scores.csv\n")
cat("열 수:", ncol(result), "| v6 — ITU IDI 2023 비판적 감사 반영, 14개 지표\n")
cat("변경: Dim1 축소(2), Dim4 핵심기기(2), Dim5 Q7추가(4), Dim6 행동/인식(2)\n")
cat("★ Dim2 Available for Use: 추후 기지국 적정성 데이터로 교체 예정\n")
