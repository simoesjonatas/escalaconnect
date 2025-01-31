from django.core.exceptions import ValidationError

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
