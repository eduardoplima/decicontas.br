# LLM rescoring against cleanlab-corrected gold

Predictions unchanged; only the gold labels (`golden`) were swapped for the
corrected version produced by `research.release.export_dataset`.

| Model | Span F1 | Span P | Span R | Token F1 |
| --- | ---: | ---: | ---: | ---: |
| deepseek-v4-flash_few_shot | 0.7527 | 0.7370 | 0.7691 | 0.8086 |
| gpt-4.1_few_shot | 0.7216 | 0.6560 | 0.8017 | 0.8002 |
| gpt-4.1-mini_few_shot | 0.6851 | 0.5946 | 0.8083 | 0.7812 |
| gpt-5.1_few_shot | 0.6833 | 0.6121 | 0.7734 | 0.7696 |
| qwen2.5-72b_few_shot | 0.6129 | 0.5481 | 0.6950 | 0.7020 |
| gpt-5.2_few_shot | 0.6047 | 0.5000 | 0.7647 | 0.7405 |
| gpt-4.1-nano_few_shot | 0.4325 | 0.3587 | 0.5447 | 0.5795 |
| gpt-5-mini_few_shot | 0.4092 | 0.2760 | 0.7908 | 0.5714 |
| llama-3.3-70b_few_shot | 0.3396 | 0.5956 | 0.2375 | 0.4023 |
