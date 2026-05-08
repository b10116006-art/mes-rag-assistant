# AI System Upgrade Roadmap (MES Copilot Enhancement)

## Objective
Enhance current AI MES Copilot system into a more complete AI application system by adding:
1. YOLO Computer Vision pipeline
2. Docker deployment
3. Simulated action layer

---

## Task 1 — YOLO Mini Project
Goal: dataset → training → inference → JSON output

Output example:
{
  "defect_type": "scratch",
  "confidence": 0.92,
  "bbox": [x, y, w, h]
}

---

## Task 2 — Dockerize System
- FastAPI
- MongoDB
- docker-compose

Run:
docker-compose up

---

## Task 3 — Action Simulation
Flow:
AOI → AI decision → action

Example:
{
  "action": "adjust_parameter",
  "target": "machine_A",
  "value": "-2%"
}

---

## Final Architecture
Data → AI → Decision → Action
