from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from accounts.views import (
    dashboard,
    node_me,
    marketplace_users,
    marketplace_user_detail,
    marketplace_user_update,
    marketplace_toggle_ban,

    marketplace_notifications,
    marketplace_notification_detail,
    marketplace_notification_action,

    marketplace_withdrawals,
    marketplace_withdrawal_action,

    marketplace_support,
    marketplace_support_detail,
    marketplace_support_action,
)


urlpatterns = [
    path(
        "",
        RedirectView.as_view(
            url="/admin/login/",
            permanent=False,
        ),
    ),
    
    # /admin/ -> dashboard-ul NEXORA
    path(
        "admin/",
        RedirectView.as_view(
            pattern_name="nexora_dashboard",
            permanent=False,
        ),
    ),

    path(
        "admin/dashboard/",
        admin.site.admin_view(dashboard),
        name="nexora_dashboard",
    ),

    path(
        "admin/node-me/",
        admin.site.admin_view(node_me),
        name="node_me",
    ),

    path(
        "admin/marketplace-users/",
        admin.site.admin_view(marketplace_users),
        name="marketplace_users",
    ),

    path(
        "admin/marketplace-users/<str:user_id>/",
        admin.site.admin_view(marketplace_user_detail),
        name="marketplace_user_detail",
    ),

    path(
        "admin/marketplace-users/<str:user_id>/ban/",
        admin.site.admin_view(
            marketplace_toggle_ban
        ),
    name="marketplace_toggle_ban",
    ),

    path(
        "admin/marketplace-users/<str:user_id>/update/",
        admin.site.admin_view(
            marketplace_user_update
        ),
        name="marketplace_user_update",
    ),

    # Notifications
    path(
        "admin/notifications/",
        admin.site.admin_view(
            marketplace_notifications
        ),
        name="marketplace_notifications",
    ),
    
    path(
        "admin/notifications/<str:notification_id>/",
        admin.site.admin_view(
            marketplace_notification_detail
        ),
        name="marketplace_notification_detail",
    ),

    path(
        (
            "admin/notifications/"
            "<str:notification_id>/action/"
        ),
        admin.site.admin_view(
            marketplace_notification_action
        ),
        name="marketplace_notification_action",
    ),

    # Withdrawals
    path(
        "admin/withdrawals/",
        admin.site.admin_view(
            marketplace_withdrawals
        ),
        name="marketplace_withdrawals",
    ),

    path(
        "admin/withdrawals/<str:withdrawal_id>/action/",
        admin.site.admin_view(
            marketplace_withdrawal_action
        ),
        name="marketplace_withdrawal_action",
    ),

    # Support
    path(
        "admin/support/",
        admin.site.admin_view(
            marketplace_support
        ),
        name="marketplace_support",
    ),

    path(
        "admin/support/<str:ticket_id>/",
        admin.site.admin_view(
            marketplace_support_detail
        ),
        name="marketplace_support_detail",
    ),

    path(
        "admin/support/<str:ticket_id>/action/",
        admin.site.admin_view(
            marketplace_support_action
        ),
        name="marketplace_support_action",
    ),

        # Trebuie să fie ultimul
        path(
            "admin/",
            admin.site.urls,
        ),
]