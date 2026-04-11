# 製程異常標準處置程序 SOP

## SOP-001：設備 OOC（Out of Control）處置程序

### 適用範圍
適用於所有製程設備發生 OOC 警報時的標準處理流程

### 處置步驟

**Step 1：確認警報類型（5 分鐘內）**
- 登入 MES 系統確認警報來源設備及參數
- 判斷為 1-sigma / 2-sigma / 3-sigma 超標
- 3-sigma 超標 → 立即 Hold 設備，通知 On-Call Engineer

**Step 2：資料蒐集（15 分鐘內）**
- 下載近 10 run 的製程參數趨勢
- 確認最近一次 PM（Preventive Maintenance）時間
- 確認最近一次設備 recipe 修改紀錄
- 確認同站其他設備是否有類似趨勢

**Step 3：根因分析（1 小時內）**
- 使用 Ishikawa（魚骨圖）分析：Machine / Method / Material / Man / Environment
- 優先排查：耗材壽命（靶材、燈管、閥門）、氣體純度、溫控系統
- 若多機台同步異常 → 懷疑共用設施（CDA、Chiller、Gas System）

**Step 4：處置行動**
- 輕微漂移（1~2 sigma）：調整 recipe 參數，觀察 2 run
- 中度超標（2~3 sigma）：通知 process owner，執行 recipe optimization
- 嚴重超標（>3 sigma）：Hold 設備，執行完整 PM，驗機後放行

**Step 5：關單前確認**
- 執行 3 片 qualification wafer 確認恢復正常
- 更新 SPC chart
- 填寫 8D 報告（若影響量產 lot）

---

## SOP-002：Lot Hold 處置程序

### Hold 觸發條件
1. 設備發生 OOC 且尚未確認影響範圍
2. 量測數據超過規格（out-of-spec）
3. 操作員發現異常（外觀、顏色、氣味）
4. 客訴或 OSAT 回饋可能相關批號

### Hold 執行步驟
1. 在 MES 系統對相關 lot 執行 Hold 操作，選擇 Hold reason
2. 同時 Hold 同機台同日生產之其他 lot（contamination risk 時）
3. 通知 Section Manager 及 Process Engineer
4. 保留 Hold lot 在隔離區（不得繼續加工）

### Hold 解除條件
- Process Engineer 完成根因確認
- 確認 Hold lot 不受影響，或執行補救措施後確認合格
- Section Manager 簽核放行

---

## SOP-003：MES 系統異常資料輸入規範

### 異常回報格式
```
設備 ID：[e.g., PECVD-01]
發生時間：[YYYY-MM-DD HH:MM]
異常參數：[e.g., Chamber Pressure]
測量值：[e.g., 5.2 Torr]
規格範圍：[e.g., 4.5 ± 0.3 Torr]
偏離方向：[HIGH / LOW]
受影響 Lot：[Lot ID 列表]
初步判斷：[操作員描述]
```

### AI 分析請求格式
當要求 AI Copilot 分析異常時，應提供：
1. 異常參數名稱及偏離方向
2. 受影響製程層別（layer）
3. 同站其他設備狀況（對比）
4. 近期 PM 紀錄
5. 是否已有 Hold lot

---

## SOP-004：定期保養（PM）排程規範

### PM 週期標準
| 設備類別 | PM 週期 | 觸發條件 |
|---------|---------|---------|
| PECVD | 每 500 RF-hours | 或粒子計數超標 |
| PVD | 每靶材 EOL 或 6 個月 | 靶材使用率 > 80% |
| CMP | 每 300 wafer passes | 或研磨速率漂移 >5% |
| 微影（Litho） | 每月一次 + 換燈 | 曝光能量漂移 >3% |
| 乾式蝕刻（Etch） | 每 200 RF-hours | 或速率漂移 >3% |

### PM 後驗機流程
1. 執行 dummy wafer run × 3（conditioning）
2. 量測關鍵參數（厚度 / Rs / 粒子）
3. 對比 PM 前 baseline，確認恢復
4. Process Engineer 確認簽核後 release 設備

---

## SOP-005：良率損失回報與分析

### 良率定義
- **Line yield**：製程中未被 Hold/Scrap 的 wafer 比例
- **Die yield**：最終測試通過的 die 數比例
- **Scrap rate**：本月報廢 wafer 數 / 投片總數

### 良率異常警戒線
- Scrap rate > 2%/月 → 觸發 Yield Review Meeting
- 單一機台造成 scrap > 5 wafers/周 → 觸發專案改善
- 同層別連續 2 批 OOS → 觸發緊急分析

### AI 輔助良率分析流程
1. 輸入製程層別及異常批號
2. AI 比對歷史記憶（相似案例）
3. AI 提供 root cause 假設排序（by confidence）
4. Engineer 確認並執行驗證實驗
5. 結果回饋 MES，更新記憶庫
