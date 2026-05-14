library(tidyverse)
library(readxl)
library(haven)

# ============================================================
# 서울특별시 구별 UMC 지표 전처리 (통합 코드)
# ============================================================

# --- 구 코드 매핑 테이블 ---
gu_codes <- tibble(
  gu_name = c("종로구", "중구", "용산구", "성동구", "광진구",
              "동대문구", "중랑구", "성북구", "강북구", "도봉구",
              "노원구", "은평구", "서대문구", "마포구", "양천구",
              "강서구", "구로구", "금천구", "영등포구", "동작구",
              "관악구", "서초구", "강남구", "송파구", "강동구"),
  district_code = c(11010, 11020, 11030, 11040, 11050,
                    11060, 11070, 11080, 11090, 11100,
                    11110, 11120, 11130, 11140, 11150,
                    11160, 11170, 11180, 11190, 11200,
                    11210, 11220, 11230, 11240, 11250),
  sq1_code = 1:25
)


# ============================================================
# PART 1: 통신품질 (CQ_1_2022~2024)
# ============================================================

years <- 2022:2024
raw_list <- map(years, function(yr) {
  path <- paste0("raw/CQ_1_", yr, ".csv")
  df <- read_csv(path, locale = locale(encoding = "CP949"), show_col_types = FALSE)
  df <- df %>%
    select(-구분, -읍면동,
           -contains("접속성공률"), -contains("LTE"))
  df %>% mutate(year = yr)
})

df_all <- bind_rows(raw_list)

df_seoul <- df_all %>%
  filter(시도 == "서울특별시", !is.na(시군구), 시군구 != "") %>%
  select(-시도)

numeric_cols_cq <- c(
  "전송속도(다운로드)", "전송속도(업로드)",
  "전송성공률(다운로드)", "전송성공률(업로드)",
  "접속시간(다운로드)", "접속시간(업로드)",
  "평균 지연", "평균 손실률"
)

df_seoul <- df_seoul %>%
  mutate(across(all_of(numeric_cols_cq), ~ as.numeric(str_trim(.))))

df_cq <- df_seoul %>%
  group_by(시군구) %>%
  summarise(across(all_of(numeric_cols_cq), ~ mean(., na.rm = TRUE)),
            .groups = "drop") %>%
  left_join(gu_codes %>% select(gu_name, district_code), by = c("시군구" = "gu_name")) %>%
  rename(
    district         = 시군구,
    download_speed   = `전송속도(다운로드)`,
    upload_speed     = `전송속도(업로드)`,
    download_success = `전송성공률(다운로드)`,
    upload_success   = `전송성공률(업로드)`,
    download_latency = `접속시간(다운로드)`,
    upload_latency   = `접속시간(업로드)`,
    avg_delay        = `평균 지연`,
    avg_loss_rate    = `평균 손실률`
  ) %>%
  select(district_code, district, everything())

cat("=== PART 1 완료: 통신품질 ===\n")


# ============================================================
# PART 2: 공공 와이파이 / 인구 (AFU_1_SGG.xlsx)
# ============================================================

df_afu <- read_excel("raw/AFU_1_SGG.xlsx") %>%
  mutate(wifi_per_1k_total = wifi / olderly * 1000,
         SIGUNGU_CD = as.numeric(SIGUNGU_CD)) %>%
  select(SIGUNGU_CD, wifi_per_1k_total)

cat("=== PART 2 완료: 와이파이/인구 ===\n")


# ============================================================
# PART 3: 서울시민 디지털역량 실태조사 2023
# ============================================================

sav <- read_sav("raw/Seoul_digital_2023.SAV")

# --- 파생 변수 생성 ---

# Devices: 기기 보유 종류 수 (Q1K1_1~7)
device_home_cols <- paste0("Q1K1_", 1:7)
sav <- sav %>%
  mutate(device_home_count = rowSums(!is.na(pick(all_of(device_home_cols))) &
                                       pick(all_of(device_home_cols)) != 0))

# Devices: 기기 사용 종류 수 (Q1K2_1~10)
device_use_cols <- paste0("Q1K2_", 1:10)
sav <- sav %>%
  mutate(device_use_count = rowSums(!is.na(pick(all_of(device_use_cols))) &
                                      pick(all_of(device_use_cols)) != 0))

# Digital Skills: Q4(기본조작) + Q5B(서비스이용) + Q7(비판적이해) 통합
# Q4_1~6 (24점) + Q5B_1~10 (40점) + Q7_1~5 (20점) = 84점 만점
skill_cols    <- paste0("Q4_", 1:6)
service_cols  <- paste0("Q5B_", 1:10)
critical_cols <- paste0("Q7_", 1:5)
all_skill_cols <- c(skill_cols, service_cols, critical_cols)

sav <- sav %>%
  mutate(skill_total = rowSums(pick(all_of(all_skill_cols)), na.rm = TRUE))

# Safety: 디지털 보안 (Q10_1~10, 40점 만점)
safety_cols <- paste0("Q10_", 1:10)
sav <- sav %>%
  mutate(safety_total = rowSums(pick(all_of(safety_cols)), na.rm = TRUE))

# Available for use: 인터넷 이용 빈도 (Q3 == 1: 최근 24시간 이내 → 주 3회 이상 근사)
sav <- sav %>%
  mutate(internet_active = ifelse(Q3 == 1, 1, 0))

# 연령 그룹 (65세 이상/미만)
sav <- sav %>%
  mutate(age_group = ifelse(HSQ3 >= 6, 1, 0))


# --- 가중 평균 / 가중 비율 함수 ---
wmean <- function(x, w) {
  valid <- !is.na(x) & !is.na(w)
  if (sum(valid) == 0) return(NA_real_)
  sum(x[valid] * w[valid]) / sum(w[valid])
}

wprop <- function(x, w) {
  valid <- !is.na(x) & !is.na(w)
  if (sum(valid) == 0) return(NA_real_)
  sum((x[valid] == 1) * w[valid]) / sum(w[valid])
}


# --- 구별 전체 인구 집계 ---
df_all_pop <- sav %>%
  group_by(SQ1) %>%
  summarise(
    device_home_all      = wmean(device_home_count, WT),
    device_use_all       = wmean(device_use_count, WT),
    skill_all            = wmean(skill_total, WT),
    safety_all           = wmean(safety_total, WT),
    internet_freq_rate  = wprop(internet_active, WT),
    .groups = "drop"
  )


# --- 격차 산출 함수 ---
calc_gap <- function(data, var_name, group_var, val_a, val_b) {
  data %>%
    group_by(SQ1, .data[[group_var]]) %>%
    summarise(val = wmean(.data[[var_name]], WT), .groups = "drop") %>%
    pivot_wider(names_from = all_of(group_var), values_from = val) %>%
    mutate(gap = .data[[as.character(val_a)]] - .data[[as.character(val_b)]]) %>%
    select(SQ1, gap)
}

# 격차 대상 변수
gap_vars    <- c("device_home_count", "device_use_count", "skill_total", "safety_total")
gap_names   <- c("device_home", "device_use", "skill", "safety")

# 남녀 격차 (남-여)
df_gender_gaps <- df_all_pop %>% select(SQ1)
for (i in seq_along(gap_vars)) {
  g <- calc_gap(sav, gap_vars[i], "SQ2", 1, 2)
  names(g)[2] <- paste0(gap_names[i], "_gender_gap")
  df_gender_gaps <- left_join(df_gender_gaps, g, by = "SQ1")
}

# 연령 격차 (65세 미만 - 65세 이상)
df_age_gaps <- df_all_pop %>% select(SQ1)
for (i in seq_along(gap_vars)) {
  g <- calc_gap(sav, gap_vars[i], "age_group", 0, 1)
  names(g)[2] <- paste0(gap_names[i], "_age_gap")
  df_age_gaps <- left_join(df_age_gaps, g, by = "SQ1")
}

# 설문 데이터 통합
df_survey <- df_all_pop %>%
  left_join(df_gender_gaps, by = "SQ1") %>%
  left_join(df_age_gaps, by = "SQ1") %>%
  left_join(gu_codes %>% select(sq1_code, district_code), by = c("SQ1" = "sq1_code")) %>%
  select(-SQ1)

cat("=== PART 3 완료: 디지털역량 2023 ===\n")


# ============================================================
# PART 4: 전체 병합 + 반올림 + 저장
# ============================================================

df_final <- df_cq %>%
  left_join(df_afu, by = c("district_code" = "SIGUNGU_CD")) %>%
  left_join(df_survey, by = "district_code") %>%
  mutate(across(where(is.numeric) & !matches("district_code"), ~ round(., 3)))

cat("\n=== 최종 결과 ===\n")
cat("행:", nrow(df_final), "/ 열:", ncol(df_final), "\n")
cat("열 이름:\n")
cat(paste(names(df_final), collapse = "\n"), "\n")

write.csv(df_final,
          file = "result/seoul_umc_indicators.csv",
          row.names = FALSE,
          fileEncoding = "EUC-KR")

cat("\n저장 완료: result/seoul_umc_indicators.csv\n")
print(df_final, n = 25, width = Inf)
