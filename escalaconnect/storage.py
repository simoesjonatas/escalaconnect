from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Storage de estáticos com hash no nome (cache-busting automático).

    Quando o conteúdo de um arquivo muda, o nome muda (ex.: styles.a1b2c3.css),
    então o navegador busca a versão nova sozinho — sem precisar limpar cache.

    É "tolerante": se um arquivo referenciado em url() de um CSS não existir
    (ex.: fontes do FontAwesome que faltam no projeto), NÃO derruba o
    collectstatic — apenas mantém aquela referência sem hash. Os arquivos que
    existem continuam ganhando hash normalmente.
    """

    manifest_strict = False

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            # Arquivo referenciado não encontrado: mantém o nome original.
            return name
