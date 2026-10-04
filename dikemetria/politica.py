"""Regras de LGPD do projeto (README, seção "Dados pessoais e LGPD") aplicadas no código.

* Regra 1: nada em segredo de justiça.
* Regra 6: matérias sensíveis (família, crianças e adolescentes, saúde, sexualidade, religião,
  violência doméstica) ficam marcadas e, por padrão, fora do corpus analisado e publicado.
* Regra 4: agregados com poucos casos não são publicados (supressão de células pequenas).
"""

from __future__ import annotations

import re

from dikemetria.limpeza import sem_acentos

# Grupos com menos casos que isso não aparecem em tabelas publicadas.
MINIMO_PUBLICAVEL = 10

_SEGREDO = re.compile(
    r"segredo de justica|tramita(?:m|ndo)? (?:sob|em) sigilo|processo sigiloso|sob sigilo"
)

_SENSIVEL = re.compile(
    r"\b(?:familia|alimentos|guarda|divorcio|uniao estavel|separacao|filiacao|paternidade|"
    r"maternidade|adocao|poder familiar|tutela de menor|infancia|juventude|crianca|adolescente|"
    r"menor de idade|ato infracional|estatuto da crianca|saude|tratamento medico|medicamento|"
    r"internacao|hospital|plano de saude|doenca|hiv|aids|deficiencia|interdicao|curatela|"
    r"orientacao sexual|identidade de genero|homofobia|transfobia|religi\w+|culto|"
    r"violencia domestica|maria da penha|estupro|dignidade sexual|abuso sexual)\b"
)


def em_segredo(nivel_sigilo: int | None = None, texto: str = "") -> bool:
    if nivel_sigilo:
        return True
    return bool(texto) and bool(_SEGREDO.search(sem_acentos(texto[:3000].lower())))


def materia_sensivel(*descricoes: str | None) -> bool:
    """Verdadeiro se classe, assuntos ou texto indicam matéria sensível."""
    base = sem_acentos(" ".join(d for d in descricoes if d).lower())
    return bool(_SENSIVEL.search(base))
