from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """Retorna a querystring atual substituindo apenas os parâmetros informados.

    Preserva filtros ativos (busca, equipe, ordenação etc.) ao trocar de página
    ou de ordenação. Uso: <a href="?{% url_replace page=2 %}">
    """
    params = context['request'].GET.copy()
    for chave, valor in kwargs.items():
        params[chave] = valor
    return params.urlencode()
