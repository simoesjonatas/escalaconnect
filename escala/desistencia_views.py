from django.shortcuts import render, redirect
from .desistencia_forms import DesistenciaForm
from .models import Desistencia, Escala
from . import services
from django.contrib.auth.decorators import login_required
from django.views.generic.detail import DetailView
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.auth import get_user_model
from equipe.decorators import require_lider, pode_gerenciar_equipe
from escala.utils import usuarios_disponiveis_para_evento

User = get_user_model()


@login_required
@require_lider
def aprovar_desistencia(request, desistencia_id):
    desistencia = get_object_or_404(Desistencia, pk=desistencia_id)
    escala = desistencia.escala  # Obtenha a escala relacionada à desistência

    # Só a liderança da equipe da escala (ou staff/superuser) pode aprovar.
    if not pode_gerenciar_equipe(request.user, escala.equipe):
        return render(request, '403_forbidden.html', status=403)

    if request.method == "POST":
        # Aprova e libera a vaga para outro voluntário (não faz nada se já aprovada).
        services.aprovar_desistencia(desistencia)
    return redirect('escala_detail_equipe', equipe_pk=escala.funcao.equipe.pk, pk=escala.pk)


@method_decorator(require_lider, name='dispatch')
class DetalhesDesistenciaPorEscalaView(DetailView):
    model = Desistencia
    template_name = 'desistencia/desistencia_detalhes.html'
    context_object_name = 'desistencia'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Só a liderança da equipe da escala (ou staff/superuser) pode ver.
        if not pode_gerenciar_equipe(request.user, self.object.escala.equipe):
            return render(request, '403_forbidden.html', status=403)
        return self.render_to_response(self.get_context_data(object=self.object))

    def get_object(self):
        # Obtenha a escala pelo ID fornecido na URL
        escala_id = self.kwargs.get('escala_id')
        # Encontre a desistência relacionada a essa escala
        desistencia = get_object_or_404(Desistencia, escala__id=escala_id, aprovada=False)
        return desistencia

    def get_context_data(self, **kwargs):
        # Quem está disponível para cobrir o furo caso a desistência seja aprovada.
        context = super().get_context_data(**kwargs)
        escala = self.object.escala
        if escala.funcao and escala.evento:
            ids = usuarios_disponiveis_para_evento(
                equipe=escala.funcao.equipe,
                evento=escala.evento,
                excluir_escala_id=escala.pk,
            )
        else:
            ids = []
        context['disponiveis'] = (
            User.objects.filter(id__in=ids)
            .exclude(pk=self.object.usuario_id)  # quem está desistindo não é candidato
            .order_by('first_name', 'username')
        )
        return context


@login_required
def create_desistencia(request, escala_id):
    usuario = request.user  # Usuário logado
    # Só o dono da escala pode sinalizar impedimento nela.
    escala = get_object_or_404(Escala, id=escala_id, usuario=usuario)

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
