# LLM rescoring against cleanlab-corrected gold

Predictions unchanged; only the gold labels (`golden`) were swapped for the
corrected version produced by `research.release.export_dataset`.

| Model | Span F1 | Span P | Span R | Token F1 |
| --- | ---: | ---: | ---: | ---: |
| deepseek-v4-flash_few_shot | 0.7696 | 0.7390 | 0.8027 | 0.8335 |
| gpt-4.1_few_shot | 0.7365 | 0.6578 | 0.8367 | 0.8167 |
| gpt-5.1_few_shot | 0.7032 | 0.6190 | 0.8141 | 0.7813 |
| gpt-4.1-mini_few_shot | 0.6986 | 0.5962 | 0.8435 | 0.7937 |
| qwen2.5-72b_few_shot | 0.6237 | 0.5481 | 0.7234 | 0.7173 |
| gpt-5.2_few_shot | 0.6177 | 0.5028 | 0.8005 | 0.7505 |
| gpt-4.1-nano_few_shot | 0.4341 | 0.3544 | 0.5601 | 0.5809 |
| gpt-5-mini_few_shot | 0.4157 | 0.2776 | 0.8277 | 0.5687 |
| llama-3.3-70b_few_shot | 0.3558 | 0.6066 | 0.2517 | 0.4090 |
