# FAB Copilot AI 判斷邏輯說明文件

## 1. 系統架構概述

FAB Copilot 是一套整合在 MES（製造執行系統）內的 AI 輔助決策工具。
主要功能：
- 接收即時製程數據，判斷異常類型與嚴重程度
- 從歷史記憶（ai_memory_events）中調取相似案例
- 輸出結構化建議，供工程師快速決策
- 透過 LINE Bot 推送高風險警示

---

## 2. 核心判斷參數

### 2.1 anomaly_type 分類
| 類型代碼 | 說明 | 常見層別 |
|---------|------|---------|
| `thickness_ood` | 厚度超規格（偏厚或偏薄） | ILD, BPSG, Gate Oxide |
| `particle_count` | 粒子污染超標 | 所有層別 |
| `sheet_resistance` | 片電阻偏離 | TiN, W-plug, Metal |
| `uniformity_fail` | 均勻性不佳（Uniformity > 2%） | ILD, CMP |
| `etch_rate_drift` | 蝕刻速率漂移 | Etch 各層 |
| `cd_shift` | 線寬偏移（Critical Dimension） | Gate, Metal |
| `void_detected` | 空洞缺陷 | W-plug, STI fill |
| `general` | 無法歸類的一般異常 | 任何層別 |

### 2.2 risk_level 計算邏輯
```
HIGH  → anomaly_type in [void_detected, cd_shift]
        OR scrap_count > 3
        OR confidence > 0.85 AND worsening=True

MEDIUM → scrap_count 1~3
         OR anomaly_type in [thickness_ood, sheet_resistance]
         OR 新案例（is_existing_case=False）

LOW   → 已存在案例（is_existing_case=True）
        AND case_progression = "improving"
        AND confidence < 0.6
```

### 2.3 case_progression 判斷規則
比較當次 evidence 與前次 workflow snapshot：
- `improving`：scrap_count 下降 AND confidence 下降
- `worsening`：scrap_count 上升 OR risk_level 升高
- `stable`：變化在誤差範圍內

---

## 3. 記憶系統（ai_memory_events）

### 3.1 記憶寫入條件
每次 LLM 成功分析後，自動寫入：
- 時間戳記（ts）
- 機台 ID（machine_id）
- 製程層別（layer）
- 異常類型（anomaly_type）
- 信心分數（confidence）
- 根因假設列表（possible_root_causes）
- 建議行動（recommended_actions）

### 3.2 記憶檢索邏輯（Ranked Retrieval）
排序優先順序：
1. 相同 layer（完全匹配 +10 分）
2. 相同 machine_id（+8 分）
3. 相同 anomaly_type（+6 分）
4. 近 7 天內的記錄（+4 分）
5. confidence > 0.7 的記錄（+2 分）

### 3.3 記憶注入 Prompt 格式
```
[Historical Context]
Similar case on {machine_id} ({layer}), {N} days ago:
- anomaly_type: {anomaly_type}
- confidence: {confidence}
- root_causes: {possible_root_causes}
- actions taken: {recommended_actions}
- outcome: {case_progression}
```

---

## 4. Workflow 管理

### 4.1 Workflow 生命週期
```
新案例 → workflow_id 建立（case_status: "open"）
    ↓
重複分析同案例 → 重用相同 workflow_id
    ↓
case_progression = "improving" + risk = "LOW" + is_existing = True
    ↓
auto_close → case_status: "resolved"
    ↓
下次新異常 → 建立新 workflow_id
```

### 4.2 Trigger Gate 邏輯
| trigger_gate | 條件 | 行為 |
|-------------|------|------|
| `blocked` | case_status="resolved" 或 trigger_type="monitor_only" | 不發送 LINE |
| `preview_eligible` | suggested_channel="line_bot" + case 未 resolved | 顯示預覽，待確認 |
| `advisory` | 其他情況 | 僅 dashboard 顯示 |

---

## 5. 常見工程師問答 FAQ

**Q：AI 的建議一定要執行嗎？**
A：不，AI 輸出為「建議」性質，最終決策需工程師確認。AI 的角色是快速縮小排查範圍，提供根因假設清單，節省工程師分析時間。

**Q：信心分數（confidence）代表什麼？**
A：代表 AI 對當前異常判斷的確定程度（0~1）。< 0.5 表示資訊不足，建議人工深入分析；> 0.8 表示歷史有高度相似案例支撐。

**Q：為什麼有時候 evidence_source 是 "memory" 有時候是 "live"？**
A：`memory` 表示 AI 找到相似歷史案例並參考其分析；`live` 表示純基於當前數據，無歷史比對。memory-backed 的判斷通常更準確。

**Q：如何讓 AI 分析更準確？**
A：提供更完整的 evidence 資訊，包括：多機台對比數據、近期 PM 記錄、相同層別其他參數。資訊越完整，根因假設越精準。

**Q：LINE Bot 何時會自動發送警示？**
A：需要 `LINE_E2_AUTO_EXECUTE=true`（生產環境需謹慎啟用），且 trigger_gate="preview_eligible"，以及 10 分鐘 dedup 窗口無重複。預設為 preview-only 模式。
