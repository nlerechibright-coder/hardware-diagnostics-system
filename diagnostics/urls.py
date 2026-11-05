from django.urls import path
from .views import (
    SystemStatusView, dashboard, StartDiagnosisView, 
    ProcessDiagnosisView, SearchSymptomsView, SelectSearchNodeView,
    TechnicianHistoryView,
)

urlpatterns = [
    # Real-time Monitoring Endpoints
    path('status/', SystemStatusView.as_view(), name='system-status'),
    
    # Interactive Expert System Endpoints
    path('diagnosis/start/', StartDiagnosisView.as_view(), name='start-diagnosis'),
    path('diagnosis/process/', ProcessDiagnosisView.as_view(), name='process-diagnosis'),
    
    # Symptom Search endpoints
    path('diagnosis/search/', SearchSymptomsView.as_view(), name='search-symptoms'),
    path('diagnosis/select-search/', SelectSearchNodeView.as_view(), name='select-search-node'),
    path('technician/history/', TechnicianHistoryView.as_view(), name='technician-history'),
]