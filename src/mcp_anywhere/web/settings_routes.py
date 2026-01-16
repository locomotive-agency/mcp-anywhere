from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from mcp_anywhere.config import Config
from mcp_anywhere.database import get_async_session
from mcp_anywhere.logging_config import get_logger
from mcp_anywhere.web.routes import get_current_user, get_template_context
from mcp_anywhere.web.settings_model import InstanceSetting
from mcp_anywhere.web.user_routes import require_admin_role

logger = get_logger(__name__)
templates = Jinja2Templates(directory="src/mcp_anywhere/web/templates")

DEFAULT_SETTINGS = [
    {
        "key": "oauth_user_allowed_domain",
        "value": Config.OAUTH_USER_ALLOWED_DOMAIN or "",
        "category": "OAuth",
        "label": "Allowed OAuth Domain",
        "description": "Restrict OAuth users to a specific domain (e.g., company.com)",
        "value_type": "string",
    },
]


async def get_setting(key: str, default: str | None = None) -> str | None:
    try:
        async with get_async_session() as session:
            stmt = select(InstanceSetting).where(InstanceSetting.key == key)
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()

            if setting:
                return setting.value
            return default
    except Exception as e:
        logger.warning(f"Error retrieving setting '{key}': {e}")
        return default


async def get_setting_bool(key: str, default: bool = False) -> bool:
    value = await get_setting(key, str(default).lower())
    return value == "true"


async def get_setting_int(key: str, default: int = 0) -> int:
    value = await get_setting(key, str(default))
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid integer value for setting '{key}': {value}")
        return default


async def initialize_default_settings():
    async with get_async_session() as session:
        for setting_data in DEFAULT_SETTINGS:

            stmt = select(InstanceSetting).where(
                InstanceSetting.key == setting_data["key"]
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                setting = InstanceSetting(
                    key=setting_data["key"],
                    value=setting_data["value"],
                    category=setting_data["category"],
                    label=setting_data["label"],
                    description=setting_data.get("description"),
                    value_type=setting_data["value_type"],
                )
                session.add(setting)

        await session.commit()
        logger.info("Initialized default instance settings")


@require_admin_role
async def settings_view(request: Request) -> HTMLResponse:
    try:
        async with get_async_session() as session:
            stmt = select(InstanceSetting).order_by(
                InstanceSetting.category, InstanceSetting.key
            )
            result = await session.execute(stmt)
            all_settings = result.scalars().all()

            settings_by_category = {}
            for setting in all_settings:
                if setting.category not in settings_by_category:
                    settings_by_category[setting.category] = []
                settings_by_category[setting.category].append(setting)

            settings_options = {}
            for setting_data in DEFAULT_SETTINGS:
                if setting_data["value_type"] == "select":
                    settings_options[setting_data["key"]] = setting_data.get(
                        "options", []
                    )

            context = get_template_context(
                request,
                settings_by_category=settings_by_category,
                settings_options=settings_options,
            )
            return templates.TemplateResponse(request, "settings/view.html", context)

    except Exception as e:
        logger.exception(f"Error loading settings: {e}")
        context = get_template_context(
            request, error=f"Failed to load settings: {str(e)}"
        )
        return templates.TemplateResponse(
            request, "settings/view.html", context, status_code=500
        )


@require_admin_role
async def settings_update(request: Request) -> Response:
    try:
        form_data = await request.form()
        current_user = get_current_user(request)

        async with get_async_session() as session:
            updated_count = 0

            for key, value in form_data.items():
                if key.startswith("setting_"):
                    setting_key = key.replace("setting_", "")

                    stmt = select(InstanceSetting).where(
                        InstanceSetting.key == setting_key
                    )
                    result = await session.execute(stmt)
                    setting = result.scalar_one_or_none()

                    if setting:
                        if setting.value_type == "boolean":
                            new_value = "true" if value == "on" else "false"
                        else:
                            new_value = value

                        if setting.value != new_value:
                            setting.value = new_value
                            setting.updated_by = current_user.username
                            updated_count += 1

            for setting_data in DEFAULT_SETTINGS:
                if setting_data["value_type"] == "boolean":
                    key = f"setting_{setting_data['key']}"
                    if key not in form_data:
                        stmt = select(InstanceSetting).where(
                            InstanceSetting.key == setting_data["key"]
                        )
                        result = await session.execute(stmt)
                        setting = result.scalar_one_or_none()

                        if setting and setting.value != "false":
                            setting.value = "false"
                            setting.updated_by = current_user.username
                            updated_count += 1

            await session.commit()
            logger.info(
                f"Updated {updated_count} settings by user {current_user.username}"
            )

            return RedirectResponse(
                url="/admin/settings?success=Settings updated successfully",
                status_code=302,
            )

    except Exception as e:
        logger.exception(f"Error updating settings: {e}")
        return RedirectResponse(
            url=f"/admin/settings?error=Failed to update settings: {str(e)}",
            status_code=302,
        )

# Routes
settings_routes = [
    Route("/admin/settings", settings_view, methods=["GET"]),
    Route("/admin/settings/update", settings_update, methods=["POST"]),
]