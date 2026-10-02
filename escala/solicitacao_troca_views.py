from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .solicitacao_desistencia_forms import DesistenciaForm
from .models import Escala, SolicitacaoTroca
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from equipe.decorators import require_lider, pode_gerenciar_equipe


@login_required
def solicitar_desistencia(request, escala_id):
    escala = get_object_or_404(Escala, id=escala_id, usuario=request.user)  # Garantindo que a escala pertence ao usuário
    if request.method == 'POST':
        form = DesistenciaForm(request.POST, user=request.user, escala=escala)
        if form.is_valid():
            desistencia = form.save(commit=False)
            desistencia.escala_origem = escala
            desistencia.solicitante = request.user
            desistencia.data_solicitacao = timezone.now()
            desistencia.save()
            messages.success(request, 'Solicitação de desistência enviada com sucesso!')
            return render(request, 'escala/minha_escala_detail.html', {'escala': escala, 'desistencia_form': form})
        else:
            # Renderiza novamente com o formulário e os erros
            return render(request, 'escala/minha_escala_detail.html', {'escala': escala, 'desistencia_form': form})
    else:
        # Se não for POST, cria um formulário vazio inicializado com usuário e escala
        form = DesistenciaForm(user=request.user, escala=escala)
        return render(request, 'escala/minha_escala_detail.html', {'escala': escala, 'desistencia_form': form})


@login_required
def cancelar_solicitacao_troca(request, escala_id):
    escala = get_object_or_404(Escala, id=escala_id, usuario=request.user)
    solicitacao = SolicitacaoTroca.objects.filter(escala_origem=escala, aprovada=False).first()
    if solicitacao:
        solicitacao.delete()  # Ou marque como 'cancelada' se você tiver um campo para isso
        messages.success(request, "Solicitação de troca cancelada com sucesso.")
    else:
        messages.error(request, "Nenhuma solicitação pendente encontrada.")
    return redirect('minha_escala_detail', pk=escala_id)


@require_lider
def detalhes_solicitacao_troca(request, troca_id):
    troca = get_object_or_404(SolicitacaoTroca, id=troca_id)
    # Só a liderança da equipe da escala (ou staff/superuser) pode ver.
    if not pode_gerenciar_equipe(request.user, troca.escala_origem.equipe):
        return render(request, '403_forbidden.html', status=403)
    return render(request, 'desistencia/detalhes_solicitacao_troca.html', {'troca': troca})

@login_required
@require_lider
def aprovar_solicitacao_troca(request, troca_id):
    troca = get_object_or_404(SolicitacaoTroca, id=troca_id)
    escala = troca.escala_origem

    # Só a liderança da equipe da escala (ou staff/superuser) pode aprovar.
    if not pode_gerenciar_equipe(request.user, escala.equipe):
        return render(request, '403_forbidden.html', status=403)

    # Aprovação altera estado: só por POST (o botão do template já envia POST).
    if request.method != "POST":
        return redirect('detalhes_solicitacao_troca', troca_id=troca.pk)

    # Já aprovada: não limpa a escala de novo (pode já ter outro voluntário nela).
    if not troca.aprovada:
        troca.lider_aprovador = request.user
        troca.aprovada = True
        troca.data_aprovacao = timezone.now()
        troca.save()
        # limpa a escala
        escala.clear_escala()
        messages.success(request, "Solicitação de troca aprovada com sucesso.")
    return redirect('escala_detail_equipe', equipe_pk=escala.funcao.equipe.pk, pk=escala.pk)
