from django.urls import path
from .views import equipe_list, equipe_create, equipe_update, equipe_delete, equipe_detail, candidatura_equipe
from .views_funcao import *
from .views_lideranca import *
from .views_membros import *
from .views_escala import *
from .views_pdf import *

urlpatterns = [
    path('', equipe_list, name='equipe_list'),
    path('create/', equipe_create, name='equipe_create'),
    path('<int:pk>/', equipe_detail, name='equipe_detail'),
    path('<int:pk>/edit/', equipe_update, name='equipe_update'),
    path('<int:pk>/delete/', equipe_delete, name='equipe_delete'),
    path('candidatura/', candidatura_equipe, name='processar_candidatura'),

    
    # funcao
    path('<int:equipe_pk>/funcoes/', funcao_list, name='listar_funcoes'),
    path('<int:equipe_pk>/funcoes/<int:pk>/', funcao_detail, name='funcao_detail'),
    path('<int:equipe_pk>/funcoes/adicionar/', funcao_create, name='funcao_create'),
    path('<int:equipe_pk>/funcao/<int:pk>/editar/', funcao_update, name='funcao_update'),
    path('<int:equipe_pk>/funcao/<int:pk>/excluir/', funcao_delete, name='funcao_delete'),
    
    #lideranca
    path('<int:equipe_pk>/liderancas/', lideranca_list, name='listar_liderancas'),
    path('lideranca/<int:pk>/', lideranca_detail, name='lideranca_detail'),
    path('<int:equipe_pk>/lideranca/adicionar/', lideranca_create, name='lideranca_create'),
    path('lideranca/<int:pk>/editar/', lideranca_update, name='lideranca_update'),
    path('lideranca/<int:pk>/excluir/', lideranca_delete, name='lideranca_delete'),
    
    #membros
    path('<int:equipe_pk>/membros/', membros_equipe_list, name='listar_membros_equipe'),
    path('<int:equipe_pk>/membro/<int:pk>/', membros_equipe_detail, name='membros_equipe_detail'),
    path('<int:equipe_pk>/membro/adicionar/', membros_equipe_create, name='membros_equipe_create'),
    path('<int:equipe_pk>/membro/<int:pk>/editar/', membros_equipe_update, name='membros_equipe_update'),
    path('<int:equipe_pk>/membro/<int:pk>/excluir/', membros_equipe_delete, name='membros_equipe_delete'),

    path('<int:equipe_pk>/escalas/', listar_escalas, name='listar_escalas'),
    path('<int:equipe_pk>/escalas/<int:pk>', escala_detail_equipe, name='escala_detail_equipe'),

    path('equipe/<int:equipe_pk>/escalas/exportar-pdf/', exportar_tabela_para_pdf, name='exportar_pdf'),
    
    path('equipe/<int:equipe_pk>/membros-pendentes/', listar_membros_pendentes, name='listar_membros_pendentes'),
    path('equipe/<int:equipe_pk>/aprovar-membro/<int:membro_pk>/', aprovar_membro, name='aprovar_membro'),
    path('equipe/<int:equipe_pk>/rejeitar-membro/<int:membro_pk>/', rejeitar_membro, name='rejeitar_membro'),


]
