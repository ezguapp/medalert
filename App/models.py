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

    # --- NUEVOS CAMPOS PARA HIDRATACIÓN ---
    peso_kg = models.FloatField(null=True, blank=True, help_text="Peso en kilogramos.")
    altura_cm = models.FloatField(null=True, blank=True, help_text="Altura en centímetros.")
    sexo = models.CharField(
        max_length=10,
        choices=[('M', 'Masculino'), ('F', 'Femenino')],
        null=True,
        blank=True
    )
    nivel_actividad = models.CharField(
        max_length=20,
        choices=[
            ('sedentario', 'Sedentario'),
            ('ligero', 'Actividad ligera (1-3 veces/semana)'),
            ('moderado', 'Actividad moderada (3-5 veces/semana)'),
            ('intenso', 'Actividad intensa diaria')
        ],
        null=True,
        blank=True,
        help_text="Nivel de actividad física"
    )

    def __str__(self):
        return self.user.username

    # --- FUNCIÓN PARA CALCULAR META DE AGUA ---
    def calcular_meta_agua_vasos(self):
        """
        Calcula la meta diaria de agua (en vasos de 250 ml)
        basada en el peso, sexo y nivel de actividad.
        """
        if not self.peso_kg:
            return 8  # valor por defecto si no hay datos

        # Base: 35 ml/kg
        agua_ml = self.peso_kg * 35

        # Ajuste según nivel de actividad
        if self.nivel_actividad == 'ligero':
            agua_ml += 300
        elif self.nivel_actividad == 'moderado':
            agua_ml += 600
        elif self.nivel_actividad == 'intenso':
            agua_ml += 1000

        # Ajuste leve por sexo
        if self.sexo == 'M':
            agua_ml += 250  # los hombres suelen tener más masa magra

        # Convertir a vasos (1 vaso ≈ 250 ml)
        vasos = round(agua_ml / 250)
        return vasos


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
