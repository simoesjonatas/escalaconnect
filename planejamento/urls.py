from django.urls import path
from .views import (
    planejamento_list, planejamento_create, planejamento_update,
    planejamento_delete, planejamento_detail
)

urlpatterns = [
    path('', planejamento_list, name='planejamento_list'),
    path('adicionar/', planejamento_create, name='planejamento_create'),
    path('<int:pk>/editar/', planejamento_update, name='planejamento_update'),
    path('<int:pk>/excluir/', planejamento_delete, name='planejamento_delete'),
    path('<int:pk>/', planejamento_detail, name='planejamento_detail'),
]
