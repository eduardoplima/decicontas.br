# LLM rescoring against cleanlab-corrected gold

Predictions unchanged; only the gold labels (`golden`) were swapped for the
corrected version produced by `tools.release.export_dataset`.

| Model | Span F1 | Span P | Span R | Token F1 |
| --- | ---: | ---: | ---: | ---: |
| gpt-5.4-nano_cot | 0.7613 | 0.7212 | 0.8061 | 0.7996 |
| gpt-4-turbo | 0.7584 | 0.6951 | 0.8344 | 0.8091 |
| gpt-5.4-mini_few_shot | 0.7566 | 0.7078 | 0.8126 | 0.7924 |
| gpt-4o | 0.7500 | 0.6885 | 0.8235 | 0.8032 |
| gpt-5.4-nano_few_shot | 0.7482 | 0.6933 | 0.8126 | 0.7876 |
| gpt-5.4-mini_cot | 0.7348 | 0.6862 | 0.7908 | 0.7928 |
| gemini-2.5-flash_cot | 0.7346 | 0.6673 | 0.8170 | 0.7750 |
| gpt-41-mini | 0.7337 | 0.6703 | 0.8105 | 0.7913 |
| gpt-35 | 0.7276 | 0.6691 | 0.7974 | 0.7891 |
| gemini-2.5-flash_two_stage | 0.7253 | 0.6578 | 0.8083 | 0.7738 |
| gpt-41 | 0.7250 | 0.6489 | 0.8214 | 0.7937 |
| gpt-5.4-nano_two_stage | 0.7196 | 0.6830 | 0.7603 | 0.7601 |
| gemini-2.5-flash_few_shot | 0.7093 | 0.6387 | 0.7974 | 0.7609 |
| gemini-2.5-flash_dynamic_few_shot | 0.7085 | 0.6360 | 0.7996 | 0.7797 |
| deepseek-v3_two_stage | 0.6954 | 0.6205 | 0.7908 | 0.7673 |
| gemini-2.5-pro_few_shot | 0.6927 | 0.5944 | 0.8301 | 0.7855 |
| gpt-5.4-nano_dynamic_few_shot | 0.6925 | 0.6519 | 0.7386 | 0.7417 |
| gpt-5.4-mini_dynamic_few_shot | 0.6800 | 0.6301 | 0.7386 | 0.7525 |
| gpt-5.4-mini_two_stage | 0.6798 | 0.6501 | 0.7124 | 0.7446 |
| deepseek-v3_few_shot | 0.6685 | 0.5887 | 0.7734 | 0.7414 |
| deepseek-v3_dynamic_few_shot | 0.5584 | 0.4564 | 0.7190 | 0.6785 |
| deepseek-v3_cot | 0.5250 | 0.5124 | 0.5381 | 0.6008 |
| gpt-41-nano | 0.4420 | 0.3615 | 0.5686 | 0.5738 |
| gemini-2.5-flash_self_refinement | 0.3924 | 0.2593 | 0.8061 | 0.5901 |
| gpt-5.4-mini_self_refinement | 0.3812 | 0.2920 | 0.5490 | 0.5801 |
| gpt-5.4-nano_self_refinement | 0.3383 | 0.2505 | 0.5207 | 0.5301 |
| deepseek-v3_self_refinement | 0.3377 | 0.2226 | 0.6993 | 0.5647 |
