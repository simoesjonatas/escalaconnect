from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.urls import reverse
from .forms import UsuarioForm
from django.core.paginator import Paginator
from django.db.models import Q

User = get_user_model()

def can_change(user):
    # Verificar se o usuário é líder de equipe, staff ou superuser
    return user.groups.filter(name='Lideres').exists() or user.is_staff or user.is_superuser

@login_required
@user_passes_test(can_change)
def usuario_list(request):
    order_by = request.GET.get('order_by', 'username')  # Default ordering by 'username'
    direction = request.GET.get('direction', 'asc')
    query = request.GET.get('q', '')

    if direction == 'desc':
        order_by = f'-{order_by}'

    # Filtering based on the search query which can include username, email, etc.
    usuarios = User.objects.filter(
        Q(username__icontains=query) |
        Q(email__icontains=query) |
        Q(telefone__icontains=query)
    ).order_by(order_by)

    paginator = Paginator(usuarios, 10)  # 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Field headers for sorting
    usuario_fields = [
        ('username', 'Username'),
        ('email', 'Email'),
        ('telefone', 'Telefone'),
    ]

    context = {
        'page_obj': page_obj,
        'order_by': order_by.lstrip('-'),
        'direction': direction,
        'usuario_fields': usuario_fields,
        'query': query
    }
    return render(request, 'usuario/usuario_list.html', context)

@login_required
@user_passes_test(can_change)
def usuario_detail(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    return render(request, 'usuario/usuario_detail.html', {'usuario': usuario})

@login_required
@user_passes_test(can_change)
def usuario_create(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            return redirect('usuario_list')
    else:
        form = UsuarioForm()
    return render(request, 'usuario/usuario_form.html', {'form': form})

@login_required
@user_passes_test(can_change)
def usuario_update(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            return redirect('usuario_detail', pk=usuario.pk)
    else:
        form = UsuarioForm(instance=usuario)
    return render(request, 'usuario/usuario_form.html', {'form': form})

@login_required
@user_passes_test(can_change)
def usuario_delete(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        usuario.delete()
        return redirect('usuario_list')
    return render(request, 'usuario/usuario_confirm_delete.html', {'usuario': usuario})
