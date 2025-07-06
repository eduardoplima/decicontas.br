# DeciContas.br Named Entity Recognition Pipeline

This repository contains the Python code and configuration for extracting named entities from decisions of the Rio Grande do Norte State Court of Accounts (TCE/RN), focused on auditing information such as fines, obligations, reimbursements, and recommendations. The project is part of the DeciContas.br dataset initiative.

The goal is to convert unstructured text in these decisions into structured data that can be monitored and analyzed systematically. The solution leverages Large Language Models (LLMs) deployed through Azure OpenAI, using function calling and few-shot prompting strategies inspired by the LexCare.BR project.

## Project Structure

- **tools/dataset.py**: loads the decicontas.br dataset
- **tools/prompt.py**: builds few-shot NER prompts
- **tools/schema.py**: defines the Pydantic data schema (Decisao and its components) and NER data schema (NERDecisao)
- **dataset/labeled_data/**: stores model outputs and annotations
- **ner.py**: runs the complete NER pipeline

## Legal Context

This project is aligned with TCE/RN rules governing:

- execution of fines and reimbursements ([Resolução 013/2015](./docs/Resolução_0132015_Dispõe_sobre_a_execução_das_decisões_TCERN__multaressarcimento.pdf))

It can support future auditing and compliance workflows by generating structured datasets from free-form decisions.

## Credits

- Inspired by LexCare.BR and its cross-domain NER approach
- Developed for the DeciContas.br research project
- Data sources: Tribunal de Contas do Estado do Rio Grande do Norte
- Developed in Python with langchain, pydantic, and Azure OpenAI
