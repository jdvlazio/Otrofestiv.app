"""«Colombia, Francia» → ['CO', 'FR']. Lo contrario de herencia._pais_es."""
import json
import os

import ficha_obra


def iso(texto):
    with open(os.path.join(ficha_obra.REPO, 'pipeline', 'paises.json'), encoding='utf-8') as fh:
        d = json.load(fh)['iso']
    inv = {ficha_obra.NOMBRE.get(k, v['es']): k for k, v in d.items() if k not in ficha_obra.NO_PAIS}
    inv.update({v: k for k, v in ficha_obra.HISTORICO.items()})
    out = [inv.get(p.strip()) for p in texto.split(',') if p.strip()]
    if None in out or not out:
        raise ValueError(f'país sin código: {texto}')
    return out
