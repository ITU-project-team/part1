###############################################################################
# visualize_umc.R
# Seoul UMC Score Visualization (6 Dimensions × 25 Districts)
#
# Outputs (all in English):
#   result/figures/fig_01_heatmap.png          — 25 districts × 6 dimensions
#   result/figures/fig_02_bar_umc.png          — Overall UMC ranking bar
#   result/figures/fig_03_bar_stacked.png      — Dimension contribution stacked bar
#   result/figures/fig_04_radar_top_bottom.png — Top 5 vs Bottom 5 radar comparison
#   result/figures/fig_05_map_umc.png          — Overall UMC choropleth
#   result/figures/fig_06_map_dimensions.png   — 6-dimension small multiple maps
#   result/figures/radar/radar_[district].png  — Individual district radar (×25)
###############################################################################

# install.packages(c("tidyverse", "sf", "RColorBrewer", "patchwork", "scales"))
library(tidyverse)
library(sf)
library(RColorBrewer)
library(patchwork)
library(scales)

# ── 0. Load data ─────────────────────────────────────────────
df <- read.csv("result/seoul_umc_scores.csv", fileEncoding = "EUC-KR") %>%
  as_tibble() %>%
  arrange(rank_UMC)

score_cols <- c("score_Connectivity", "score_Available_for_Use",
                "score_Affordability", "score_Devices",
                "score_Digital_Skills", "score_Safety")

# English district name mapping
gu_eng <- c(
  "종로구"="Jongno", "중구"="Jung", "용산구"="Yongsan",
  "성동구"="Seongdong", "광진구"="Gwangjin", "동대문구"="Dongdaemun",
  "중랑구"="Jungnang", "성북구"="Seongbuk", "강북구"="Gangbuk",
  "도봉구"="Dobong", "노원구"="Nowon", "은평구"="Eunpyeong",
  "서대문구"="Seodaemun", "마포구"="Mapo", "양천구"="Yangcheon",
  "강서구"="Gangseo", "구로구"="Guro", "금천구"="Geumcheon",
  "영등포구"="Yeongdeungpo", "동작구"="Dongjak", "관악구"="Gwanak",
  "서초구"="Seocho", "강남구"="Gangnam", "송파구"="Songpa",
  "강동구"="Gangdong"
)

df$district_eng <- gu_eng[df$district]

dim_labels_short <- c(
  score_Connectivity      = "Connectivity",
  score_Available_for_Use = "Availability",
  score_Affordability     = "Affordability",
  score_Devices           = "Devices",
  score_Digital_Skills    = "Digital Skills",
  score_Safety            = "Safety"
)

dim_colors <- c(
  "Connectivity"  = "#2171B5",
  "Availability"  = "#6BAED6",
  "Affordability" = "#74C476",
  "Devices"       = "#FD8D3C",
  "Digital Skills" = "#9E9AC8",
  "Safety"        = "#FC9272"
)

# Ensure output dirs exist
dir.create("result/figures/radar", recursive = TRUE, showWarnings = FALSE)


###############################################################################
# ── 1. HEATMAP (25 districts × 6 dimensions) ─────────────────
###############################################################################

heatmap_data <- df %>%
  select(district_eng, all_of(score_cols)) %>%
  pivot_longer(-district_eng, names_to = "dimension", values_to = "score") %>%
  mutate(
    dimension = factor(dimension, levels = score_cols, labels = names(dim_colors)),
    district_eng = factor(district_eng, levels = rev(df$district_eng))
  )

p_heatmap <- ggplot(heatmap_data, aes(x = dimension, y = district_eng, fill = score)) +
  geom_tile(color = "white", linewidth = 0.5) +
  geom_text(aes(label = sprintf("%.2f", score)), size = 2.8, color = "black") +
  scale_fill_distiller(palette = "RdYlGn", direction = 1,
                       limits = c(0, 1), name = "Score") +
  labs(title = "Seoul UMC Dimension Scores by District",
       subtitle = "Min-Max normalized (0 = vulnerable, 1 = good) | Sorted by overall UMC rank",
       x = NULL, y = NULL) +
  theme_minimal(base_size = 11) +
  theme(
    axis.text.x = element_text(angle = 0, hjust = 0.5, size = 9, face = "bold"),
    axis.text.y = element_text(size = 9),
    plot.title = element_text(face = "bold", size = 14),
    legend.position = "right"
  )

ggsave("result/figures/fig_01_heatmap.png", p_heatmap,
       width = 10, height = 10, dpi = 300)
cat("✅ fig_01_heatmap.png\n")


###############################################################################
# ── 2. BAR CHART — Overall UMC Ranking ────────────────────────
###############################################################################

bar_data <- df %>%
  mutate(district_eng = factor(district_eng, levels = rev(district_eng)))

p_bar_umc <- ggplot(bar_data, aes(x = district_eng, y = score_UMC, fill = score_UMC)) +
  geom_col(width = 0.7) +
  geom_text(aes(label = sprintf("%.3f", score_UMC)), hjust = -0.1, size = 3) +
  scale_fill_distiller(palette = "RdYlGn", direction = 1, limits = c(0, 0.8)) +
  coord_flip() +
  labs(title = "Overall UMC Score by District",
       subtitle = "Equal-weighted average of 6 dimensions",
       x = NULL, y = "UMC Score") +
  theme_minimal(base_size = 11) +
  theme(legend.position = "none",
        plot.title = element_text(face = "bold", size = 14)) +
  scale_y_continuous(limits = c(0, 0.85), expand = c(0, 0))

ggsave("result/figures/fig_02_bar_umc.png", p_bar_umc,
       width = 8, height = 10, dpi = 300)
cat("✅ fig_02_bar_umc.png\n")


###############################################################################
# ── 3. STACKED BAR — Dimension Contributions ─────────────────
###############################################################################

stacked_data <- df %>%
  select(district_eng, all_of(score_cols)) %>%
  mutate(across(all_of(score_cols), ~ . / 6)) %>%
  pivot_longer(-district_eng, names_to = "dimension", values_to = "contribution") %>%
  mutate(
    dimension = factor(dimension, levels = rev(score_cols),
                       labels = rev(names(dim_colors))),
    district_eng = factor(district_eng, levels = rev(df$district_eng))
  )

p_stacked <- ggplot(stacked_data,
                    aes(x = district_eng, y = contribution, fill = dimension)) +
  geom_col(width = 0.7) +
  coord_flip() +
  scale_fill_manual(values = dim_colors, name = "Dimension") +
  labs(title = "UMC Score — Dimension Contributions",
       subtitle = "Each dimension score / 6 = contribution to overall UMC",
       x = NULL, y = "UMC Score") +
  theme_minimal(base_size = 11) +
  theme(plot.title = element_text(face = "bold", size = 14),
        legend.position = "bottom") +
  guides(fill = guide_legend(nrow = 1))

ggsave("result/figures/fig_03_bar_stacked.png", p_stacked,
       width = 10, height = 10, dpi = 300)
cat("✅ fig_03_bar_stacked.png\n")


###############################################################################
# ── 4. RADAR CHARTS ──────────────────────────────────────────
###############################################################################

# --- Radar helper function ---
make_radar <- function(df_sub, title_text, show_legend = TRUE) {
  
  n_dims <- 6
  dim_names <- names(dim_colors)
  
  radar_data <- df_sub %>%
    select(district_eng, all_of(score_cols)) %>%
    pivot_longer(-district_eng, names_to = "dimension", values_to = "score") %>%
    mutate(
      dim_idx = match(dimension, score_cols),
      angle   = (dim_idx - 1) * 2 * pi / n_dims,
      x       = score * cos(angle - pi/2),
      y       = score * sin(angle - pi/2)
    )
  
  # Close polygon
  radar_closed <- radar_data %>%
    group_by(district_eng) %>%
    arrange(dim_idx) %>%
    bind_rows(radar_data %>% group_by(district_eng) %>% filter(dim_idx == 1)) %>%
    ungroup()
  
  # Grid circles
  grid_df <- map_dfr(c(0.25, 0.5, 0.75, 1.0), function(r) {
    tibble(angle = seq(0, 2*pi, length.out = 100),
           x = r * cos(angle - pi/2),
           y = r * sin(angle - pi/2),
           r = r)
  })
  
  # Grid labels
  grid_labels <- tibble(r = c(0.25, 0.5, 0.75, 1.0),
                        x = 0.02, y = -r - 0.03,
                        label = as.character(r))
  
  # Axis lines + labels
  axis_df <- tibble(
    dim_idx = 1:n_dims,
    angle   = (dim_idx - 1) * 2 * pi / n_dims,
    x_end   = 1.0 * cos(angle - pi/2),
    y_end   = 1.0 * sin(angle - pi/2),
    lx      = 1.18 * cos(angle - pi/2),
    ly      = 1.18 * sin(angle - pi/2),
    label   = dim_names
  )
  
  p <- ggplot() +
    geom_path(data = grid_df, aes(x, y, group = r),
              color = "grey80", linewidth = 0.3) +
    geom_text(data = grid_labels, aes(x, y, label = label),
              size = 2, color = "grey50") +
    geom_segment(data = axis_df, aes(x = 0, y = 0, xend = x_end, yend = y_end),
                 color = "grey70", linewidth = 0.3) +
    geom_text(data = axis_df, aes(x = lx, y = ly, label = label),
              size = 3, fontface = "bold") +
    geom_polygon(data = radar_closed,
                 aes(x, y, group = district_eng, fill = district_eng),
                 alpha = 0.15) +
    geom_path(data = radar_closed,
              aes(x, y, group = district_eng, color = district_eng),
              linewidth = 1) +
    geom_point(data = radar_data,
               aes(x, y, color = district_eng), size = 2.5) +
    coord_equal(xlim = c(-1.35, 1.35), ylim = c(-1.35, 1.35)) +
    labs(title = title_text, color = "District", fill = "District") +
    theme_void(base_size = 11) +
    theme(plot.title = element_text(face = "bold", size = 13, hjust = 0.5))
  
  if (show_legend) {
    p <- p + theme(legend.position = "bottom")
  } else {
    p <- p + theme(legend.position = "none")
  }
  
  return(p)
}

# --- 4a. Top 5 vs Bottom 5 ---
top5 <- df %>% slice_head(n = 5)
bot5 <- df %>% slice_tail(n = 5)

p_radar_top <- make_radar(top5, "Top 5 Districts")
p_radar_bot <- make_radar(bot5, "Bottom 5 Districts")

p_radar_combined <- p_radar_top + p_radar_bot +
  plot_annotation(
    title = "Seoul UMC — Dimension Profile Comparison",
    theme = theme(plot.title = element_text(face = "bold", size = 15, hjust = 0.5))
  )

ggsave("result/figures/fig_04_radar_top_bottom.png", p_radar_combined,
       width = 14, height = 7, dpi = 300)
cat("✅ fig_04_radar_top_bottom.png\n")


# --- 4b. Individual district radars (25개) ---
# Seoul average for comparison
avg_row <- df %>%
  summarise(across(all_of(score_cols), mean)) %>%
  mutate(district_eng = "Seoul Avg.")

for (i in 1:nrow(df)) {
  row_i <- df[i, ]
  gu_name <- row_i$district_eng
  gu_rank <- row_i$rank_UMC
  gu_umc  <- row_i$score_UMC
  
  # Combine district + Seoul average
  compare_df <- bind_rows(
    row_i %>% select(district_eng, all_of(score_cols)),
    avg_row
  )
  
  p_ind <- make_radar(compare_df,
                      sprintf("%s (Rank #%d, UMC = %.3f)", gu_name, gu_rank, gu_umc),
                      show_legend = TRUE)
  
  # Use English name for filename (lowercase, no spaces)
  fname <- tolower(gsub(" ", "_", gu_name))
  ggsave(sprintf("result/figures/radar/radar_%s.png", fname), p_ind,
         width = 7, height = 7, dpi = 300)
}
cat("✅ 25 individual radar charts saved to result/figures/radar/\n")


###############################################################################
# ── 5. CHOROPLETH MAP — Overall UMC ──────────────────────────
###############################################################################

# Try local shapefile first, fallback to geojson
if (file.exists("GIS/Seoul/Seoul.shp")) {
  seoul <- st_read("GIS/Seoul/Seoul.shp", quiet = TRUE)
  cat("Using: GIS/Seoul/Seoul.shp\n")
} else if (file.exists("raw/seoul_gu.geojson")) {
  seoul <- st_read("raw/seoul_gu.geojson", quiet = TRUE)
  cat("Using: raw/seoul_gu.geojson\n")
} else {
  stop("No spatial data found. Place Seoul.shp in GIS/Seoul/ or seoul_gu.geojson in raw/")
}

# Detect join column: 'name' (geojson) or 'SIGUNGU_NM' (shapefile)
if ("SIGUNGU_NM" %in% names(seoul)) {
  seoul_merged <- seoul %>%
    left_join(df, by = c("SIGUNGU_NM" = "district"))
} else if ("name" %in% names(seoul)) {
  seoul_merged <- seoul %>%
    left_join(df, by = c("name" = "district"))
} else {
  stop("Cannot find district name column in spatial data. Columns: ",
       paste(names(seoul), collapse = ", "))
}

p_map_umc <- ggplot(seoul_merged) +
  geom_sf(aes(fill = score_UMC), color = "white", linewidth = 0.3) +
  geom_sf_text(aes(label = district_eng), size = 2.3, color = "black") +
  scale_fill_distiller(palette = "RdYlGn", direction = 1,
                       name = "UMC Score", limits = c(0.2, 0.75)) +
  labs(title = "Overall UMC Score by District",
       subtitle = "Equal-weighted mean of 6 dimensions | Green = good, Red = vulnerable") +
  theme_void(base_size = 11) +
  theme(plot.title = element_text(face = "bold", size = 14),
        legend.position = "right")

ggsave("result/figures/fig_05_map_umc.png", p_map_umc,
       width = 8, height = 7, dpi = 300)
cat("✅ fig_05_map_umc.png\n")


###############################################################################
# ── 6. CHOROPLETH MAP — 6 Dimensions (Small Multiples) ───────
###############################################################################

map_long <- seoul_merged %>%
  select(district_eng, geometry, all_of(score_cols)) %>%
  pivot_longer(cols = all_of(score_cols), names_to = "dimension", values_to = "score") %>%
  mutate(dimension = factor(dimension, levels = score_cols, labels = names(dim_colors)))

p_map_facet <- ggplot(map_long) +
  geom_sf(aes(fill = score, geometry = geometry), color = "white", linewidth = 0.2) +
  facet_wrap(~ dimension, ncol = 3) +
  scale_fill_distiller(palette = "RdYlGn", direction = 1,
                       name = "Score", limits = c(0, 1)) +
  labs(title = "UMC Dimension Scores — Geographic Distribution",
       subtitle = "Min-Max normalized (0 = vulnerable, 1 = good)") +
  theme_void(base_size = 11) +
  theme(plot.title = element_text(face = "bold", size = 14),
        strip.text = element_text(face = "bold", size = 11),
        legend.position = "bottom")

ggsave("result/figures/fig_06_map_dimensions.png", p_map_facet,
       width = 12, height = 9, dpi = 300)
cat("✅ fig_06_map_dimensions.png\n")


###############################################################################
# ── Summary ──────────────────────────────────────────────────
###############################################################################

cat("\n===== Visualization Complete =====\n")
cat("result/figures/fig_01_heatmap.png          — 25 × 6 heatmap\n")
cat("result/figures/fig_02_bar_umc.png          — Overall UMC ranking\n")
cat("result/figures/fig_03_bar_stacked.png      — Dimension contributions\n")
cat("result/figures/fig_04_radar_top_bottom.png — Top 5 vs Bottom 5\n")
cat("result/figures/fig_05_map_umc.png          — UMC choropleth map\n")
cat("result/figures/fig_06_map_dimensions.png   — 6-dimension maps\n")
cat("result/figures/radar/radar_*.png           — 25 individual radars\n")
