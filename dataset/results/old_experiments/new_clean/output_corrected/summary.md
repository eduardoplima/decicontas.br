# LLM rescoring against cleanlab-corrected gold

Predictions unchanged; only the gold labels (`golden`) were swapped for the
corrected version produced by `research.release.export_dataset`.

| Model | Span F1 | Span P | Span R | Token F1 |
| --- | ---: | ---: | ---: | ---: |
| deepseek-v4-flash_few_shot | 0.7233 | 0.7321 | 0.7146 | 0.7668 |
| gpt-4.1_few_shot | 0.7137 | 0.6488 | 0.7930 | 0.7990 |
| gpt-4.1-mini_few_shot | 0.6976 | 0.6174 | 0.8017 | 0.7838 |
| gpt-5.1_few_shot | 0.6833 | 0.6121 | 0.7734 | 0.7696 |
| qwen2.5-72b_few_shot | 0.6129 | 0.5481 | 0.6950 | 0.7020 |
| gpt-5.2_few_shot | 0.6047 | 0.5000 | 0.7647 | 0.7405 |
| gpt-5-mini_few_shot | 0.4092 | 0.2760 | 0.7908 | 0.5714 |
| gpt-4.1-nano_few_shot | 0.4011 | 0.3460 | 0.4771 | 0.5636 |
| llama-3.3-70b_few_shot | 0.3396 | 0.5956 | 0.2375 | 0.4023 |
