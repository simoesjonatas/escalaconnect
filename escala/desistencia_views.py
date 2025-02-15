from django.shortcuts import render, redirect
from .desistencia_forms import DesistenciaForm
from .models import Desistencia, Escala
from django.contrib.auth.decorators import login_required

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
            escala.confirmada = False
            escala.save()
            return redirect('minhas_escalas')
    else:
        form = DesistenciaForm(user=request.user, escala=escala)


    return render(request, 'escala/desistencia.html', {'form': form, 'escala': escala})
