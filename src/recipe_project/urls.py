"""
URL configuration for recipe_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.cache import cache_control
from django.views.static import serve
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from recipes.api_views import (
    RecipeListAPIView,
    RecipeDetailAPIView,
    RecipeSearchAPIView,
    RecipeSearchStatsAPIView,
)
from recipe_project.views import login_view, logout_view, about_view


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("recipes.urls", namespace="recipes")),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("about/", about_view, name="about"),
    # JWT auth endpoints for Vue SPA
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Recipe API endpoints
    path("api/recipes/", RecipeListAPIView.as_view(), name="api_recipe_list"),
    path("api/recipes/<int:pk>/", RecipeDetailAPIView.as_view(), name="api_recipe_detail"),
    path("api/recipes/search/", RecipeSearchAPIView.as_view(), name="api_recipe_search"),
    path("api/recipes/search/stats/", RecipeSearchStatsAPIView.as_view(), name="api_recipe_search_stats"),
]

# Serve user-uploaded media files via Django's static.serve view.
# Django's `static()` helper is a no-op when DEBUG=False, so we register the
# pattern explicitly to ensure media is reachable in production too.
# Cache-Control: public, max-age=30d lets browsers and any upstream CDN cache
# images aggressively, so repeat visitors don't hit Django for media.
# Acceptable for a small portfolio app; for higher-traffic deployments,
# move media to cloud storage (django-storages) with a CDN in front.
urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        cache_control(public=True, max_age=60 * 60 * 24 * 30)(serve),
        {"document_root": settings.MEDIA_ROOT},
    ),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    # Add browser reload URLs for development
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
