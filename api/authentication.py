from knox.auth import TokenAuthentication as KnoxTokenAuthentication

from usuario.services import registrar_atividade


class TokenAuthentication(KnoxTokenAuthentication):
    """Token do knox que também conta o uso do app no monitoramento.

    Registra a atividade aqui, ao validar o token, em vez de depender de o DRF
    propagar o usuário para o request que o AtividadeMiddleware lê depois da view.
    A chamada repetida não custa nada: o registro é limitado a um por minuto.
    """

    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado is not None:
            registrar_atividade(resultado[0])
        return resultado
