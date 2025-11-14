"""
URL configuration for SVA OAuth views.
"""
from django.urls import path
from . import views

app_name = 'sva_oauth_client'

urlpatterns = [
    path('login/', views.oauth_login, name='login'),
    path('callback/', views.oauth_callback, name='callback'),
    path('exchange/', views.oauth_exchange, name='exchange'),
    path('logout/', views.oauth_logout, name='logout'),
]

