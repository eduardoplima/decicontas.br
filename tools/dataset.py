import pandas as pd

def translate_golden(annotation):
    DICT_LABELS = {
        'MULTA_FIXA': 'MULTA',
        'MULTA_PERCENTUAL': 'MULTA',
        'OBRIGACAO_MULTA': 'OBRIGACAO'
    }

    def translate_spans(value_dict):
        return {
                'start': value_dict['start'],
                'end': value_dict['end'],
                'text': value_dict['text'],
                'labels': [DICT_LABELS.get(value_dict['labels'][0], value_dict['labels'][0])],
            }
            

    for a in annotation:
        if 'result' in a.keys() and a['result'] != []:
            for r in a['result']:
                r['value'] = translate_spans(r['value'])

    return annotation

def get_decicontas_df():
    """
    Returns a DataFrame containing the decicontas dataset.
    """

    return pd.read_json("dataset/labeled_data/decicontas.json")
