from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms_signup import SignupForm
from .models import Usuario
from equipe.models import Equipe, MembrosEquipe
from django.contrib.auth.decorators import login_required

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            user.is_first_login = False
            user.save()
            return redirect('inscricao')
    else:
        form = SignupForm()
    
    return render(request, 'usuario/signup.html', {'form': form})

def termos_de_uso(request):
    return render(request, 'usuario/termos_de_uso.html')

@login_required
def inscricao(request):
    equipes = Equipe.objects.all()
    inscricoes = MembrosEquipe.objects.filter(usuario=request.user).select_related('equipe')
    inscricoes_dict = {inscricao.equipe.id: inscricao.aprovado for inscricao in inscricoes}
    return render(request, 'usuario/inscricao.html', {'equipes': equipes, 'inscricoes': inscricoes_dict})

@login_required
def candidatar_equipe(request, pk):
    equipe = get_object_or_404(Equipe, pk=pk)
    MembrosEquipe.objects.create(usuario=request.user, equipe=equipe)
    return inscricao(request)

def candidatar_equipe(request, pk):
    equipe = get_object_or_404(Equipe, pk=pk)
    # Verifica se o usuário já está inscrito nesta equipe
    if MembrosEquipe.objects.filter(usuario=request.user, equipe=equipe).exists():
        return inscricao(request)
    else:
        # Se nao estiver inscrito, cria a nova inscricao
        MembrosEquipe.objects.create(usuario=request.user, equipe=equipe)
        return inscricao(request)


@login_required
def cancelar_inscricao(request, pk):
    inscricao = get_object_or_404(MembrosEquipe, equipe_id=pk, usuario=request.user)
    inscricao.delete()
    return redirect('inscricao')  # Redireciona de volta para a lista de equipes
