# LLM rescoring against cleanlab-corrected gold

Predictions unchanged; only the gold labels (`golden`) were swapped for the
corrected version produced by `research.release.export_dataset`.

| Model | Span F1 | Span P | Span R | Token F1 |
| --- | ---: | ---: | ---: | ---: |
| deepseek-v4-flash_few_shot | 0.7730 | 0.7182 | 0.8370 | 0.8387 |
| gpt-4.1_few_shot | 0.7263 | 0.6292 | 0.8589 | 0.8114 |
| gpt-5.1_few_shot | 0.7084 | 0.6052 | 0.8540 | 0.7886 |
| gpt-4.1-mini_few_shot | 0.6995 | 0.5801 | 0.8808 | 0.7967 |
| qwen2.5-72b_few_shot | 0.6526 | 0.5567 | 0.7883 | 0.7345 |
| gpt-5.2_few_shot | 0.6433 | 0.5100 | 0.8710 | 0.7653 |
| gpt-4.1-nano_few_shot | 0.4675 | 0.3716 | 0.6302 | 0.6122 |
| gpt-5-mini_few_shot | 0.4345 | 0.2852 | 0.9124 | 0.5837 |
| llama-3.3-70b_few_shot | 0.3434 | 0.5574 | 0.2482 | 0.4075 |
