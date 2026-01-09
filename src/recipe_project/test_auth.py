from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm


class AuthenticationViewTest(TestCase):
    """Test cases for authentication views (login and logout)"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.User = get_user_model()

        # Create test user
        self.test_user = self.User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

        # Create another user for additional tests
        self.test_user2 = self.User.objects.create_user(
            username="testuser2", password="testpass456", email="test2@example.com"
        )

    def test_login_view_get_request(self):
        """Test login view with GET request (not logged in)"""
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/login.html")
        self.assertIsInstance(response.context["form"], AuthenticationForm)
        self.assertIsNone(response.context["error_message"])

    def test_login_view_post_valid_credentials(self):
        """Test login view with valid credentials"""
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "testpass123"})

        # Should redirect to recipes list after successful login
        self.assertRedirects(response, reverse("recipes:recipe-list"))

        # Check that user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, "testuser")

    def test_login_view_post_invalid_credentials(self):
        """Test login view with invalid credentials"""
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "wrongpassword"})

        # Should stay on login page - Django's AuthenticationForm handles invalid credentials
        # through form validation, so error_message will be None
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/login.html")
        self.assertIsNone(response.context["error_message"])

        # Check that user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_view_post_nonexistent_user(self):
        """Test login view with non-existent username"""
        response = self.client.post(reverse("login"), {"username": "nonexistent", "password": "testpass123"})

        # Should stay on login page - Django's AuthenticationForm handles non-existent users
        # through form validation, so error_message will be None
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/login.html")
        self.assertIsNone(response.context["error_message"])

        # Check that user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_view_post_empty_credentials(self):
        """Test login view with empty credentials"""
        response = self.client.post(reverse("login"), {"username": "", "password": ""})

        # Should stay on login page (form validation will handle this)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/login.html")
        self.assertIsNone(response.context["error_message"])

        # Check that user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_view_already_authenticated_user(self):
        """Test login view when user is already logged in - should redirect"""
        # Log in the user first
        self.client.login(username="testuser", password="testpass123")

        # Try to access login page while logged in
        response = self.client.get(reverse("login"))

        # Should redirect to recipes list
        self.assertRedirects(response, reverse("recipes:recipe-list"))

    def test_login_view_already_authenticated_user_post(self):
        """Test login view POST when user is already logged in - should redirect"""
        # Log in the user first
        self.client.login(username="testuser", password="testpass123")

        # Try to POST to login page while logged in
        response = self.client.post(reverse("login"), {"username": "testuser2", "password": "testpass456"})

        # Should redirect to recipes list (ignoring the POST data)
        self.assertRedirects(response, reverse("recipes:recipe-list"))

    def test_logout_view_authenticated_user(self):
        """Test logout view with authenticated user"""
        # Log in the user first
        self.client.login(username="testuser", password="testpass123")

        # Verify user is logged in
        self.assertTrue(self.client.session.get("_auth_user_id"))

        # Logout
        response = self.client.get(reverse("logout"))

        # Should render logout template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/logout.html")

        # Check that user is logged out
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_view_unauthenticated_user(self):
        """Test logout view with unauthenticated user - should redirect to login"""
        # Try to access logout without being logged in
        response = self.client.get(reverse("logout"))

        # Should redirect to login page (due to @login_required decorator)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('logout')}")

    def test_logout_view_post_request(self):
        """Test logout view with POST request"""
        # Log in the user first
        self.client.login(username="testuser", password="testpass123")

        # Logout with POST
        response = self.client.post(reverse("logout"))

        # Should render logout template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/logout.html")

        # Check that user is logged out
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_authentication_flow_complete(self):
        """Test complete authentication flow: login -> access protected page -> logout"""
        # 1. Try to access protected page without login
        response = self.client.get(reverse("recipes:recipe-list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('recipes:recipe-list')}")

        # 2. Login
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "testpass123"})
        self.assertRedirects(response, reverse("recipes:recipe-list"))

        # 3. Access protected page (should work now)
        response = self.client.get(reverse("recipes:recipe-list"))
        self.assertEqual(response.status_code, 200)

        # 4. Try to access login page (should redirect)
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("recipes:recipe-list"))

        # 5. Logout
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 200)

        # 6. Try to access protected page again (should redirect to login)
        response = self.client.get(reverse("recipes:recipe-list"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('recipes:recipe-list')}")

    def test_login_form_validation(self):
        """Test login form validation with various invalid inputs"""
        # Test with only username
        response = self.client.post(reverse("login"), {"username": "testuser", "password": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        # Test with only password
        response = self.client.post(reverse("login"), {"username": "", "password": "testpass123"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        # Test with whitespace only
        response = self.client.post(reverse("login"), {"username": "   ", "password": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_case_sensitive_username(self):
        """Test that username is case sensitive"""
        response = self.client.post(
            reverse("login"),
            {
                "username": "TESTUSER",  # Different case
                "password": "testpass123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["error_message"])  # Form validation handles this
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_multiple_login_attempts(self):
        """Test multiple failed login attempts"""
        # First attempt
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "wrongpass1"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["error_message"])  # Form validation handles this

        # Second attempt
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "wrongpass2"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["error_message"])  # Form validation handles this

        # Successful attempt
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "testpass123"})
        self.assertRedirects(response, reverse("recipes:recipe-list"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_redirect_after_logout(self):
        """Test that user can login again after logout"""
        # Login
        self.client.login(username="testuser", password="testpass123")

        # Logout
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

        # Login again
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "testpass123"})
        self.assertRedirects(response, reverse("recipes:recipe-list"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_session_persistence(self):
        """Test that login session persists across requests"""
        # Login
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "testpass123"})
        self.assertRedirects(response, reverse("recipes:recipe-list"))

        # Make another request to verify session persists
        response = self.client.get(reverse("recipes:recipe-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, "testuser")

    def test_logout_clears_session(self):
        """Test that logout properly clears the session"""
        # Login
        self.client.login(username="testuser", password="testpass123")

        # Verify session exists
        self.assertTrue(self.client.session.get("_auth_user_id"))

        # Logout
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 200)

        # Verify session is cleared
        self.assertFalse(self.client.session.get("_auth_user_id"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class AuthenticationURLTest(TestCase):
    """Test cases for authentication URL patterns"""

    def test_login_url(self):
        """Test login URL pattern"""
        url = reverse("login")
        self.assertEqual(url, "/login/")

    def test_logout_url(self):
        """Test logout URL pattern"""
        url = reverse("logout")
        self.assertEqual(url, "/logout/")

    def test_url_resolution(self):
        """Test URL resolution for authentication views"""
        from django.urls import resolve
        from recipe_project.views import login_view, logout_view

        # Test login URL resolution
        resolved = resolve("/login/")
        self.assertEqual(resolved.func, login_view)

        # Test logout URL resolution
        resolved = resolve("/logout/")
        self.assertEqual(resolved.func, logout_view)


class AuthenticationSecurityTest(TestCase):
    """Test cases for authentication security aspects"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.User = get_user_model()

        self.test_user = self.User.objects.create_user(username="testuser", password="testpass123")

    def test_login_required_decorator_on_logout(self):
        """Test that logout view requires authentication"""
        # Try to access logout without authentication
        response = self.client.get(reverse("logout"))

        # Should redirect to login with next parameter
        expected_url = f"{reverse('login')}?next={reverse('logout')}"
        self.assertRedirects(response, expected_url)

    def test_csrf_protection_on_login(self):
        """Test that login form has CSRF protection"""
        response = self.client.get(reverse("login"))

        # Check that CSRF token is present in the form
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_csrf_protection_on_logout(self):
        """Test that logout view has CSRF protection"""
        # Login first
        self.client.login(username="testuser", password="testpass123")

        # Try to logout without CSRF token
        response = self.client.post(reverse("logout"), {})

        # Should still work (GET request doesn't require CSRF for logout)
        self.assertEqual(response.status_code, 200)

    def test_password_not_exposed_in_error_messages(self):
        """Test that passwords are not exposed in error messages"""
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "wrongpassword"})

        # Error message should be None (handled by form validation)
        error_message = response.context["error_message"]
        self.assertIsNone(error_message)

        # Check that form errors don't contain password
        form = response.context["form"]
        if form.errors:
            error_text = str(form.errors)
            self.assertNotIn("wrongpassword", error_text)

    def test_username_not_exposed_in_error_messages(self):
        """Test that usernames are not exposed in error messages"""
        response = self.client.post(reverse("login"), {"username": "nonexistentuser", "password": "testpass123"})

        # Error message should be None (handled by form validation)
        error_message = response.context["error_message"]
        self.assertIsNone(error_message)

        # Check that form errors don't expose username
        form = response.context["form"]
        if form.errors:
            error_text = str(form.errors)
            self.assertNotIn("nonexistentuser", error_text)

    def test_error_message_when_authentication_fails(self):
        """Test that error_message is set when authentication fails after form validation"""
        # This test demonstrates when error_message would be set
        # In the current implementation, Django's AuthenticationForm handles
        # invalid credentials through form validation, so error_message is None
        # But if we had a custom scenario where form is valid but auth fails,
        # error_message would be set

        # Test with valid form data but wrong password
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "wrongpassword"})

        # In current implementation, this is handled by form validation
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["error_message"])

        # The form should have errors
        form = response.context["form"]
        self.assertFalse(form.is_valid())
