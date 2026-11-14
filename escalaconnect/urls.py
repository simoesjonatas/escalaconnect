"""
URL configuration for escalaconnect project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView, LoginView

from .views import base_view, calendario_view, redirect_to_home, confirmar_presenca, view_enviar_confirmacao, privacidade
from escala.views import agenda_ics, carregar_funcoes
from equipe.views_pdf import pdf_por_link
from usuario.views_monitor import monitoramento_uso, monitoramento_app, monitoramento_fila
from .views_saude import saude_celery

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(template_name='login.html', next_page='/'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),

    path('', base_view, name='base_page'),
    path('calendario/', calendario_view, name='calendario'),
    path('monitoramento/', monitoramento_uso, name='monitoramento_uso'),
    path('monitoramento/app/', monitoramento_app, name='monitoramento_app'),
    path('monitoramento/fila/', monitoramento_fila, name='monitoramento_fila'),
    path('privacidade/', privacidade, name='privacidade'),
    # Saúde do Celery para monitoramento externo; com e sem a barra (sem redirect 301).
    re_path(r'^healthz/celery/?$', saude_celery, name='saude_celery'),
    # Link de agenda sem login, assinado (botões "Adicionar à agenda" do app).
    path('agenda/<str:token>.ics', agenda_ics, name='agenda_ics'),
    path('pdf/escala/<str:token>/', pdf_por_link, name='pdf_da_escala'),

    # API JSON do app mobile (as demais rotas api/... abaixo devolvem HTML).
    path('api/v1/', include('api.urls')),

    path('api/escala/', include('escala.urls')),
    path('api/equip/', include('equipe.urls')),
    path('api/events/', include('evento.urls')),
    path('api/user/', include('usuario.urls')),
    path('api/plan/', include('planejamento.urls')),
    path('api/busy/', include('ocupado.urls')),
    path('api/free/', include('disponivel.urls')),
    
    path('api/carregar_funcoes/', carregar_funcoes, name='carregar_funcoes'),

    path('teste/<int:evento_id>/notificar/', view_enviar_confirmacao, name='evento_notificar_confirmacao_2'),

    path(
        "api/escala/minhas-escalas/<int:evento_id>/<int:escala_id>/confirmar/",
        confirmar_presenca,
        name="minhas_escalas_confirmar",
    )



]

handler404 = 'escalaconnect.views.redirect_to_home'

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


