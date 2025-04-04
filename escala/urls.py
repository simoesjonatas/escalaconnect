from django.urls import path
from .views import *
from escala.views import *
from escala.views2 import *
from escala.desistencia_views import *
from escala.solicitacao_troca_views import *

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
    
    path('desistencia/<int:escala_id>/', create_desistencia, name='sinalizar_impedimento'),
    path('solicitacao-troca/<int:escala_id>/desistencia', solicitar_desistencia, name='solicitar_desistencia'),
    path('solicitacao-troca/detalhes-troca/<int:troca_id>/', detalhes_solicitacao_troca, name='detalhes_solicitacao_troca'),
    path('solicitacao-troca/<int:escala_id>/cancelar-troca', cancelar_solicitacao_troca, name='cancelar_solicitacao_troca'),
    path('solicitacao-troca/aprovar-troca/<int:troca_id>/', aprovar_solicitacao_troca, name='aprovar_solicitacao_troca'),


    
    path('escala/<int:escala_id>/desistencia/', DetalhesDesistenciaPorEscalaView.as_view(), name='detalhes_desistencia_escala'),
    path('desistencia/aprovar/<int:desistencia_id>/', aprovar_desistencia, name='aprovar_desistencia'),




]
