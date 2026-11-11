from django.urls import path

from apps.accounts.views import EmailTokenObtainPairView, LogoutView, ThrottledTokenRefreshView

urlpatterns = [
    path("login/", EmailTokenObtainPairView.as_view(), name="auth-login"),
    path("refresh/", ThrottledTokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
