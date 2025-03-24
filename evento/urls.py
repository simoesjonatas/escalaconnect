from django.urls import path
from .views import *
from escala.views import *
from escala.views2 import *
from evento.views_recorrente import *
from evento.views_planejamento import *
from evento.views_evento_recorrente import *

urlpatterns = [
    path('', eventos_api, name='eventos_api'),
    path('create/', criar_evento, name='criar_evento'),
    path('update/<int:event_id>/', atualizar_evento, name='atualizar_evento'),
    path('delete/<int:event_id>/', excluir_evento, name='excluir_evento'),
    
    path('lista', evento_list, name='evento_list'),
    path('create/event', evento_create, name='evento_create'),
    path('<int:pk>/', evento_detail, name='evento_detail'),
    path('<int:pk>/edit/', evento_update, name='evento_update'),
    path('<int:pk>/delete/', evento_delete, name='evento_delete'),

    #escala
    path('<int:pk>/escalas/', escalas_por_evento, name='evento_escalas'),
    path('<int:pk>/escala/adicionar/', escala_create, name='escala_create'),
    path('<int:pk>/editar/', escala_update, name='escala_update'),
    path('<int:pk>/deletar/', escala_delete, name='escala_delete'),
    path('<int:pk>/detail', escala_detail, name='escala_detail'),
    
    path('<int:evento_pk>/escala/adicionar-multiplas/', multi_escala_create, name='multi_escala_create'),

    # eventos recorrentes
    path('eventos/adicionar-recorrente/', evento_create_recorrente, name='evento_create_recorrente'),

    # planejamento 
    path('planejamento-equipes/', planejamento_equipes, name='planejamento_equipes'),
    path('evento-planejamento-equipes/', create_evento_planejamento, name='create_evento_planejamento'),
    
    # evento com planejamento recorrente
    path('gerar-eventos-planejamento/', gerar_eventos_planejamento, name='gerar_eventos_planejamento'),
    
    #notificar    
    path('evento/<int:evento_id>/notificar-confirmacao/', view_enviar_confirmacao, name='evento_notificar_confirmacao'),
    path('evento/<int:evento_id>/notificar-colaboradores/', view_enviar_lembrete, name='evento_notificar_colaboradores'),


]
