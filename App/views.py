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
        medicamentos = request.user.medicamentos.all()
        hidratacion = None

        hoy = timezone.now().date()

        try:
            perfil = PerfilUsuario.objects.get(user=request.user)

            # Buscar registro de hidratación del día
            hidratacion = RegistroHidratacion.objects.filter(
                usuario=request.user, fecha=hoy
            ).first()

            # Si no existe, crearlo automáticamente (si perfil completo)
            if not hidratacion and all([
                perfil.peso_kg,
                perfil.altura_cm,
                perfil.sexo,
                perfil.nivel_actividad
            ]):
                hidratacion = RegistroHidratacion.objects.create(
                    usuario=request.user,
                    fecha=hoy,
                    meta_vasos=perfil.calcular_meta_agua_vasos()
                )

        except PerfilUsuario.DoesNotExist:
            # Si aún no tiene perfil, simplemente no mostrar nada
            pass

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
                instrucciones=instrucciones,
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


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import PerfilUsuario, RegistroHidratacion
from .forms import PerfilUsuarioForm


@login_required
def hidratacion_view(request):
    """Muestra el control de hidratación o redirige a completar perfil si faltan datos."""
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)

    # Verificar si faltan datos fisiológicos
    if not all([perfil.peso_kg, perfil.altura_cm, perfil.sexo, perfil.nivel_actividad]):
        return redirect('completar_perfil')

    # Obtener o crear registro diario de hidratación
    hoy = timezone.now().date()
    registro, _ = RegistroHidratacion.objects.get_or_create(
        usuario=request.user,
        fecha=hoy,
        defaults={'meta_vasos': perfil.calcular_meta_agua_vasos()}
    )

    # Incrementar vasos si se presiona el botón "+1"
    if request.method == 'POST' and 'agregar_vaso' in request.POST:
        registro.vasos_tomados += 1
        registro.save()
        return redirect('hidratacion')

    progreso = registro.progreso()
    return render(request, 'App/hidratacion.html', {
        'registro': registro,
        'progreso': progreso
    })


@login_required
def completar_perfil_view(request):
    """Permite al usuario completar su perfil antes de acceder a hidratación."""
    perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('hidratacion')
    else:
        form = PerfilUsuarioForm(instance=perfil)
    return render(request, 'App/completar_perfil.html', {'form': form})
