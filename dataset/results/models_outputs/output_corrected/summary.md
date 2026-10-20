# LLM rescoring against cleanlab-corrected gold

Predictions unchanged; only the gold labels (`golden`) were swapped for the
corrected version produced by `research.release.export_dataset`.

| Model | Span F1 | Span P | Span R | Token F1 |
| --- | ---: | ---: | ---: | ---: |
| deepseek-v4-flash_few_shot | 0.8238 | 0.7808 | 0.8718 | 0.8826 |
| gpt-4.1_few_shot | 0.7737 | 0.6827 | 0.8928 | 0.8557 |
| gpt-5.1_few_shot | 0.7532 | 0.6552 | 0.8858 | 0.8306 |
| gpt-4.1-mini_few_shot | 0.7388 | 0.6234 | 0.9068 | 0.8359 |
| qwen2.5-72b_few_shot | 0.6963 | 0.6048 | 0.8205 | 0.7766 |
| gpt-5.2_few_shot | 0.6879 | 0.5541 | 0.9068 | 0.8083 |
| gpt-4.1-nano_few_shot | 0.4867 | 0.3931 | 0.6387 | 0.6329 |
| gpt-5-mini_few_shot | 0.4530 | 0.3004 | 0.9207 | 0.6063 |
| llama-3.3-70b_few_shot | 0.3497 | 0.5847 | 0.2494 | 0.4166 |
