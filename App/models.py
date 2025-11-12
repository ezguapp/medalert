from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# --- PERFIL DE USUARIO ---
class PerfilUsuario(models.Model):
    """Extiende la información del usuario base de Django."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    es_cuidador = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


# --- MEDICAMENTO ---
class Medicamento(models.Model):
    """Medicamentos registrados por cada usuario."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicamentos')
    nombre = models.CharField(max_length=100)
    dosis = models.CharField(max_length=50)
    frecuencia_horas = models.PositiveIntegerField(help_text="Cada cuántas horas debe tomarse.")
    duracion_dias = models.PositiveIntegerField(help_text="Duración del tratamiento en días.")
    instrucciones = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.usuario.username})"

    def fecha_fin(self):
        """Calcula automáticamente la fecha de término del tratamiento."""
        return timezone.now().date() + timezone.timedelta(days=self.duracion_dias)


# --- RECORDATORIO DE MEDICAMENTO ---
class RecordatorioMedicamento(models.Model):
    """Recordatorios generados a partir de un medicamento."""
    medicamento = models.ForeignKey(Medicamento, on_delete=models.CASCADE, related_name='recordatorios')
    hora = models.DateTimeField(help_text="Fecha y hora exacta del recordatorio.")
    tomado = models.BooleanField(default=False)
    fecha_toma = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Recordatorio de {self.medicamento.nombre} a las {self.hora.strftime('%H:%M')}"


# --- REGISTRO DE HIDRATACIÓN ---
class RegistroHidratacion(models.Model):
    """Registro diario de hidratación de cada usuario."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidrataciones')
    fecha = models.DateField(default=timezone.now)
    vasos_tomados = models.PositiveIntegerField(default=0)
    meta_vasos = models.PositiveIntegerField(default=8, help_text="Meta diaria de vasos.")

    def __str__(self):
        return f"Hidratación de {self.usuario.username} - {self.fecha}"

    def progreso(self):
        """Retorna el porcentaje de cumplimiento diario."""
        return round((self.vasos_tomados / self.meta_vasos) * 100, 1)


# --- NOTIFICACIONES (opcional, para futuras versiones) ---
class Notificacion(models.Model):
    """Registro de notificaciones enviadas (agua o medicamentos)."""
    TIPO_CHOICES = (
        ('medicamento', 'Medicamento'),
        ('agua', 'Agua'),
    )

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    mensaje = models.TextField()
    fecha_envio = models.DateTimeField(default=timezone.now)
    enviado = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación {self.tipo} - {self.usuario.username}"
