from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Equipe
from escala.models import Escala
from django.utils.timezone import now
from django.template.loader import render_to_string
from weasyprint import HTML
from datetime import datetime, timedelta
from django.utils.timezone import make_aware

def exportar_tabela_para_pdf(request, equipe_pk):
    if request.method == 'POST':
        equipe = get_object_or_404(Equipe, pk=equipe_pk)
        ano_atual = datetime.now().year
        
        
        # Dicionário de nomes de meses
        meses = {
            1: 'Janeiro',
            2: 'Fevereiro',
            3: 'Março',
            4: 'Abril',
            5: 'Maio',
            6: 'Junho',
            7: 'Julho',
            8: 'Agosto',
            9: 'Setembro',
            10: 'Outubro',
            11: 'Novembro',
            12: 'Dezembro'
        }

        # Capturando o mês a partir do POST
        mes_escolhido = request.POST.get('mes')
        mes = int(mes_escolhido) if mes_escolhido else datetime.now().month
        mes_nome = meses[mes]

        # Decidir o ano baseado no mês selecionado
        ano = ano_atual if mes >= datetime.now().month else ano_atual + 1

        # Determinar o início e o fim do mês selecionado
        inicio_mes = make_aware(datetime(ano, mes, 1))
        if mes == 12:
            fim_mes = make_aware(datetime(ano + 1, 1, 1)) - timedelta(seconds=1)
        else:
            fim_mes = make_aware(datetime(ano, mes + 1, 1)) - timedelta(seconds=1)

        # Filtrar escalas pelo mês e ano
        escalas = Escala.objects.filter(funcao__equipe_id=equipe_pk, evento__data_inicio__gte=inicio_mes, evento__data_inicio__lte=fim_mes).order_by('evento__data_inicio')

        # Renderizar o HTML
        html_string = render_to_string('meu_template.html', {'escalas': escalas, 'equipe': equipe, 'mes_nome': mes_nome})

        # Criar um objeto HTML WeasyPrint
        html = HTML(string=html_string)

        # Gerar o PDF
        pdf = html.write_pdf()

        # Nome do arquivo personalizado com nome da equipe e mês
        nome_mes = inicio_mes.strftime('%B').capitalize()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="escala_{equipe.nome}_{nome_mes}_{ano}.pdf"'

        return response
    else:
        # Retorna alguma resposta para método GET ou outro método não suportado
        return HttpResponse("Método não suportado", status=405)
