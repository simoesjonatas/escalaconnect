from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_disponivel, name='lista_disponivel'),
    path('adicionar/', views.adicionar_disponivel, name='adicionar_disponivel'),
    path('editar/<int:pk>/', views.editar_disponivel, name='editar_disponivel'),
    path('excluir/<int:pk>/', views.excluir_disponivel, name='excluir_disponivel'),
    path('detalhes/<int:pk>/', views.detalhes_disponivel, name='detalhes_disponivel'),

    path('registrar-disponibilidade/', views.registrar_disponibilidade_view, name='registrar_disponibilidade'),
    path('registrar-disponibilidade/por-horario/', views.adicionar_disponivel, name='registrar_disponibilidade_horario'),
    path('registrar-disponibilidade/por-evento/', views.registrar_por_evento, name='registrar_disponibilidade_evento'),
    path('processar-disponibilidade-evento/', views.processar_disponibilidade_evento, name='processar_disponibilidade_evento'),

]
