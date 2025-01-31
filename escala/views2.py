from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.http import JsonResponse
from escala.models import Escala, Funcao
from evento.models import Evento
from equipe.models import Equipe
from escala.forms import MultiEscalaForm
from equipe.decorators import require_lideranca 

@require_lideranca
def multi_escala_create(request, evento_pk):
    evento = get_object_or_404(Evento, pk=evento_pk)

    if request.method == 'POST':
        escalas = request.POST.getlist('escalas')  # Lista de escalas enviadas pelo formulário
        for escala in escalas:
            equipe_id, funcao_id = escala.split(',')
            equipe = get_object_or_404(Equipe, pk=equipe_id)
            funcao = get_object_or_404(Funcao, pk=funcao_id)

            Escala.objects.create(
                evento=evento,
                # equipe=equipe,
                funcao=funcao
            )

        return redirect(reverse('evento_escalas', args=[evento.pk]))

    form = MultiEscalaForm()
    return render(request, 'escala/multi_escala_form.html', {'form': form, 'evento': evento})

def carregar_funcoes(request):
    """Retorna funções filtradas por equipe via AJAX."""
    equipe_id = request.GET.get('equipe_id')
    if equipe_id:
        funcoes = Funcao.objects.filter(equipe_id=equipe_id).values('id', 'nome')
        return JsonResponse(list(funcoes), safe=False)
    return JsonResponse([], safe=False)
