"""User management routes for admin dashboard."""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from mcp_anywhere.auth.models import OAuth2Token, User, UserToolPermission
from mcp_anywhere.config import Config
from mcp_anywhere.database import MCPServerTool, get_async_session
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.web.routes import get_current_user, get_template_context

logger = get_logger(__name__)
templates = Jinja2Templates(directory="src/mcp_anywhere/web/templates")


def require_admin_role(func):
    """Require admin role for privileged actions"""

    async def wrapper(request: Request, *args, **kwargs):
        current_user = get_current_user(request)

        if not current_user.is_authenticated:
            return RedirectResponse(url="/auth/login", status_code=302)

        if not current_user.is_admin:
            return templates.TemplateResponse(
                request,
                "403.html",
                get_template_context(
                    request, message="Access denied. Admin role required."
                ),
                status_code=403,
            )

        return await func(request, *args, **kwargs)

    return wrapper


@require_admin_role
async def user_list(request: Request) -> HTMLResponse:

    try:
        async with get_async_session() as db_session:

            stmt = select(User).order_by(User.created_at.desc())
            result = await db_session.execute(stmt)
            users = result.scalars().all()


            user_data = []
            for user in users:
                token_stmt = (
                    select(OAuth2Token)
                    .where(OAuth2Token.user_id == user.id)
                    .where(OAuth2Token.is_revoked == False)  # noqa: E712
                )
                token_result = await db_session.execute(token_stmt)
                active_tokens = len(token_result.scalars().all())

                user_data.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "created_at": user.created_at,
                        "active_tokens": active_tokens,
                    }
                )

        return templates.TemplateResponse(
            request, "users/list.html", get_template_context(request, users=user_data)
        )

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error loading users: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error loading users"),
            status_code=500,
        )


@require_admin_role
async def user_detail(request: Request) -> HTMLResponse:
    """Display user details"""
    user_id = request.path_params["user_id"]

    try:
        async with get_async_session() as db_session:

            stmt = select(User).where(User.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(
                        request, message=f"User with ID '{user_id}' not found"
                    ),
                    status_code=404,
                )

            token_stmt = (
                select(OAuth2Token)
                .where(OAuth2Token.user_id == user_id)
                .order_by(OAuth2Token.created_at.desc())
            )
            token_result = await db_session.execute(token_stmt)
            tokens = token_result.scalars().all()

            # Calculate statistics
            active_tokens = sum(1 for t in tokens if t.is_valid())
            expired_tokens = sum(1 for t in tokens if t.is_expired())
            revoked_tokens = sum(1 for t in tokens if t.is_revoked)

        return templates.TemplateResponse(
            request,
            "users/detail.html",
            get_template_context(
                request,
                user=user,
                tokens=tokens,
                active_tokens=active_tokens,
                expired_tokens=expired_tokens,
                revoked_tokens=revoked_tokens,
            ),
        )

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error loading user details for {user_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error loading user details"),
            status_code=500,
        )


@require_admin_role
async def user_create_get(request: Request) -> HTMLResponse:
    """Display create user form."""
    return templates.TemplateResponse(
        request, "users/create.html", get_template_context(request)
    )


@require_admin_role
async def user_create_post(request: Request) -> HTMLResponse:
    """Handle user creation."""
    form_data = await request.form()
    username = form_data.get("username", "").strip()
    password = form_data.get("password", "")
    confirm_password = form_data.get("confirm_password", "")
    role = form_data.get("role", Config.USER_ROLE)
    email = form_data.get("email", "")

    # Validation
    errors = {}
    if not username:
        errors["username"] = ["Username is required"]
    elif len(username) < 3:
        errors["username"] = ["Username must be at least 3 characters"]

    if not password:
        errors["password"] = ["Password is required"]
    elif len(password) < 8:
        errors["password"] = ["Password must be at least 8 characters"]

    if password != confirm_password:
        errors["confirm_password"] = ["Passwords do not match"]

    if role not in Config.AUTH_ROLES:
        errors["role"] = ["Invalid role selected"]

    if errors:
        return templates.TemplateResponse(
            request,
            "users/create.html",
            get_template_context(
                request, errors=errors, username=username, role=role, error_summary=True
            ),
        )

    try:
        async with get_async_session() as db_session:
            # Create new user
            user = User(username=username, role=role, email=email)
            user.set_password(password)

            db_session.add(user)
            await db_session.commit()

            logger.info(f"User '{username}' created successfully with role: {role}")

        return RedirectResponse(url="/admin/users", status_code=302)

    except IntegrityError:
        return templates.TemplateResponse(
            request,
            "users/create.html",
            get_template_context(
                request,
                username=username,
                role=role,
                errors={"username": ["Username already exists"]},
                error_summary=True,
            ),
        )
    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error creating user: {e}")
        return templates.TemplateResponse(
            request,
            "users/create.html",
            get_template_context(
                request,
                username=username,
                role=role,
                errors={"general": ["Error creating user. Please try again."]},
                error_summary=True,
            ),
        )


@require_admin_role
async def user_delete(request: Request) -> RedirectResponse | HTMLResponse:
    """Delete a user."""
    user_id = request.path_params["user_id"]

    try:
        async with get_async_session() as db_session:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(
                        request, message=f"User with ID '{user_id}' not found"
                    ),
                    status_code=404,
                )

            # Prevent deletion of the initial admin user
            if user.username == "admin":
                return templates.TemplateResponse(
                    request,
                    "400.html",
                    get_template_context(
                        request,
                        message="Cannot delete the default admin account. This account is protected.",
                    ),
                    status_code=400,
                )

            username = user.username

            # Delete user (cascade will handle related records)
            await db_session.delete(user)
            await db_session.commit()

            logger.info(f"User '{username}' deleted successfully")

        return RedirectResponse(url="/admin/users", status_code=302)

    except (RuntimeError, ValueError, ConnectionError, IntegrityError) as e:
        logger.exception(f"Error deleting user {user_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error deleting user"),
            status_code=500,
        )


@require_admin_role
async def user_revoke_token(request: Request) -> RedirectResponse | HTMLResponse:
    """Revoke a user's token."""
    user_id = request.path_params["user_id"]
    token_id = request.path_params["token_id"]

    try:
        async with get_async_session() as db_session:
            # Get token
            stmt = select(OAuth2Token).where(
                OAuth2Token.id == token_id, OAuth2Token.user_id == user_id
            )
            result = await db_session.execute(stmt)
            token = result.scalar_one_or_none()

            if not token:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(request, message="Token not found"),
                    status_code=404,
                )

            # Revoke token
            token.is_revoked = True
            await db_session.commit()

            logger.info(f"Token {token_id} for user {user_id} revoked successfully")

        # Return to user detail page
        return RedirectResponse(url=f"/admin/users/{user_id}", status_code=302)

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error revoking token {token_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error revoking token"),
            status_code=500,
        )


@require_admin_role
async def user_revoke_all_tokens(request: Request) -> RedirectResponse | HTMLResponse:
    """Revoke all tokens for a user."""
    user_id = request.path_params["user_id"]

    try:
        async with get_async_session() as db_session:
            # Verify user exists
            user_stmt = select(User).where(User.id == user_id)
            user_result = await db_session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if not user:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(
                        request, message=f"User with ID '{user_id}' not found"
                    ),
                    status_code=404,
                )

            # Revoke all active tokens
            token_stmt = (
                select(OAuth2Token)
                .where(OAuth2Token.user_id == user_id)
                .where(OAuth2Token.is_revoked == False)  # noqa: E712
            )
            token_result = await db_session.execute(token_stmt)
            tokens = token_result.scalars().all()

            count = 0
            for token in tokens:
                token.is_revoked = True
                count += 1

            await db_session.commit()

            logger.info(f"Revoked {count} tokens for user {user.username}")

        return RedirectResponse(url=f"/admin/users/{user_id}", status_code=302)

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error revoking all tokens for user {user_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error revoking tokens"),
            status_code=500,
        )


@require_admin_role
async def user_change_password_get(request: Request) -> HTMLResponse:
    """Display change password form."""
    user_id = request.path_params["user_id"]

    try:
        async with get_async_session() as db_session:
            stmt = select(User).where(User.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(
                        request, message=f"User with ID '{user_id}' not found"
                    ),
                    status_code=404,
                )

        return templates.TemplateResponse(
            request,
            "users/change_password.html",
            get_template_context(request, user=user),
        )

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error loading change password form for user {user_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error loading form"),
            status_code=500,
        )


@require_admin_role
async def user_change_password_post(request: Request) -> HTMLResponse:
    """Handle password change."""
    user_id = request.path_params["user_id"]
    form_data = await request.form()
    new_password = form_data.get("new_password", "")
    confirm_password = form_data.get("confirm_password", "")

    # Validation
    errors = {}
    if not new_password:
        errors["new_password"] = ["Password is required"]
    elif len(new_password) < 8:
        errors["new_password"] = ["Password must be at least 8 characters"]

    if new_password != confirm_password:
        errors["confirm_password"] = ["Passwords do not match"]

    try:
        async with get_async_session() as db_session:
            stmt = select(User).where(User.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(
                        request, message=f"User with ID '{user_id}' not found"
                    ),
                    status_code=404,
                )

            if errors:
                return templates.TemplateResponse(
                    request,
                    "users/change_password.html",
                    get_template_context(
                        request, user=user, errors=errors, error_summary=True
                    ),
                )

            # Update password
            user.set_password(new_password)
            await db_session.commit()

            logger.info(f"Password changed for user '{user.username}'")

        return RedirectResponse(url=f"/admin/users/{user_id}", status_code=302)

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error changing password for user {user_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error changing password"),
            status_code=500,
        )


async def user_create(request: Request) -> HTMLResponse:
    if request.method == "GET":
        return await user_create_get(request)
    else:
        return await user_create_post(request)


async def user_change_password(request: Request) -> HTMLResponse:
    if request.method == "GET":
        return await user_change_password_get(request)
    else:
        return await user_change_password_post(request)


@require_admin_role
async def user_change_role(request: Request) -> RedirectResponse | HTMLResponse:
    user_id = request.path_params["user_id"]
    form_data = await request.form()
    new_role = form_data.get("role", "")

    # Validation
    if new_role not in Config.AUTH_ROLES:
        return templates.TemplateResponse(
            request,
            "400.html",
            get_template_context(request, message="Invalid role selected."),
            status_code=400,
        )

    try:
        async with get_async_session() as db_session:
            stmt = select(User).where(User.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(
                        request, message=f"User with ID '{user_id}' not found"
                    ),
                    status_code=404,
                )

            # Prevent changing role of the initial admin user
            if user.username == "admin":
                return templates.TemplateResponse(
                    request,
                    "400.html",
                    get_template_context(
                        request,
                        message="Cannot change role of the default admin account. This account is protected.",
                    ),
                    status_code=400,
                )

            old_role = user.role
            user.role = new_role
            await db_session.commit()

            logger.info(
                f"Role changed for user '{user.username}' from {old_role} to {new_role}"
            )

        return RedirectResponse(url=f"/admin/users/{user_id}", status_code=302)

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error changing role for user {user_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error changing user role"),
            status_code=500,
        )


@require_admin_role
async def user_permissions(request: Request) -> HTMLResponse:
    """Display tool permissions for a user."""
    user_id = request.path_params["user_id"]

    try:
        async with get_async_session() as db_session:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await db_session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return templates.TemplateResponse(
                    request,
                    "404.html",
                    get_template_context(
                        request, message=f"User with ID '{user_id}' not found"
                    ),
                    status_code=404,
                )

            # Get all tools with their servers and existing permissions
            tools_stmt = (
                select(MCPServerTool)
                .options(selectinload(MCPServerTool.server))
                .order_by(MCPServerTool.tool_name)
            )
            tools_result = await db_session.execute(tools_stmt)
            all_tools = tools_result.scalars().all()

            # Get existing permissions for this user
            perms_stmt = select(UserToolPermission).where(
                UserToolPermission.user_id == user_id
            )
            perms_result = await db_session.execute(perms_stmt)
            permissions = {p.tool_id: p.permission for p in perms_result.scalars().all()}

            # Attach permission to each tool (default to 'allow')
            tools_with_perms = []
            for tool in all_tools:
                tool.permission = permissions.get(tool.id, "allow")
                tools_with_perms.append(tool)

        return templates.TemplateResponse(
            request,
            "users/permissions.html",
            get_template_context(request, user=user, tools=tools_with_perms),
        )

    except (RuntimeError, ValueError, ConnectionError) as e:
        logger.exception(f"Error loading permissions for user {user_id}: {e}")
        return templates.TemplateResponse(
            request,
            "500.html",
            get_template_context(request, message="Error loading permissions"),
            status_code=500,
        )


@require_admin_role
async def user_toggle_permission(request: Request) -> Response:
    """Toggle tool permission for a user via HTMX."""
    user_id = request.path_params["user_id"]
    tool_id = request.path_params["tool_id"]

    try:
        form_data = await request.form()
        new_permission = form_data.get("permission", "allow")

        # Validate permission value
        if new_permission not in ["allow", "deny"]:
            return Response(content="Invalid permission", status_code=400)

        async with get_async_session() as db_session:
            # Check if permission record exists
            stmt = select(UserToolPermission).where(
                UserToolPermission.user_id == user_id,
                UserToolPermission.tool_id == tool_id,
            )
            result = await db_session.execute(stmt)
            permission = result.scalar_one_or_none()

            if permission:
                # Update existing permission
                permission.permission = new_permission
                permission.updated_at = datetime.utcnow()
            else:
                # Create new permission record
                permission = UserToolPermission(
                    user_id=user_id, tool_id=tool_id, permission=new_permission
                )
                db_session.add(permission)

            await db_session.commit()

            logger.info(
                f"Tool permission updated: user_id={user_id}, tool_id={tool_id}, permission={new_permission}"
            )

        return Response(content="", status_code=200)

    except (RuntimeError, ValueError, ConnectionError, IntegrityError) as e:
        logger.exception(
            f"Error toggling permission for user {user_id}, tool {tool_id}: {e}"
        )
        return Response(content="Error updating permission", status_code=500)


routes = [
    Route("/admin/users", endpoint=user_list, methods=["GET"]),
    Route("/admin/users/create", endpoint=user_create, methods=["GET", "POST"]),
    Route("/admin/users/{user_id}", endpoint=user_detail, methods=["GET"]),
    Route("/admin/users/{user_id}/delete", endpoint=user_delete, methods=["POST"]),
    Route(
        "/admin/users/{user_id}/change-password",
        endpoint=user_change_password,
        methods=["GET", "POST"],
    ),
    Route(
        "/admin/users/{user_id}/change-role",
        endpoint=user_change_role,
        methods=["POST"],
    ),
    Route(
        "/admin/users/{user_id}/permissions",
        endpoint=user_permissions,
        methods=["GET"],
    ),
    Route(
        "/admin/users/{user_id}/permissions/{tool_id}/toggle",
        endpoint=user_toggle_permission,
        methods=["POST"],
    ),
    Route(
        "/admin/users/{user_id}/tokens/{token_id}/revoke",
        endpoint=user_revoke_token,
        methods=["POST"],
    ),
    Route(
        "/admin/users/{user_id}/tokens/revoke-all",
        endpoint=user_revoke_all_tokens,
        methods=["POST"],
    ),
]
