from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('medicamentos/', views.medicamentos_view, name='medicamentos'),
    path('medicamentos/eliminar/<int:id>/', views.eliminar_medicamento, name='eliminar_medicamento'),
    path('hidratacion/', views.hidratacion_view, name='hidratacion'),
    path('perfil/completar/', views.completar_perfil_view, name='completar_perfil'),
    path('medicamentos/<int:medicamento_id>/toma/', views.registrar_toma, name='registrar_toma'),
    path('medicamentos/<int:medicamento_id>/toma/', views.registrar_toma, name='registrar_toma'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
]
