from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from diagnostics.models import DiagnosticSession, UserProfile
from diagnostics.services.inference_engine import InferenceEngine
from diagnostics.services.presentation import present_node
from diagnostics.services.roles import get_account_type, is_technician


class AuthAndRoleTests(TestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_signup_creates_normal_user_by_default(self):
        payload = {
            'username': 'alice',
            'email': 'alice@example.com',
            'account_type': 'normal',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }

        response = self.client.post(reverse('signup'), payload)
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username='alice')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(get_account_type(user), 'normal')
        self.assertFalse(is_technician(user))

    def test_technician_signup_creates_technician_account(self):
        payload = {
            'username': 'techie',
            'email': 'techie@example.com',
            'account_type': 'technician',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }

        response = self.client.post(reverse('signup'), payload)
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username='techie')
        self.assertEqual(get_account_type(user), 'technician')
        self.assertTrue(is_technician(user))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_invalid_account_type_is_rejected(self):
        payload = {
            'username': 'bad-role',
            'email': 'bad@example.com',
            'account_type': 'admin',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }

        response = self.client.post(reverse('signup'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select a valid choice')
        self.assertFalse(get_user_model().objects.filter(username='bad-role').exists())

    def test_login_and_logout_work(self):
        user = get_user_model().objects.create_user(username='carol', password='StrongPass123!')

        login_response = self.client.post(reverse('login'), {'username': 'carol', 'password': 'StrongPass123!'})
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

        logout_response = self.client.post(reverse('logout'))
        self.assertEqual(logout_response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sessions_are_scoped_to_the_authenticated_user(self):
        alice = get_user_model().objects.create_user(username='alice', password='StrongPass123!')
        bob = get_user_model().objects.create_user(username='bob', password='StrongPass123!')

        DiagnosticSession.objects.create(session_id='alice-session-1', user=alice, status='active')
        DiagnosticSession.objects.create(session_id='bob-session-1', user=bob, status='active')

        alice_sessions = DiagnosticSession.objects.filter(user=alice)
        bob_sessions = DiagnosticSession.objects.filter(user=bob)

        self.assertEqual(list(alice_sessions.values_list('session_id', flat=True)), ['alice-session-1'])
        self.assertEqual(list(bob_sessions.values_list('session_id', flat=True)), ['bob-session-1'])

    def test_technician_history_is_server_side_protected(self):
        normal = get_user_model().objects.create_user(username='normal', password='StrongPass123!')
        technician = get_user_model().objects.create_user(username='tech-history', password='StrongPass123!')
        UserProfile.objects.create(user=technician, account_type='technician')
        administrator = get_user_model().objects.create_superuser(
            username='administrator', password='StrongPass123!', email='admin@example.com'
        )

        self.client.force_login(normal)
        self.assertEqual(self.client.get(reverse('technician-history')).status_code, 403)

        self.client.force_login(technician)
        response = self.client.get(reverse('technician-history'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['role'], 'Technician')

        self.client.force_login(administrator)
        self.assertEqual(self.client.get(reverse('technician-history')).status_code, 200)

    def test_normal_user_and_technician_receive_different_guidance_for_same_diagnosis(self):
        normal = get_user_model().objects.create_user(username='normal-guide', password='StrongPass123!')
        technician = get_user_model().objects.create_user(username='tech-guide', password='StrongPass123!')
        UserProfile.objects.create(user=technician, account_type='technician')

        rule = DiagnosticSession.objects.create(session_id='guide-session-1', user=normal, status='active')
        del rule

        rule = get_user_model().objects.none()
        del rule

        result = {
            'node_id': 'RAM-002',
            'type': 'solution',
            'diagnosis': 'RAM Not Detected',
            'reasoning': 'The system is reporting a memory detection issue.',
            'recommendation': 'Re-seat the RAM and check slot configuration.',
            'user_explanation': 'Your computer may not be detecting its memory. Turn it off and unplug it before checking the memory sticks.',
            'technician_explanation': 'Possible DIMM detection fault. Reseat the module and verify memory detection in BIOS.',
            'user_recommendation': 'Turn off the computer, unplug it, and reseat the RAM if you are comfortable doing so. If not, contact a technician.',
            'technician_recommendation': 'Verify DIMM seating, validate slot order, and check BIOS memory detection.',
            'safety_warning': 'Always power down and unplug the PC before opening the case.',
        }

        normal_result = present_node(result, normal)
        technician_result = present_node(result, technician)

        self.assertEqual(normal_result['node_id'], technician_result['node_id'])
        self.assertIn('memory', normal_result['explanation'].lower())
        self.assertIn('DIMM', technician_result['explanation'])
        self.assertIn('technician', normal_result['procedure'].lower())
        self.assertIn('BIOS', technician_result['procedure'])

    def test_missing_normal_user_guidance_falls_back_safely(self):
        normal = get_user_model().objects.create_user(username='normal-fallback', password='StrongPass123!')

        result = {
            'node_id': 'CPU-001',
            'type': 'solution',
            'diagnosis': 'CPU Overheating',
            'reasoning': 'The hardware is overheating under load.',
            'recommendation': 'Inspect cooling hardware and clean dust.',
            'user_explanation': '',
            'technician_explanation': 'Thermal conditions exceed safe limits.',
            'user_recommendation': '',
            'technician_recommendation': 'Inspect the cooler assembly and airflow.',
            'safety_warning': 'Do not keep the system running if it is overheating.',
        }

        presented = present_node(result, normal)
        self.assertIn('safely', presented['explanation'].lower())
        self.assertIn('technician', presented['procedure'].lower())
        self.assertEqual(presented['diagnosis'], 'CPU Overheating')

    def test_normal_user_uses_separate_diagnostic_engine(self):
        normal = get_user_model().objects.create_user(username='normal-engine', password='StrongPass123!')
        technician = get_user_model().objects.create_user(username='tech-engine', password='StrongPass123!')
        UserProfile.objects.create(user=technician, account_type='technician')

        from diagnostics.services.user_inference_engine import UserInferenceEngine

        normal_engine = UserInferenceEngine()
        tech_engine = InferenceEngine()

        start_user = normal_engine.start()
        start_tech = tech_engine.get_node('CPU-Q1')

        self.assertEqual(start_user['audience'], 'user')
        self.assertEqual(start_tech['category'], 'CPU')
        self.assertNotEqual(start_user['case_id'], start_tech['node_id'])

        flow = normal_engine.process_step(start_user['case_id'], 0)
        self.assertIn('case_id', flow[0])
        self.assertEqual(flow[0]['audience'], 'user')


class DiagnosticWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_kb', '--flush')

    def test_cpu_branch_requires_additional_evidence_before_solution(self):
        engine = InferenceEngine()
        next_node, next_node_id = engine.process_step('CPU-Q1', 0)

        self.assertIn('CPU-Q2', next_node_id)
        self.assertEqual(next_node['type'], 'question')
        self.assertNotIn(next_node['node_id'], ['CPU-001', 'solution'])
        self.assertIn('CPU-001', next_node['options'][0]['next'])

    def test_kb_has_expanded_multistage_coverage(self):
        engine = InferenceEngine()
        root = engine.get_node('CPU-Q1')
        self.assertTrue(root['options'])
        self.assertTrue(any(str(opt.get('next')).startswith('CPU-Q2::') for opt in root['options']))

    def test_roles_share_the_same_diagnostic_node_and_path(self):
        normal = get_user_model().objects.create_user(username='normal-flow', password='StrongPass123!')
        technician = get_user_model().objects.create_user(username='tech-flow', password='StrongPass123!')
        UserProfile.objects.create(user=technician, account_type='technician')
        engine = InferenceEngine()

        normal_node, normal_id = engine.process_step('CPU-Q1', 0)
        technician_node, technician_id = engine.process_step('CPU-Q1', 0)

        self.assertEqual(normal_id, technician_id)
        self.assertEqual(normal_node['node_id'], technician_node['node_id'])

        normal_result = present_node(engine.get_node('CPU-001'), normal)
        technician_result = present_node(engine.get_node('CPU-001'), technician)
        self.assertEqual(normal_result['node_id'], technician_result['node_id'])
        self.assertEqual(normal_result['audience'], 'user')
        self.assertEqual(technician_result['audience'], 'technician')
        self.assertNotIn('technical_reasoning', normal_result)
        self.assertNotIn('technician_explanation', normal_result)
        self.assertIn('technical_reasoning', technician_result)
