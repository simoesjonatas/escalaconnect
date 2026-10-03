"""Cliente mínimo da Expo Push API (https://docs.expo.dev/push-notifications/sending-notifications/)."""
import requests
from django.conf import settings

URL_ENVIO = 'https://exp.host/--/api/v2/push/send'
URL_RECIBOS = 'https://exp.host/--/api/v2/push/getReceipts'
LOTE = 100  # máximo de mensagens por requisição


def _post(url, corpo):
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    if settings.EXPO_ACCESS_TOKEN:
        headers['Authorization'] = f'Bearer {settings.EXPO_ACCESS_TOKEN}'
    resposta = requests.post(url, json=corpo, headers=headers, timeout=10)
    resposta.raise_for_status()
    return resposta.json().get('data')


def enviar(mensagens):
    """Envia as mensagens e devolve um ticket por mensagem, na mesma ordem."""
    tickets = []
    for i in range(0, len(mensagens), LOTE):
        tickets.extend(_post(URL_ENVIO, mensagens[i:i + LOTE]))
    return tickets


def recibos(ticket_ids):
    """Recibos de entrega dos tickets já processados: {ticket_id: recibo}."""
    return _post(URL_RECIBOS, {'ids': list(ticket_ids)}) or {}


def token_invalido(resultado):
    """True se o ticket/recibo diz que o aparelho não recebe mais push (app desinstalado, por exemplo)."""
    return (
        resultado.get('status') == 'error'
        and (resultado.get('details') or {}).get('error') == 'DeviceNotRegistered'
    )
