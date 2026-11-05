from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LogoutView
from diagnostics.views import (
    dashboard, signup, user_login,
    manager_dashboard, manager_knowledge_list, manager_knowledge_create, 
    manager_knowledge_edit, manager_knowledge_delete,
    manager_user_cases, manager_user_case_create, manager_user_case_edit, manager_user_case_delete
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', signup, name='signup'),
    path('accounts/login/', user_login, name='login'), # <-- UNIFIED LOGIN URL
    path('accounts/logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('api/', include('diagnostics.urls')),
    
    # Custom Manager Routes (Protected by @manager_required decorator)
    path('manager/', manager_dashboard, name='manager_dashboard'),
    path('manager/knowledge/', manager_knowledge_list, name='manager_knowledge_list'),
    path('manager/knowledge/create/', manager_knowledge_create, name='manager_knowledge_create'),
    path('manager/knowledge/edit/<str:node_id>/', manager_knowledge_edit, name='manager_knowledge_edit'),
    path('manager/knowledge/delete/<str:node_id>/', manager_knowledge_delete, name='manager_knowledge_delete'),
    path('manager/user-cases/', manager_user_cases, name='manager_user_cases'),
    path('manager/user-cases/create/', manager_user_case_create, name='manager_user_case_create'),
    path('manager/user-cases/edit/<str:case_id>/', manager_user_case_edit, name='manager_user_case_edit'),
    path('manager/user-cases/delete/<str:case_id>/', manager_user_case_delete, name='manager_user_case_delete'),
]
