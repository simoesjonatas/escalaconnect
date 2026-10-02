class RegraDeNegocio(Exception):
    """Operação recusada por uma regra. `code` identifica o motivo para quem chama.

    Levantada pelos módulos services.py; o site mostra a mensagem ao usuário e a
    API do app a converte em erro 400 com o mesmo `code`.
    """

    def __init__(self, mensagem, code='erro'):
        super().__init__(mensagem)
        self.code = code
