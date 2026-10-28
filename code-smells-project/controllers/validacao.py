from controllers.erros import ValidationError


def exige_objeto(dados):
    if not isinstance(dados, dict) or not dados:
        raise ValidationError("Dados inválidos")
    return dados


def eh_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def eh_inteiro(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)
