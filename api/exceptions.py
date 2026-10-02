from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler

from escalaconnect.regras import RegraDeNegocio


class ErroDeNegocio(exceptions.APIException):
    """Regra de negócio recusou a operação (400 com um código que o app entende)."""
    status_code = 400
    default_detail = 'Não foi possível concluir a operação.'
    default_code = 'erro'


def erros_do_form(form):
    """Converte os erros de um Django Form em ValidationError da API."""
    return exceptions.ValidationError({
        campo: [str(erro) for erro in erros]
        for campo, erros in form.errors.items()
    })


def exception_handler(exc, context):
    """Padroniza os erros da API em {"code", "detail"} (+ "errors" na validação).

    O app decide o que fazer pelo "code": por exemplo, senha_pendente e
    termo_pendente abrem a tela correspondente. Uma RegraDeNegocio levantada
    pelos services vira 400 com o code dela.
    """
    if isinstance(exc, RegraDeNegocio):
        exc = ErroDeNegocio(str(exc), code=exc.code)
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        response.data = {
            'code': 'validacao',
            'detail': 'Dados inválidos.',
            'errors': response.data,
        }
    else:
        codes = exc.get_codes()
        response.data = {
            'code': codes if isinstance(codes, str) else 'erro',
            'detail': response.data.get('detail', ''),
        }
    return response
