from django.urls import path
from .views import *
from escala.views import *
from escala.views2 import *

urlpatterns = [
    
    path('minhas-escalas/', minhas_escalas, name='minhas_escalas'),
    path('minhas-escalas/<int:pk>/', minha_escala_detail, name='minha_escala_detail'),
    path('minhas-escalas/<int:pk>/confirmar/', confirmar_minha_escala, name='confirmar_minha_escala'),

    
    path('<int:pk>/escalas/adicionar/', escala_create, name='escala_create'),
    path('<int:pk>/editar/', escala_update, name='escala_update'),
    path('<int:pk>/excluir/', escala_delete, name='escala_delete'),
    path('<int:pk>/', escala_detail, name='escala_detail'),
    
    path('escala/<int:escala_id>/escalar/<int:usuario_id>/', escalar_usuario, name='escalar_usuario'),
    path('escala/<int:escala_id>/escalar/<int:usuario_id>/equipe', escalar_usuario_equipe, name='escalar_usuario_equipe'),
    path('escala/<int:escala_id>/cancelar/', cancelar_escala, name='cancelar_escala'),
    path('escala/<int:escala_id>/cancelar/equipe', cancelar_escala_equipe, name='cancelar_escala_equipe'),


]
