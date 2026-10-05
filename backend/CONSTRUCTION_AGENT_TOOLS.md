# Construction AI Agent Tools — Lesson 14

This lesson adds three deterministic construction tools that can later be
connected to the Construction AI Assistant as agent tools.

## Tools

1. `calculate_concrete_volume` — length × width × depth → m³
2. `calculate_project_progress` — completed ÷ total × 100 → %
3. `calculate_material_balance` — required − available → remaining quantity

The tools contain no LLM calls. This is intentional: calculations should be
performed by reliable Python functions, while the AI decides which tool to use.

## Example results

- 10 m × 5 m × 0.2 m = **10 m³**
- 750 m completed out of 1,000 m = **75%**
- 500 tonnes required, 320 tonnes available = **180 tonnes remaining**

## Tests

From the `backend` directory:

```bash
pytest tests/test_construction_tools.py
```

Next step: connect these tools to the existing Gemini-based Construction AI
Assistant without replacing the current RAG/database architecture.
