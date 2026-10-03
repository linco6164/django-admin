from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render

from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.http import require_POST

from .node_api import node_request, NodeAPIError


@staff_member_required
def node_me(request):
    try:
        user = node_request(
            request,
            "GET",
            "/auth/me",
        )

        return JsonResponse({
            "success": True,
            "user": user,
        })

    except NodeAPIError as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=401,
        )

def dashboard(request):
    try:
        response = node_request(
            request,
            "GET",
            "/admin/stats",
        )

        stats = response.get("data", {})

        api_error = None

    except NodeAPIError as error:
        stats = {}
        api_error = str(error)

    context = admin.site.each_context(request)

    context.update({
        "title": "Dashboard",
        "stats": stats,
        "api_error": api_error,
    })

    return render(
        request,
        "admin/dashboard.html",
        context,
    )

def marketplace_users(request):
    search = request.GET.get("search", "").strip()

    try:
        page = int(request.GET.get("page", 1))
    except ValueError:
        page = 1

    if page < 1:
        page = 1

    try:
        response = node_request(
            request,
            "GET",
            "/admin/users",
            params={
                "page": page,
                "limit": 20,
                "search": search,
            },
        )

        users = response.get("data", [])

        for user in users:
            user['id'] = str(
                user.get('_id') or user.get('id') or ''
            )

        total = response.get("total", 0)
        current_page = response.get("page", page)
        pages = response.get("pages", 1)

    except NodeAPIError as error:
        users = []
        total = 0
        current_page = page
        pages = 1

        context = admin.site.each_context(request)

        context.update({
            "title": "Marketplace users",
            "users": users,
            "total": total,
            "page": current_page,
            "pages": pages,
            "search": search,
            "api_error": str(error),
        })

        return render(
            request,
            "admin/marketplace_users.html",
            context,
        )

    context = admin.site.each_context(request)

    context.update({
        "title": "Marketplace users",
        "users": users,
        "total": total,
        "page": current_page,
        "pages": pages,
        "search": search,
    })

    return render(
        request,
        "admin/marketplace_users.html",
        context,
    )

def marketplace_user_detail(request, user_id):
    allowed_tabs = {
        "overview",
        "profile",
        "listings",
        "security",
    }

    current_tab = request.GET.get(
        "tab",
        "overview",
    )

    if current_tab not in allowed_tabs:
        current_tab = "overview"

    try:
        # =====================================================
        # USER
        # =====================================================

        response = node_request(
            request,
            "GET",
            f"/admin/users/{user_id}",
        )

        user = response.get("data")

        if not user:
            raise NodeAPIError(
                "Utilizatorul nu a fost găsit."
            )

        user["id"] = str(
            user.get("_id")
            or user.get("id")
            or user_id
        )

        # =====================================================
        # LISTINGS
        # =====================================================

        listings = []
        listings_total = 0
        listings_pages = 1
        listings_page = 1

        listings_stats = {
            "total": 0,
            "active": 0,
            "sold": 0,
        }

        listing_status = request.GET.get(
            "status",
            "",
        ).strip()

        if current_tab == "listings":
            try:
                listings_page = int(
                    request.GET.get(
                        "page",
                        1,
                    )
                )
            except ValueError:
                listings_page = 1

            if listings_page < 1:
                listings_page = 1

            params = {
                "seller": user_id,
                "page": listings_page,
                "limit": 20,
            }

            if listing_status:
                params["status"] = listing_status

            listings_response = node_request(
                request,
                "GET",
                "/admin/listings",
                params=params,
            )

            listings = listings_response.get(
                "data",
                [],
            )

            listings_total = listings_response.get(
                "total",
                0,
            )

            listings_pages = listings_response.get(
                "pages",
                1,
            )

            # Total toate
            all_response = node_request(
                request,
                "GET",
                "/admin/listings",
                params={
                    "seller": user_id,
                    "page": 1,
                    "limit": 1,
                },
            )

            # Total active
            active_response = node_request(
                request,
                "GET",
                "/admin/listings",
                params={
                    "seller": user_id,
                    "status": "active",
                    "page": 1,
                    "limit": 1,
                },
            )

            # Total sold
            sold_response = node_request(
                request,
                "GET",
                "/admin/listings",
                params={
                    "seller": user_id,
                    "status": "sold",
                    "page": 1,
                    "limit": 1,
                },
            )

            listings_stats = {
                "total": all_response.get(
                    "total",
                    0,
                ),
                "active": active_response.get(
                    "total",
                    0,
                ),
                "sold": sold_response.get(
                    "total",
                    0,
                ),
            }

        # =====================================================
        # CONTEXT
        # =====================================================

        context = admin.site.each_context(
            request
        )

        context.update({
            "title": (
                f"User: "
                f"{user.get('username', '')}"
            ),

            "marketplace_user": user,

            "current_tab": current_tab,

            "listings": listings,
            "listings_total": listings_total,
            "listings_page": listings_page,
            "listings_pages": listings_pages,
            "listing_status": listing_status,
            "listings_stats": listings_stats,
        })

        return render(
            request,
            "admin/marketplace_user_detail.html",
            context,
        )

    except NodeAPIError as error:
        context = admin.site.each_context(
            request
        )

        context.update({
            "title": "User details",
            "marketplace_user": None,
            "api_error": str(error),
            "current_tab": current_tab,
        })

        return render(
            request,
            "admin/marketplace_user_detail.html",
            context,
        )
        
# ============================================================
# NOTIFICATIONS
# ============================================================

def marketplace_notifications(request):
    if request.method == "POST":
        title = request.POST.get(
            "title",
            "",
        ).strip()

        body = request.POST.get(
            "body",
            "",
        ).strip()

        if not title or not body:
            messages.error(
                request,
                "Titlul și mesajul sunt obligatorii.",
            )

            return redirect(
                "marketplace_notifications"
            )

        try:
            node_request(
                request,
                "POST",
                "/admin/broadcast",
                json={
                    "title": title,
                    "body": body,
                },
            )

            messages.success(
                request,
                "Notificarea a fost trimisă.",
            )

            return redirect(
                "marketplace_notifications"
            )

        except NodeAPIError as error:
            messages.error(
                request,
                str(error),
            )

    context = admin.site.each_context(
        request
    )

    context.update({
        "title": "Notifications",
    })

    return render(
        request,
        "admin/marketplace_notifications.html",
        context,
    )


# ============================================================
# WITHDRAWALS
# ============================================================

def marketplace_withdrawals(request):
    status = request.GET.get(
        "status",
        "pending",
    ).strip()

    allowed_statuses = {
        "pending",
        "completed",
        "rejected",
        "failed",
    }

    if status not in allowed_statuses:
        status = "pending"

    try:
        page = int(
            request.GET.get(
                "page",
                1,
            )
        )
    except ValueError:
        page = 1

    if page < 1:
        page = 1

    try:
        # =====================================================
        # CURRENT LIST
        # =====================================================

        response = node_request(
            request,
            "GET",
            "/admin/withdrawals",
            params={
                "status": status,
                "page": page,
                "limit": 20,
            },
        )

        withdrawals = response.get(
            "data",
            [],
        )

        for withdrawal in withdrawals:
            withdrawal["id"] = str(
                withdrawal.get("_id")
                or withdrawal.get("id")
                or ""
            )

        total = response.get(
            "total",
            0,
        )

        pages = response.get(
            "pages",
            1,
        )

        # =====================================================
        # COUNTERS
        # =====================================================

        withdrawal_counts = {}

        for item_status in (
            "pending",
            "completed",
            "rejected",
            "failed",
        ):
            count_response = node_request(
                request,
                "GET",
                "/admin/withdrawals",
                params={
                    "status": item_status,
                    "page": 1,
                    "limit": 1,
                },
            )

            withdrawal_counts[
                item_status
            ] = count_response.get(
                "total",
                0,
            )

        api_error = None

    except NodeAPIError as error:
        withdrawals = []
        total = 0
        pages = 1

        withdrawal_counts = {
            "pending": 0,
            "completed": 0,
            "rejected": 0,
            "failed": 0,
        }

        api_error = str(error)

    context = admin.site.each_context(
        request
    )

    context.update({
        "title": "Withdrawals",

        "withdrawals": withdrawals,

        "status": status,

        "page": page,
        "pages": pages,

        "total": total,

        "withdrawal_counts":
            withdrawal_counts,

        "api_error": api_error,
    })

    return render(
        request,
        "admin/marketplace_withdrawals.html",
        context,
    )


@require_POST
def marketplace_withdrawal_action(
    request,
    withdrawal_id,
):
    action = request.POST.get(
        "action",
        "",
    ).strip()

    if action not in {
        "approve",
        "reject",
    }:
        messages.error(
            request,
            "Acțiune invalidă.",
        )

        return redirect(
            "marketplace_withdrawals"
        )

    try:
        node_request(
            request,
            "POST",
            (
                f"/admin/withdrawals/"
                f"{withdrawal_id}/"
                f"{action}"
            ),
            json={},
        )

        if action == "approve":
            messages.success(
                request,
                "Retragerea a fost aprobată.",
            )
        else:
            messages.success(
                request,
                "Retragerea a fost respinsă "
                "și suma a fost returnată în sold.",
            )

    except NodeAPIError as error:
        messages.error(
            request,
            str(error),
        )

    return redirect(
        "marketplace_withdrawals"
    )


# ============================================================
# SUPPORT LIST
# ============================================================

def marketplace_support(request):
    active_filter = request.GET.get(
        "filter",
        "unassigned",
    ).strip()

    department = request.GET.get(
        "department",
        "",
    ).strip()

    priority = request.GET.get(
        "priority",
        "",
    ).strip()

    allowed_filters = {
        "all",
        "my",
        "unassigned",
        "open",
        "pending",
        "closed",
        "urgent",
    }

    if active_filter not in allowed_filters:
        active_filter = "unassigned"

    params = {}

    # =====================================================
    # MAIN FILTER
    # =====================================================

    if active_filter in {
        "open",
        "pending",
        "closed",
    }:
        params["status"] = active_filter

    elif active_filter == "my":
        params["assignedTo"] = "me"

    elif active_filter == "unassigned":
        params["assignedTo"] = "unassigned"

    elif active_filter == "urgent":
        params["priority"] = "urgent"

    # =====================================================
    # EXTRA FILTERS
    # =====================================================

    if department:
        params["department"] = department

    if (
        priority
        and active_filter != "urgent"
    ):
        params["priority"] = priority

    try:
        # =================================================
        # STAFF INFO
        # =================================================

        staff_response = node_request(
            request,
            "GET",
            "/support/staff/info",
        )

        staff = {
            "id": staff_response.get("id"),
            "role": staff_response.get("role"),
            "department": staff_response.get(
                "department"
            ),
            "departments": staff_response.get(
                "departments",
                [],
            ),
        }

        # =================================================
        # STATS
        # =================================================

        stats_response = node_request(
            request,
            "GET",
            "/support/staff/stats",
        )

        stats = stats_response.get(
            "stats",
            {},
        )

        # =================================================
        # TICKETS
        # =================================================

        response = node_request(
            request,
            "GET",
            "/support/staff/tickets",
            params=params,
        )

        result = response.get(
            "tickets",
            {},
        )

        tickets = result.get(
            "tickets",
            [],
        )

        total = result.get(
            "total",
            0,
        )

        for ticket in tickets:
            ticket["id"] = str(
                ticket.get("_id")
                or ticket.get("id")
                or ""
            )

            user = ticket.get(
                "user"
            ) or {}

            ticket["user_id"] = str(
                user.get("_id")
                or user.get("id")
                or ""
            )

            messages = ticket.get(
                "messages"
            ) or []

            if messages:
                last_message = (
                    messages[-1]
                    or {}
                )

                ticket["preview"] = (
                    last_message.get(
                        "message",
                        ""
                    )
                )
            else:
                ticket["preview"] = (
                    "No messages"
                )

        api_error = None

    except NodeAPIError as error:
        tickets = []
        total = 0

        staff = {
            "departments": [],
        }

        stats = {}

        api_error = str(error)

    context = admin.site.each_context(
        request
    )

    context.update({
        "title": "Support",

        "tickets": tickets,
        "total": total,

        "staff": staff,
        "stats": stats,

        "active_filter":
            active_filter,

        "filter_department":
            department,

        "filter_priority":
            priority,

        "api_error":
            api_error,
    })

    return render(
        request,
        "admin/marketplace_support.html",
        context,
    )


# ============================================================
# SUPPORT DETAIL
# ============================================================

def marketplace_support_detail(
    request,
    ticket_id,
):
    try:
        # =====================================================
        # TICKET
        # =====================================================

        response = node_request(
            request,
            "GET",
            f"/support/staff/tickets/{ticket_id}",
        )

        ticket = response.get(
            "ticket"
        )

        if not ticket:
            raise NodeAPIError(
                "Ticketul nu a fost găsit."
            )

        ticket["id"] = str(
            ticket.get("_id")
            or ticket.get("id")
            or ticket_id
        )

        # =====================================================
        # USER
        # =====================================================

        ticket_user = (
            ticket.get("user")
            or {}
        )

        ticket["user_id"] = str(
            ticket_user.get("_id")
            or ticket_user.get("id")
            or ""
        )

        # =====================================================
        # ASSIGNED TO
        # =====================================================

        assigned_to = (
            ticket.get("assignedTo")
            or {}
        )

        ticket["assigned_to_id"] = str(
            assigned_to.get("_id")
            or assigned_to.get("id")
            or ""
        )

        # =====================================================
        # STAFF INFO
        # =====================================================

        staff_response = node_request(
            request,
            "GET",
            "/support/staff/info",
        )

        staff = {
            "id": str(
                staff_response.get("id")
                or ""
            ),
            "role": staff_response.get(
                "role"
            ),
            "department":
                staff_response.get(
                    "department"
                ),
        }

        ticket["is_assigned_to_me"] = (
            bool(
                ticket[
                    "assigned_to_id"
                ]
            )
            and
            ticket[
                "assigned_to_id"
            ] == staff["id"]
        )

        # =====================================================
        # CONTEXT
        # =====================================================

        context = admin.site.each_context(
            request
        )

        context.update({
            "title": ticket.get(
                "subject",
                "Support ticket",
            ),
            "ticket": ticket,
            "staff": staff,
        })

        return render(
            request,
            "admin/marketplace_support_detail.html",
            context,
        )

    except NodeAPIError as error:
        context = admin.site.each_context(
            request
        )

        context.update({
            "title": "Support ticket",
            "ticket": None,
            "api_error": str(error),
        })

        return render(
            request,
            "admin/marketplace_support_detail.html",
            context,
        )


# ============================================================
# SUPPORT ACTIONS
# ============================================================

@require_POST
def marketplace_support_action(
    request,
    ticket_id,
):
    action = request.POST.get(
        "action",
        "",
    ).strip()

    try:
        # =====================================================
        # ASSIGN
        # =====================================================

        if action == "assign":
            node_request(
                request,
                "POST",
                f"/support/staff/tickets/{ticket_id}/assign",
                json={},
            )

            messages.success(
                request,
                "Ticketul a fost preluat.",
            )

        # =====================================================
        # UNASSIGN
        # =====================================================

        elif action == "unassign":
            node_request(
                request,
                "POST",
                f"/support/staff/tickets/{ticket_id}/unassign",
                json={},
            )

            messages.success(
                request,
                "Ticketul a fost eliberat.",
            )

        # =====================================================
        # STATUS
        # =====================================================

        elif action == "status":
            status = request.POST.get(
                "status",
                "",
            ).strip()

            allowed_statuses = {
                "open",
                "pending",
                "closed",
            }

            if status not in allowed_statuses:
                messages.error(
                    request,
                    "Status invalid.",
                )

                return redirect(
                    "marketplace_support_detail",
                    ticket_id=ticket_id,
                )

            node_request(
                request,
                "PATCH",
                f"/support/staff/tickets/{ticket_id}/status",
                json={
                    "status": status,
                },
            )

            messages.success(
                request,
                "Statusul a fost actualizat.",
            )

        # =====================================================
        # PRIORITY
        # =====================================================

        elif action == "priority":
            priority = request.POST.get(
                "priority",
                "",
            ).strip()

            allowed_priorities = {
                "low",
                "normal",
                "high",
                "urgent",
            }

            if priority not in allowed_priorities:
                messages.error(
                    request,
                    "Prioritate invalidă.",
                )

                return redirect(
                    "marketplace_support_detail",
                    ticket_id=ticket_id,
                )

            node_request(
                request,
                "PATCH",
                f"/support/staff/tickets/{ticket_id}/priority",
                json={
                    "priority": priority,
                },
            )

            messages.success(
                request,
                "Prioritatea a fost actualizată.",
            )

        # =====================================================
        # MESSAGE
        # =====================================================

        elif action == "message":
            message = request.POST.get(
                "message",
                "",
            ).strip()

            if not message:
                messages.error(
                    request,
                    "Mesajul nu poate fi gol.",
                )

                return redirect(
                    "marketplace_support_detail",
                    ticket_id=ticket_id,
                )

            if len(message) > 5000:
                messages.error(
                    request,
                    "Mesajul poate avea maximum 5000 de caractere.",
                )

                return redirect(
                    "marketplace_support_detail",
                    ticket_id=ticket_id,
                )

            node_request(
                request,
                "POST",
                f"/support/staff/tickets/{ticket_id}/messages",
                json={
                    "message": message,
                },
            )

            messages.success(
                request,
                "Mesajul a fost trimis.",
            )

        else:
            messages.error(
                request,
                "Acțiune necunoscută.",
            )

    except NodeAPIError as error:
        messages.error(
            request,
            str(error),
        )

    return redirect(
        "marketplace_support_detail",
        ticket_id=ticket_id,
    )

@require_POST
def marketplace_toggle_ban(request, user_id):
    action = request.POST.get("action", "").strip()

    if action not in ("ban", "unban"):
        messages.error(
            request,
            "Acțiune invalidă."
        )
        return redirect("marketplace_users")

    # Protecție: administratorul autentificat
    # nu își poate bloca propriul cont.
    node_user = request.session.get("node_user", {})
    current_admin_id = str(
        node_user.get("id") or ""
    )

    if (
        action == "ban"
        and current_admin_id == str(user_id)
    ):
        messages.error(
            request,
            "Nu îți poți bloca propriul cont."
        )
        return redirect("marketplace_users")

    reason = request.POST.get(
        "reason",
        ""
    ).strip()

    custom_reason = request.POST.get(
        "custom_reason",
        ""
    ).strip()

    if action == "ban":

        if reason == "Alt motiv":
            reason = custom_reason

        if not reason:
            messages.error(
                request,
                "Trebuie să selectezi un motiv pentru blocare."
            )
            return redirect("marketplace_users")

        if len(reason) < 3:
            messages.error(
                request,
                "Motivul este prea scurt."
            )
            return redirect("marketplace_users")

        if len(reason) > 500:
            messages.error(
                request,
                "Motivul poate avea maximum 500 de caractere."
            )
            return redirect("marketplace_users")

    try:
        # Verificăm starea actuală.
        user_response = node_request(
            request,
            "GET",
            f"/admin/users/{user_id}",
        )

        user = user_response.get(
            "data",
            {}
        )

        is_banned = bool(
            user.get("banned")
        )

        # Endpoint-ul Node este toggle.
        # Evităm să inversăm greșit starea dacă
        # utilizatorul este deja în starea cerută.
        if action == "ban" and is_banned:
            messages.info(
                request,
                "Contul este deja blocat."
            )
            return redirect(
                "marketplace_users"
            )

        if action == "unban" and not is_banned:
            messages.info(
                request,
                "Contul este deja activ."
            )
            return redirect(
                "marketplace_users"
            )

        node_request(
            request,
            "PATCH",
            f"/admin/users/{user_id}/ban",
            json={
                "reason": (
                    reason
                    if action == "ban"
                    else ""
                )
            },
        )

        if action == "ban":
            messages.success(
                request,
                "Contul a fost blocat."
            )
        else:
            messages.success(
                request,
                "Contul a fost deblocat."
            )

    except NodeAPIError as error:
        messages.error(
            request,
            str(error)
        )

    return redirect(
        "marketplace_users"
    )

@require_POST
def marketplace_user_update(request, user_id):
    action = request.POST.get("action", "").strip()

    try:
        # =====================================================
        # PROFILE
        # =====================================================

        if action == "profile":
            username = request.POST.get(
                "username",
                "",
            ).strip()

            if len(username) < 2:
                messages.error(
                    request,
                    "Username-ul este prea scurt.",
                )

                return redirect(
                    "marketplace_user_detail",
                    user_id=user_id,
                )

            payload = {
                "username": username,
                "fullName": request.POST.get(
                    "fullName",
                    "",
                ).strip(),
                "phone": request.POST.get(
                    "phone",
                    "",
                ).strip(),
                "bio": request.POST.get(
                    "bio",
                    "",
                ).strip(),
                "country": request.POST.get(
                    "country",
                    "",
                ).strip(),
                "city": request.POST.get(
                    "city",
                    "",
                ).strip(),
                "county": request.POST.get(
                    "county",
                    "",
                ).strip(),
                "postalCode": request.POST.get(
                    "postalCode",
                    "",
                ).strip(),
                "instagram": request.POST.get(
                    "instagram",
                    "",
                ).strip(),
                "facebook": request.POST.get(
                    "facebook",
                    "",
                ).strip(),
                "website": request.POST.get(
                    "website",
                    "",
                ).strip(),
            }

            node_request(
                request,
                "PATCH",
                f"/admin/users/{user_id}/profile",
                json=payload,
            )

            messages.success(
                request,
                "Profilul a fost actualizat.",
            )

        # =====================================================
        # EMAIL
        # =====================================================

        elif action == "email":
            email = request.POST.get(
                "email",
                "",
            ).strip().lower()

            try:
                validate_email(email)

            except ValidationError:
                messages.error(
                    request,
                    "Adresa de email nu este validă.",
                )

                return redirect(
                    "marketplace_user_detail",
                    user_id=user_id,
                )

            node_request(
                request,
                "PATCH",
                f"/admin/users/{user_id}/email",
                json={
                    "email": email,
                },
            )

            messages.success(
                request,
                "Emailul a fost actualizat.",
            )

        # =====================================================
        # PASSWORD
        # =====================================================

        elif action == "password":
            new_password = request.POST.get(
                "new_password",
                "",
            )

            confirm_password = request.POST.get(
                "confirm_password",
                "",
            )

            if len(new_password) < 8:
                messages.error(
                    request,
                    "Parola trebuie să aibă cel puțin 8 caractere.",
                )

                return redirect(
                    "marketplace_user_detail",
                    user_id=user_id,
                )

            if new_password != confirm_password:
                messages.error(
                    request,
                    "Parolele nu coincid.",
                )

                return redirect(
                    "marketplace_user_detail",
                    user_id=user_id,
                )

            node_request(
                request,
                "PATCH",
                f"/admin/users/{user_id}/password",
                json={
                    "newPassword": new_password,
                },
            )

            messages.success(
                request,
                "Parola utilizatorului a fost schimbată.",
            )

        # =====================================================
        # GENERATE TEMP PASSWORD
        # =====================================================

        elif action == "generate_password":
            result = node_request(
                request,
                "PATCH",
                f"/admin/users/{user_id}/password",
                json={},
            )

            temporary_password = result.get(
                "temporaryPassword"
            )

            if temporary_password:
                messages.warning(
                    request,
                    "Parolă temporară generată: "
                    f"{temporary_password}"
                )
            else:
                messages.success(
                    request,
                    "Parola temporară a fost generată.",
                )

        # =====================================================
        # DISABLE 2FA
        # =====================================================

        elif action == "disable_2fa":
            node_request(
                request,
                "PATCH",
                f"/admin/users/{user_id}/2fa/disable",
                json={},
            )

            messages.success(
                request,
                "Autentificarea 2FA a fost dezactivată.",
            )

        else:
            messages.error(
                request,
                "Acțiune necunoscută.",
            )

    except NodeAPIError as error:
        messages.error(
            request,
            str(error),
        )

    return redirect(
        "marketplace_user_detail",
        user_id=user_id,
    )