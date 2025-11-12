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

from datetime import datetime, timedelta
from django.utils import timezone

from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Medicamento, RegistroToma


# === Función auxiliar para calcular la próxima dosis ===
def calcular_proxima_toma(med):
    """
    Lógica:
    - Sin tomas previas -> NO hay countdown (remaining=0) y el botón está habilitado.
    - Con tomas previas  -> countdown hasta última_toma + frecuencia.
    """
    now = timezone.now()
    freq = timedelta(hours=med.frecuencia_horas or 0)

    last_toma = med.tomas.order_by('-fecha_hora').first() if hasattr(med, 'tomas') else None

    # 1) Nunca se ha tomado -> permitir tomar ahora (como antes con localStorage)
    if not last_toma or med.frecuencia_horas in (None, 0):
        return now, 0, True  # next_due, remaining_seconds, can_take

    # 2) Ya hubo una toma -> calcular próxima según frecuencia
    next_due = last_toma.fecha_hora + freq
    remaining_seconds = max(int((next_due - now).total_seconds()), 0)
    can_take = remaining_seconds == 0
    return next_due, remaining_seconds, can_take

def calcular_dias_restantes(med):
    """
    Días restantes = duracion_dias - días transcurridos desde created_at.
    Si no hay duracion_dias, retorna None.
    """
    if not med.duracion_dias:
        return None

    hoy = timezone.localdate()
    # usa created_at si existe; si no existe (aún no migras), asume hoy como inicio
    inicio = med.created_at.date() if hasattr(med, 'created_at') and med.created_at else hoy
    transcurridos = (hoy - inicio).days
    return max(med.duracion_dias - transcurridos, 0)
# === Vista principal de medicamentos ===
@login_required
def medicamentos_view(request):
    """Lista y creación de medicamentos del usuario + cálculo del temporizador."""
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
                frecuencia_horas=int(frecuencia_horas or 0),
                duracion_dias=int(duracion_dias or 0),
                instrucciones=instrucciones,
            )
            return redirect('medicamentos')

    # Calcular info para cada medicamento (contador y disponibilidad)
    meds_info = []
    for m in medicamentos:
        proxima, restantes, puede_tomar = calcular_proxima_toma(m)
        dias_rest = calcular_dias_restantes(m)
        meds_info.append({
            'obj': m,
            'restantes': restantes,
            'puede_tomar': puede_tomar,
            'proxima': proxima,
            'dias_restantes': dias_rest,   # ← lo pasamos al template
        })

    return render(request, 'App/medicamentos.html', {'meds_info': meds_info})


# === Endpoint AJAX para registrar toma ===
@login_required
@require_POST
def registrar_toma(request, medicamento_id):
    """Guarda una toma en la base de datos y devuelve nuevos segundos restantes."""
    try:
        med = Medicamento.objects.get(id=medicamento_id, usuario=request.user)
    except Medicamento.DoesNotExist:
        return JsonResponse({'error': 'Medicamento no encontrado'}, status=404)

    RegistroToma.objects.create(medicamento=med)
    _, restantes, _ = calcular_proxima_toma(med)
    return JsonResponse({'remaining_seconds': restantes})



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

from django.views.decorators.http import require_POST
from .models import Medicamento, RegistroToma
@login_required
@require_POST
def registrar_toma(request, medicamento_id):
    """Registra una nueva toma del medicamento y devuelve la próxima hora estimada."""
    try:
        medicamento = Medicamento.objects.get(id=medicamento_id, usuario=request.user)
    except Medicamento.DoesNotExist:
        return JsonResponse({'error': 'Medicamento no encontrado'}, status=404)

    # Crear registro de toma
    RegistroToma.objects.create(medicamento=medicamento)

    # Calcular hora de próxima dosis
    proxima = timezone.now() + timezone.timedelta(hours=medicamento.frecuencia_horas)
    return JsonResponse({
        'message': f"Toma registrada correctamente para {medicamento.nombre}",
        'proxima': proxima.strftime('%H:%M')
    })

from .models import PerfilUsuario
from .forms import PerfilUsuarioForm  # lo haremos abajo

@login_required
def perfil_usuario(request):
    """Muestra y permite editar los datos del perfil del usuario."""
    perfil, created = PerfilUsuario.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('perfil_usuario')
    else:
        form = PerfilUsuarioForm(instance=perfil)

    meta_agua = perfil.calcular_meta_agua_vasos() if perfil else 8

    return render(request, 'App/perfil.html', {
        'form': form,
        'perfil': perfil,
        'meta_agua': meta_agua,
    })