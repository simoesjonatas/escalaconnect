from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_ocupado, name='lista_ocupado'),
    path('adicionar/', views.adicionar_ocupado, name='adicionar_ocupado'),
    path('processar-indisponibilidade-evento/', views.processar_indisponibilidade_evento, name='processar_indisponibilidade_evento'),
    path('detalhes/<int:pk>/', views.detalhes_ocupado, name='detalhes_ocupado'),
    path('atualizar/<int:pk>/', views.atualizar_ocupado, name='atualizar_ocupado'),
    path('excluir/<int:pk>/', views.excluir_ocupado, name='excluir_ocupado'),
    path('registrar-indisponibilidade/', views.registrar_indisponibilidade_view, name='registrar_indisponibilidade'),
    path('registrar-indisponibilidade/por-horario/', views.adicionar_ocupado, name='registrar_por_horario'),
    path('registrar-indisponibilidade/por-evento/', views.registrar_por_evento, name='registrar_por_evento'),




]
