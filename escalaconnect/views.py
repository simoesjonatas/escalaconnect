from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect



# View para renderizar a página base
@login_required(login_url='/login/')
def base_view(request):
    # return render(request, 'base.html')
    return render(request, 'home/home.html')

# View para renderizar o calendário
@login_required(login_url='/login/')
def calendario_view(request):
    return render(request, 'calendario.html')

def custom_403(request, exception):
    return render(request, '403_forbidden.html', status=403)

def redirect_to_home(request, exception=None):
    return HttpResponseRedirect('/')