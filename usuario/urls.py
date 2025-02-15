from django.urls import path
from .views import usuario_list, usuario_detail, usuario_create, usuario_update, usuario_delete, perfil_usuario
from .views_pass import set_password, change_password, reset_user_password
from .views_signup import * 
urlpatterns = [
    path('', usuario_list, name='usuario_list'),
    path('<int:pk>/', usuario_detail, name='usuario_detail'),
    path('create/', usuario_create, name='usuario_create'),
    path('<int:pk>/update/', usuario_update, name='usuario_update'),
    path('<int:pk>/delete/', usuario_delete, name='usuario_delete'),
    
    path('set-password/', set_password, name='set_password'),
    path('change-password/', change_password, name='change_password'),
    path('reset-password/<int:user_id>/', reset_user_password, name='reset_user_password'),
    
    path('perfil/', perfil_usuario, name='perfil_usuario'),
    path('perfil/change-password/', change_password, name='change_password'),
    
    path('termos-de-uso/', termos_de_uso, name='termos_de_uso'),
    path('signup/', signup, name='signup'),
    path('inscricao/', inscricao, name='inscricao'),
    path('equipes/candidatar/<int:pk>/', candidatar_equipe, name='candidatar_equipe'),
    path('equipes/cancelar/<int:pk>/', cancelar_inscricao, name='cancelar_inscricao'),



]
