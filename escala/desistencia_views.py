from django.shortcuts import render, redirect
from .desistencia_forms import DesistenciaForm
from .models import Desistencia, Escala
from django.contrib.auth.decorators import login_required
from django.views.generic.detail import DetailView
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from equipe.decorators import require_lider


@login_required
@require_lider
def aprovar_desistencia(request, desistencia_id):
    desistencia = get_object_or_404(Desistencia, pk=desistencia_id)
    escala = desistencia.escala  # Obtenha a escala relacionada à desistência

    if request.method == "POST":
        if not desistencia.aprovada:
            desistencia.aprovada = True
            desistencia.data_aprovacao = timezone.now()
            desistencia.save()
            
            # tirar a data de confirmacao da escala 
            escala.data_confirmacao = None
            # tirar a a confirmacao
            escala.confirmada = False
            # tirar o usuario para add outro
            escala.usuario = None
            escala.save()
            
            return redirect('escala_detail_equipe', equipe_pk=escala.funcao.equipe.pk, pk=escala.pk)
        else:
            # A desistência já foi aprovada, talvez mostrar uma mensagem
            return redirect('escala_detail_equipe', equipe_pk=escala.funcao.equipe.pk, pk=escala.pk)
    else:
        # Método não é POST, redirecione de volta à página de detalhes
        return redirect('escala_detail_equipe', equipe_pk=escala.funcao.equipe.pk, pk=escala.pk)


@method_decorator(require_lider, name='dispatch')
class DetalhesDesistenciaPorEscalaView(DetailView):
    model = Desistencia
    template_name = 'desistencia/desistencia_detalhes.html'
    context_object_name = 'desistencia'
    
    def get_object(self):
        # Obtenha a escala pelo ID fornecido na URL
        escala_id = self.kwargs.get('escala_id')
        # Encontre a desistência relacionada a essa escala
        desistencia = get_object_or_404(Desistencia, escala__id=escala_id, aprovada=False)
        return desistencia


@login_required
def create_desistencia(request, escala_id):
    usuario = request.user  # Usuário logado
    escala = Escala.objects.get(id=escala_id)  # Obter a escala pelo ID passado, ajuste conforme necessário

    if request.method == 'POST':
        form = DesistenciaForm(request.POST, user=request.user, escala=escala)
        if form.is_valid():
            desistencia = form.save(commit=False)
            desistencia.usuario = usuario
            desistencia.escala = escala
            desistencia.save()
            # movido para aprovar desistencia
            # escala.confirmada = False
            # escala.save()
            return redirect('minhas_escalas')
    else:
        form = DesistenciaForm(user=request.user, escala=escala)


    return render(request, 'escala/desistencia.html', {'form': form, 'escala': escala})
