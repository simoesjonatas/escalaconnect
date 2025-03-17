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
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView, LoginView

from .views import base_view, calendario_view, redirect_to_home
from escala.views2 import carregar_funcoes

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(template_name='login.html', next_page='/'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),

    path('', base_view, name='base_page'),
    path('calendario/', calendario_view, name='calendario'),

    path('api/escala/', include('escala.urls')),
    path('api/equip/', include('equipe.urls')),
    path('api/events/', include('evento.urls')),
    path('api/user/', include('usuario.urls')),
    path('api/plan/', include('planejamento.urls')),
    path('api/busy/', include('ocupado.urls')),
    path('api/free/', include('disponivel.urls')),
    
    path('api/carregar_funcoes/', carregar_funcoes, name='carregar_funcoes'),


]

handler404 = 'escalaconnect.views.redirect_to_home'

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


