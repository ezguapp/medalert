from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .models import Medicamento, RecordatorioMedicamento
from django.utils import timezone
from datetime import timedelta

def home(request):
    """Página principal. Muestra distinto contenido según el estado del usuario."""
    if request.user.is_authenticated:
        # Aquí podrías traer datos personalizados del usuario
        medicamentos = request.user.medicamentos.all()
        hidratacion = request.user.hidrataciones.order_by('-fecha').first()
        return render(request, 'App/home.html', {
            'medicamentos': medicamentos,
            'hidratacion': hidratacion,
        })
    else:
        return render(request, 'App/home.html')

def login_view(request):
    """Vista para manejar el login de usuarios."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Si el formulario viene desde AJAX
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            # Si es normal (no AJAX)
            return redirect('home')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Usuario o contraseña incorrectos'})
            
            messages.error(request, 'Usuario o contraseña incorrectos')

    return render(request, 'App/login.html')

def register_view(request):
    """Vista para manejar el registro de usuarios."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Validaciones básicas
        if password1 != password2:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Las contraseñas no coinciden'})
            messages.error(request, 'Las contraseñas no coinciden')
            return render(request, 'App/register.html')

        if User.objects.filter(username=username).exists():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'El nombre de usuario ya existe'})
            messages.error(request, 'El nombre de usuario ya existe')
            return render(request, 'App/register.html')

        # Crear usuario
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, '¡Cuenta creada con éxito! Ya puedes iniciar sesión.')
        return redirect('login')

    return render(request, 'App/register.html')

def logout_view(request):
    """Cerrar sesión y volver al inicio."""
    logout(request)
    return redirect('home')

# Medicamentos 

@login_required
def medicamentos_view(request):
    """Lista y creación de medicamentos del usuario."""
    medicamentos = Medicamento.objects.filter(usuario=request.user)

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        dosis = request.POST.get('dosis')
        frecuencia_horas = request.POST.get('frecuencia_horas')
        duracion_dias = request.POST.get('duracion_dias')
        instrucciones = request.POST.get('instrucciones')

        if nombre and dosis:
            Medicamento.objects.create(
                usuario=request.user,
                nombre=nombre,
                dosis=dosis,
                frecuencia_horas=frecuencia_horas or 0,
                duracion_dias=duracion_dias or 0,
                instrucciones=instrucciones
            )
            return redirect('medicamentos')

    return render(request, 'App/medicamentos.html', {'medicamentos': medicamentos})

@login_required
def eliminar_medicamento(request, id):
    """Eliminar un medicamento del usuario logeado."""
    medicamento = Medicamento.objects.filter(usuario=request.user, id=id).first()
    if medicamento:
        medicamento.delete()
    return redirect('medicamentos')