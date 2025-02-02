from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_ocupado, name='lista_ocupado'),
    path('adicionar/', views.adicionar_ocupado, name='adicionar_ocupado'),
    path('detalhes/<int:pk>/', views.detalhes_ocupado, name='detalhes_ocupado'),
    path('atualizar/<int:pk>/', views.atualizar_ocupado, name='atualizar_ocupado'),
    path('excluir/<int:pk>/', views.excluir_ocupado, name='excluir_ocupado'),


]
