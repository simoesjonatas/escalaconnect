from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import Equipe
from escala.models import Escala
from django.utils.timezone import now

from django.template.loader import render_to_string
from weasyprint import HTML

def exportar_tabela_para_pdf(request, equipe_pk):
    # Buscar dados da tabela
    equipe = get_object_or_404(Equipe, pk=equipe_pk)
    # escalas = Escala.objects.filter(funcao__equipe=equipe, evento__data_inicio__gte=now()).order_by('evento__data_inicio')
    escalas = Escala.objects.filter(funcao__equipe_id=equipe_pk).order_by('evento__data_inicio')

    # for i in escalas:
    #     print(i) 

    # Renderizar o HTML
    html_string = render_to_string('meu_template.html', {'escalas': escalas})
    
    # Criar um objeto HTML WeasyPrint
    html = HTML(string=html_string)

    # Gerar o PDF
    pdf = html.write_pdf()

    # Criar uma resposta HTTP com o PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="minha_tabela.pdf"'

    return response
