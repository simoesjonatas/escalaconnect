"""Token assinado do link "confirmar presença" enviado por e-mail."""
from django.core import signing

SALT = 'confirmar-presenca'
VALIDADE = 60 * 60 * 24 * 60  # 60 dias


def token_de_confirmacao(escala):
    return signing.dumps({'e': escala.pk, 'u': escala.usuario_id}, salt=SALT)


def usuario_do_token(token, escala):
    """Devolve o id do voluntário se o token é válido para esta escala; senão None."""
    if not token:
        return None
    try:
        dados = signing.loads(token, salt=SALT, max_age=VALIDADE)
    except signing.BadSignature:  # inclui token expirado
        return None
    return dados.get('u') if dados.get('e') == escala.pk else None
