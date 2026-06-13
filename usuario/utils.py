from django.core.exceptions import ValidationError


def normalizar_telefone(value):
    """Normaliza um telefone para o formato canônico: só dígitos, com DDD, sem +55.

    Ex.: '+55 (21) 99276-9489' -> '21992769489'. Não inventa DDD: se o número
    vier sem DDD, devolve apenas os dígitos como estão.
    """
    if not value:
        return value
    digitos = ''.join(filter(str.isdigit, value))
    # Remove o código do país (55) de números internacionais: 55 + DDD + 8/9 dígitos.
    if len(digitos) in (12, 13) and digitos.startswith('55'):
        digitos = digitos[2:]
    return digitos


def validate_telefone(value):
    """Valida o formato canônico: 10 (fixo) ou 11 (celular) dígitos, com DDD."""
    digitos = normalizar_telefone(value)
    if not digitos:
        return
    if len(digitos) not in (10, 11) or digitos[0] == '0':
        raise ValidationError(
            "Informe o telefone com DDD, ex.: (21) 99999-9999."
        )


def formatar_telefone(value):
    """Formata o telefone canônico para exibição: (21) 99276-9489."""
    if not value:
        return ''
    digitos = ''.join(filter(str.isdigit, value))
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return value


def validate_cpf(value):
    """
    Valida o CPF informado.
    Regras:
    - Deve conter 11 números
    - Não pode conter uma sequência de números repetidos
    - Deve passar no cálculo dos dígitos verificadores
    """
    cpf = ''.join(filter(str.isdigit, value))  # Remove caracteres não numéricos

    if len(cpf) != 11:
        raise ValidationError("O CPF deve conter 11 dígitos.")

    if cpf in ("00000000000", "11111111111", "22222222222", "33333333333",
               "44444444444", "55555555555", "66666666666", "77777777777",
               "88888888888", "99999999999"):
        raise ValidationError("O CPF informado é inválido.")

    # Validação dos dígitos verificadores
    for i in range(9, 11):
        value_sum = sum(int(cpf[num]) * ((i + 1) - num) for num in range(0, i))
        digit = ((value_sum * 10) % 11) % 10
        if digit != int(cpf[i]):
            raise ValidationError("O CPF informado é inválido.")
