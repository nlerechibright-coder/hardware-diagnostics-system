import uuid

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from .forms import RegistrationForm
from .services.scanner import HardwareScanner, get_status_color
from .services.inference_engine import InferenceEngine
from .services.user_inference_engine import UserInferenceEngine
from .services.presentation import present_node
from .services.roles import IsTechnician, get_role_name, is_technician
from .models import DiagnosticRule, DiagnosticSession, NormalUserDiagnosticCase, UserProfile


def get_diagnostic_engine_for_user(user):
    return UserInferenceEngine() if not is_technician(user) else InferenceEngine()


def get_start_node_for_user(user):
    return 'user-root' if not is_technician(user) else 'CPU-Q1'


@login_required
def dashboard(request):
    """
    Serves the HTML frontend for the IAUE project defense.
    
    RESTORED: Now passes color_status context to template so the
    threshold color indicators (green/yellow/orange/red) render correctly.
    """
    scanner = HardwareScanner()
    diagnosis_data = scanner.get_diagnosis()
    
    color_status = diagnosis_data.get('color_status', {})
    
    stats = diagnosis_data.get('current_stats', {})
    metric_colors = {}
    for metric_key, threshold_key in [
        ('cpu_usage', 'cpu'),
        ('ram_usage', 'ram'),
        ('disk_usage', 'disk'),
        ('battery', 'battery'),
    ]:
        val = stats.get(metric_key)
        if val is not None:
            metric_colors[metric_key] = get_status_color(threshold_key, val)
        else:
            metric_colors[metric_key] = get_status_color(threshold_key, 0)

    recent_sessions = request.user.diagnostic_sessions.order_by('-started_at')[:5]
    
    context = {
        'diagnosis_data': diagnosis_data,
        'color_status': color_status,
        'metric_colors': metric_colors,
        'current_stats': stats,
        'overall_status': diagnosis_data.get('overall_status', 'UNKNOWN'),
        'recent_sessions': recent_sessions,
        'request_user': request.user,
        'role_label': get_role_name(request.user),
        'is_technician': is_technician(request.user),
    }
    
    return render(request, 'diagnostics/dashboard.html', context)


def signup(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            print(f"🔍 LOGIN DEBUG: User '{user.username}' authenticated. is_staff={user.is_staff}, is_active={user.is_active}")
            user = form.save()
            login(request, user)
            messages.success(request, 'Your account has been created successfully.')
            return redirect('dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'registration/signup.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            print(f"🔍 LOGIN DEBUG: User '{user.username}' authenticated. is_staff={user.is_staff}, is_active={user.is_active}")
            login(request, user)
            # Unified Authentication: Redirect managers to management dashboard, others to normal dashboard
            if user.is_staff:
                return redirect('manager_dashboard')
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


@method_decorator(login_required, name='dispatch')
class SystemStatusView(APIView):
    """
    API Endpoint that returns real-time hardware health data 
    and expert system diagnostics based on thresholds.
    """
    def get(self, request):
        scanner = HardwareScanner()
        data = scanner.get_diagnosis()
        return Response(data)


@method_decorator(login_required, name='dispatch')
class StartDiagnosisView(APIView):
    """
    Initializes a new interactive diagnostic session based on the server-side account type.
    """
    def get(self, request):
        technician_mode = is_technician(request.user)
        engine = get_diagnostic_engine_for_user(request.user)
        start_node_id = get_start_node_for_user(request.user)

        request.session['current_node'] = start_node_id
        request.session['step_count'] = 1
        request.session['history'] = []
        request.session['diagnostic_subsystem'] = 'technician' if technician_mode else 'normal_user'
        session_id = f"{request.user.username}-{uuid.uuid4().hex[:12]}"
        request.session['diagnostic_session_id'] = session_id
        request.session.modified = True

        if technician_mode:
            node = engine.get_node(start_node_id)
            DiagnosticSession.objects.create(
                session_id=session_id,
                user=request.user,
                current_node=DiagnosticRule.objects.filter(node_id=start_node_id).first(),
                diagnostic_subsystem='technician',
                status='active',
            )
            return Response({
                "step": 1,
                "node_id": start_node_id,
                "data": present_node(node, request.user),
            })

        node = engine.start()
        DiagnosticSession.objects.create(
            session_id=session_id,
            user=request.user,
            current_node=None,
            diagnostic_subsystem='normal_user',
            status='active',
        )
        return Response({
            "step": 1,
            "node_id": start_node_id,
            "data": node,
        })


@method_decorator(login_required, name='dispatch')
class SearchSymptomsView(APIView):
    """
    API endpoint for handling instant hardware symptom searches.
    """
    def get(self, request):
        query = request.query_params.get('q', '')
        engine = InferenceEngine()
        results = [present_node(node, request.user) for node in engine.search_symptoms(query)]
        return Response(results)


@method_decorator(login_required, name='dispatch')
class SelectSearchNodeView(APIView):
    """
    Bypasses standard forward traversal to seed the diagnostic state 
    directly with a chosen search path selection.
    """
    def post(self, request):
        engine = InferenceEngine()
        target_node_id = request.data.get('node_id')
        
        node = engine.get_node(target_node_id)
        if not node:
            return Response({"error": "Target diagnostic branch missing"}, status=400)
            
        if node.get('type') == 'solution':
            node = engine._apply_hybrid_logic(node)
        node = present_node(node, request.user)

        request.session['current_node'] = target_node_id
        request.session['step_count'] = 1
        request.session['history'] = [{
            "question": "Symptom Search System",
            "answer": f"Direct navigation via: '{node.get('text') if node.get('type') == 'question' else node.get('diagnosis')}'"
        }]
        request.session.modified = True

        session_id = request.session.get('diagnostic_session_id')
        if session_id:
            DiagnosticSession.objects.filter(session_id=session_id, user=request.user).update(
                current_node=DiagnosticRule.objects.filter(node_id=target_node_id).first(),
                status='active',
                path_taken=[target_node_id],
            )

        return Response({
            "step": 1,
            "node_id": target_node_id,
            "data": node,
            "session_history": request.session['history']
        })


class TechnicianHistoryView(APIView):
    permission_classes = [IsTechnician]

    def get(self, request):
        sessions = DiagnosticSession.objects.filter(user=request.user).values(
            'session_id', 'status', 'path_taken', 'started_at', 'updated_at', 'completed_at'
        )[:25]
        return Response({
            'role': 'Technician',
            'sessions': list(sessions),
        })


@method_decorator(login_required, name='dispatch')
class ProcessDiagnosisView(APIView):
    """
    Processes the user's answer and determines the next node in the tree.
    Includes reasoning, confidence levels, and session logging.
    """
    def post(self, request):
        technician_mode = is_technician(request.user)
        engine = get_diagnostic_engine_for_user(request.user)
        current_node_id = request.session.get('current_node', get_start_node_for_user(request.user))
        selected_index = request.data.get('answer_index')

        if technician_mode:
            current_node_data = engine.get_node(current_node_id)
            next_node, next_node_id = engine.process_step(current_node_id, selected_index)
            if not next_node or "error" in next_node:
                return Response({"error": "Diagnostic flow interrupted or invalid choice"}, status=400)
            presented_node = present_node(next_node, request.user)
        else:
            current_node_data = engine.get_case(current_node_id) or engine.start()
            next_node, next_node_id = engine.process_step(current_node_id, selected_index)
            if not next_node or "error" in next_node:
                return Response({"error": "Diagnostic flow interrupted or invalid choice"}, status=400)
            presented_node = next_node

        history = request.session.get('history', [])
        if current_node_data and current_node_data.get('type') == 'question':
            try:
                chosen_text = current_node_data['options'][selected_index]['text']
            except (IndexError, KeyError, TypeError):
                chosen_text = "Unknown Option"

            history.append({
                "question": current_node_data.get('text') or current_node_data.get('question'),
                "answer": chosen_text
            })
        request.session['history'] = history

        request.session['current_node'] = next_node_id
        request.session['step_count'] = request.session.get('step_count', 1) + 1
        request.session['diagnostic_subsystem'] = 'technician' if technician_mode else 'normal_user'
        request.session.modified = True

        session_id = request.session.get('diagnostic_session_id')
        if session_id:
            DiagnosticSession.objects.filter(session_id=session_id, user=request.user).update(
                current_node=DiagnosticRule.objects.filter(node_id=next_node_id).first() if technician_mode else None,
                diagnostic_subsystem='technician' if technician_mode else 'normal_user',
                status='completed' if next_node.get('type') == 'solution' else 'active',
                path_taken=[step.get('answer') for step in history if isinstance(step, dict)],
            )

        response_data = {
            "step": request.session['step_count'],
            "node_id": next_node_id,
            "data": presented_node,
            "session_history": history,
            "diagnostic_subsystem": 'technician' if technician_mode else 'normal_user',
        }

        if next_node.get('type') == 'solution':
            response_data['summary'] = "Diagnosis Complete"

        return Response(response_data)
# ==========================================
# MANAGER DASHBOARD & KNOWLEDGE MANAGEMENT
# ==========================================
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

def is_manager(user):
    return user.is_authenticated and user.is_staff

def manager_required(view_func):
    return user_passes_test(is_manager, login_url='login')(view_func)

def manager_login_view(request):
    if request.user.is_staff:
        return redirect('manager_dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            print(f"🔍 LOGIN DEBUG: User '{user.username}' authenticated. is_staff={user.is_staff}, is_active={user.is_active}")
            user = form.get_user()
            if user.is_staff:
                auth_login(request, user)
                return redirect('manager_dashboard')
            else:
                messages.error(request, 'You do not have manager privileges.')
    else:
        form = AuthenticationForm()
    return render(request, 'manager/login.html', {'form': form})

@manager_required
def manager_logout_view(request):
    auth_logout(request)
    return redirect('manager_login')

@manager_required
def manager_dashboard(request):
    context = {
        'total_rules': DiagnosticRule.objects.count(),
        'total_questions': DiagnosticRule.objects.filter(node_type='question').count(),
        'total_solutions': DiagnosticRule.objects.filter(node_type='solution').count(),
        'total_user_cases': NormalUserDiagnosticCase.objects.count(),
        'total_sessions': DiagnosticSession.objects.count(),
        'technicians': UserProfile.objects.filter(account_type='technician').count(),
        'normal_users': UserProfile.objects.filter(account_type='normal').count(),
        'recent_sessions': DiagnosticSession.objects.select_related('user').order_by('-started_at')[:10],
    }
    return render(request, 'manager/dashboard.html', context)

@manager_required
def manager_knowledge_list(request):
    rules = DiagnosticRule.objects.all().order_by('-updated_at')
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('node_type', '')
    if category_filter: rules = rules.filter(category__icontains=category_filter)
    if type_filter: rules = rules.filter(node_type=type_filter)
    return render(request, 'manager/knowledge_list.html', {'rules': rules, 'category_filter': category_filter, 'type_filter': type_filter})

@manager_required
def manager_knowledge_create(request):
    if request.method == 'POST':
        node_id = request.POST.get('node_id')
        if DiagnosticRule.objects.filter(node_id=node_id).exists():
            messages.error(request, 'Node ID already exists.')
            return redirect('manager_knowledge_create')
        rule = DiagnosticRule(
            node_id=node_id, category=request.POST.get('category'), title=request.POST.get('title'),
            node_type=request.POST.get('node_type', 'solution'), content=request.POST.get('content', ''),
            recommendation=request.POST.get('recommendation', ''), severity=request.POST.get('severity', 'MEDIUM'),
            search_keywords=request.POST.get('search_keywords', ''), is_active=request.POST.get('is_active') == 'on',
        )
        rule.save()
        rule.rebuild_search_index()
        messages.success(request, 'Diagnostic rule created successfully.')
        return redirect('manager_knowledge_list')
    return render(request, 'manager/knowledge_form.html', {'rule': None})

@manager_required
def manager_knowledge_edit(request, node_id):
    rule = get_object_or_404(DiagnosticRule, node_id=node_id)
    if request.method == 'POST':
        rule.category = request.POST.get('category')
        rule.title = request.POST.get('title')
        rule.node_type = request.POST.get('node_type', 'solution')
        rule.content = request.POST.get('content', '')
        rule.recommendation = request.POST.get('recommendation', '')
        rule.severity = request.POST.get('severity', 'MEDIUM')
        rule.search_keywords = request.POST.get('search_keywords', '')
        rule.is_active = request.POST.get('is_active') == 'on'
        rule.save()
        rule.rebuild_search_index()
        messages.success(request, 'Diagnostic rule updated successfully.')
        return redirect('manager_knowledge_list')
    return render(request, 'manager/knowledge_form.html', {'rule': rule})

@manager_required
def manager_knowledge_delete(request, node_id):
    rule = get_object_or_404(DiagnosticRule, node_id=node_id)
    if rule.active_sessions.filter(status='active').exists():
        messages.error(request, 'Cannot delete: Referenced by an active diagnostic session.')
        return redirect('manager_knowledge_list')
    rule.delete()
    messages.success(request, 'Diagnostic rule deleted successfully.')
    return redirect('manager_knowledge_list')

@manager_required
def manager_user_cases(request):
    cases = NormalUserDiagnosticCase.objects.all().order_by('-updated_at')
    return render(request, 'manager/user_cases.html', {'cases': cases})

@manager_required
def manager_user_case_create(request):
    if request.method == 'POST':
        case_id = request.POST.get('case_id')
        if NormalUserDiagnosticCase.objects.filter(case_id=case_id).exists():
            messages.error(request, 'Case ID already exists.')
            return redirect('manager_user_case_create')
        case = NormalUserDiagnosticCase(
            case_id=case_id, category=request.POST.get('category'), title=request.POST.get('title'),
            question=request.POST.get('question', ''), diagnosis=request.POST.get('diagnosis', ''),
            explanation=request.POST.get('explanation', ''), procedure=request.POST.get('procedure', ''),
            warning=request.POST.get('warning', ''), option_yes_text=request.POST.get('option_yes_text', 'Yes'),
            option_no_text=request.POST.get('option_no_text', 'No'), next_yes=request.POST.get('next_yes', ''),
            next_no=request.POST.get('next_no', ''), is_root=request.POST.get('is_root') == 'on',
            is_solution=request.POST.get('is_solution') == 'on',
        )
        case.save()
        messages.success(request, 'User case created successfully.')
        return redirect('manager_user_cases')
    return render(request, 'manager/user_case_form.html', {'case': None})

@manager_required
def manager_user_case_edit(request, case_id):
    case = get_object_or_404(NormalUserDiagnosticCase, case_id=case_id)
    if request.method == 'POST':
        case.category = request.POST.get('category')
        case.title = request.POST.get('title')
        case.question = request.POST.get('question', '')
        case.diagnosis = request.POST.get('diagnosis', '')
        case.explanation = request.POST.get('explanation', '')
        case.procedure = request.POST.get('procedure', '')
        case.warning = request.POST.get('warning', '')
        case.option_yes_text = request.POST.get('option_yes_text', 'Yes')
        case.option_no_text = request.POST.get('option_no_text', 'No')
        case.next_yes = request.POST.get('next_yes', '')
        case.next_no = request.POST.get('next_no', '')
        case.is_root = request.POST.get('is_root') == 'on'
        case.is_solution = request.POST.get('is_solution') == 'on'
        case.save()
        messages.success(request, 'User case updated successfully.')
        return redirect('manager_user_cases')
    return render(request, 'manager/user_case_form.html', {'case': case})

@manager_required
def manager_user_case_delete(request, case_id):
    case = get_object_or_404(NormalUserDiagnosticCase, case_id=case_id)
    case.delete()
    messages.success(request, 'User case deleted successfully.')
    return redirect('manager_user_cases')




