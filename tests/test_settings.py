import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import QueryParams

from mcp_anywhere.auth.models import User
from mcp_anywhere.base import Base
from mcp_anywhere.web.settings_model import InstanceSetting
from mcp_anywhere.web.settings_routes import (
    get_setting,
    get_setting_bool,
    get_setting_int,
    initialize_default_settings,
    settings_view,
)


@pytest.mark.asyncio
async def test_initialize_default_settings():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            await initialize_default_settings()

            async with TestSessionLocal() as session:
                from sqlalchemy import select

                result = await session.execute(select(InstanceSetting))
                settings = result.scalars().all()

                # Verify at least one setting was created
                assert len(settings) > 0

                # Verify the OAuth domain setting exists (as per current DEFAULT_SETTINGS)
                setting_keys = {s.key for s in settings}
                assert "oauth_user_allowed_domain" in setting_keys

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_model():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            settings = [
                InstanceSetting(
                    key="test_setting_1",
                    value="value1",
                    category="Test Category",
                    label="Test Setting 1",
                    description="Test description",
                    value_type="string",
                ),
                InstanceSetting(
                    key="test_setting_2",
                    value="123",
                    category="Test Category",
                    label="Test Setting 2",
                    value_type="integer",
                ),
                InstanceSetting(
                    key="test_boolean",
                    value="true",
                    category="Test Category",
                    label="Test Boolean",
                    value_type="boolean",
                ),
            ]
            session.add_all(settings)
            await session.commit()

            from sqlalchemy import select

            result = await session.execute(
                select(InstanceSetting).order_by(InstanceSetting.key)
            )
            queried_settings = result.scalars().all()

            assert len(queried_settings) == 3
            assert queried_settings[0].key == "test_boolean"
            assert queried_settings[0].value == "true"
            assert queried_settings[0].value_type == "boolean"
            assert queried_settings[1].key == "test_setting_1"
            assert queried_settings[1].value == "value1"
            assert queried_settings[2].key == "test_setting_2"
            assert queried_settings[2].value == "123"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

@pytest.mark.asyncio
async def test_get_setting_helpers():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            settings = [
                InstanceSetting(
                    key="test_string",
                    value="hello",
                    category="Test",
                    label="Test String",
                    value_type="string",
                ),
                InstanceSetting(
                    key="test_int",
                    value="42",
                    category="Test",
                    label="Test Integer",
                    value_type="integer",
                ),
                InstanceSetting(
                    key="test_bool_true",
                    value="true",
                    category="Test",
                    label="Test Boolean True",
                    value_type="boolean",
                ),
                InstanceSetting(
                    key="test_bool_false",
                    value="false",
                    category="Test",
                    label="Test Boolean False",
                    value_type="boolean",
                ),
            ]
            session.add_all(settings)
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            # Test get_setting
            value = await get_setting("test_string")
            assert value == "hello"

            # Test get_setting with default for missing key
            value = await get_setting("nonexistent", "default_value")
            assert value == "default_value"

            # Test get_setting_int
            int_value = await get_setting_int("test_int")
            assert int_value == 42
            assert isinstance(int_value, int)

            # Test get_setting_int with default for missing key
            int_value = await get_setting_int("nonexistent", 999)
            assert int_value == 999

            # Test get_setting_bool
            bool_value = await get_setting_bool("test_bool_true")
            assert bool_value is True

            bool_value = await get_setting_bool("test_bool_false")
            assert bool_value is False

            # Test get_setting_bool with default for missing key
            bool_value = await get_setting_bool("nonexistent", True)
            assert bool_value is True

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)

@pytest.mark.asyncio
async def test_settings_view_with_settings():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            settings = [
                InstanceSetting(
                    key="auth_timeout",
                    value="3600",
                    category="Authentication",
                    label="Auth Timeout",
                    description="Authentication timeout in seconds",
                    value_type="integer",
                ),
                InstanceSetting(
                    key="auth_enabled",
                    value="true",
                    category="Authentication",
                    label="Enable Authentication",
                    value_type="boolean",
                ),
                InstanceSetting(
                    key="server_host",
                    value="localhost",
                    category="Server",
                    label="Server Host",
                    value_type="string",
                ),
                InstanceSetting(
                    key="log_level",
                    value="INFO",
                    category="Logging",
                    label="Log Level",
                    value_type="select",
                ),
            ]
            session.add_all(settings)
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.query_params = QueryParams()

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.templates.TemplateResponse"
                ) as mock_template:
                    mock_template.return_value = MagicMock()

                    response = await settings_view(mock_request)

                    assert mock_template.called
                    call_args = mock_template.call_args

                    assert call_args[0][1] == "settings/view.html"

                    context = call_args[0][2]
                    assert "settings_by_category" in context

                    settings_by_category = context["settings_by_category"]
                    assert "Authentication" in settings_by_category
                    assert "Server" in settings_by_category
                    assert "Logging" in settings_by_category

                    assert len(settings_by_category["Authentication"]) == 2
                    assert len(settings_by_category["Server"]) == 1
                    assert len(settings_by_category["Logging"]) == 1

                    auth_settings = settings_by_category["Authentication"]
                    auth_keys = {s.key for s in auth_settings}
                    assert "auth_timeout" in auth_keys
                    assert "auth_enabled" in auth_keys

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_view_empty_settings():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.query_params = QueryParams()

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.templates.TemplateResponse"
                ) as mock_template:
                    mock_template.return_value = MagicMock()

                    response = await settings_view(mock_request)

                    assert mock_template.called
                    call_args = mock_template.call_args

                    context = call_args[0][2]
                    assert "settings_by_category" in context
                    assert len(context["settings_by_category"]) == 0

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_view_with_success_message():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.query_params = QueryParams("success=Settings updated successfully")

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.templates.TemplateResponse"
                ) as mock_template:
                    mock_template.return_value = MagicMock()

                    response = await settings_view(mock_request)

                    assert mock_template.called
                    call_args = mock_template.call_args

                    context = call_args[0][2]
                    assert "success" in context
                    assert context["success"] == "Settings updated successfully"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_view_with_error_message():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.query_params = QueryParams("error=Failed to update settings")

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.templates.TemplateResponse"
                ) as mock_template:
                    mock_template.return_value = MagicMock()

                    response = await settings_view(mock_request)

                    assert mock_template.called
                    call_args = mock_template.call_args

                    context = call_args[0][2]
                    assert "error" in context
                    assert context["error"] == "Failed to update settings"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_view_requires_admin():
    mock_request = MagicMock()
    mock_request.session = {}

    mock_user = MagicMock(spec=User)
    mock_user.username = "user"
    mock_user.is_admin = False
    mock_user.is_authenticated = True

    with patch(
        "mcp_anywhere.web.user_routes.get_current_user",
        return_value=mock_user,
    ):
        with patch(
            "mcp_anywhere.web.user_routes.templates.TemplateResponse"
        ) as mock_template:
            mock_template.return_value = MagicMock()

            response = await settings_view(mock_request)

            assert mock_template.called
            call_args = mock_template.call_args

            assert call_args[0][1] == "403.html"

            assert call_args[1]["status_code"] == 403


@pytest.mark.asyncio
async def test_settings_view_database_error():
    mock_request = MagicMock()
    mock_request.session = {}
    mock_request.query_params = QueryParams()

    mock_user = MagicMock(spec=User)
    mock_user.username = "admin"
    mock_user.is_admin = True
    mock_user.is_authenticated = True

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session_error():
        raise Exception("Database connection failed")

    with patch(
        "mcp_anywhere.web.settings_routes.get_async_session",
        side_effect=mock_session_error,
    ):
        with patch(
            "mcp_anywhere.web.user_routes.get_current_user",
            return_value=mock_user,
        ):
            with patch(
                "mcp_anywhere.web.settings_routes.templates.TemplateResponse"
            ) as mock_template:
                mock_template.return_value = MagicMock()

                response = await settings_view(mock_request)

                assert mock_template.called
                call_args = mock_template.call_args

                context = call_args[0][2]
                assert "error" in context
                assert "Failed to load settings" in context["error"]

                assert call_args[1]["status_code"] == 500


@pytest.mark.asyncio
async def test_settings_update_string_value():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            setting = InstanceSetting(
                key="test_host",
                value="localhost",
                category="Server",
                label="Test Host",
                value_type="string",
            )
            session.add(setting)
            await session.commit()

        from contextlib import asynccontextmanager
        from mcp_anywhere.web.settings_routes import settings_update

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.form = AsyncMock(return_value={"setting_test_host": "example.com"})

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.get_current_user",
                    return_value=mock_user,
                ):
                    response = await settings_update(mock_request)

                    from starlette.responses import RedirectResponse

                    assert isinstance(response, RedirectResponse)
                    assert "/admin/settings?success=" in response.headers["location"]

                    async with TestSessionLocal() as session:
                        from sqlalchemy import select

                        result = await session.execute(
                            select(InstanceSetting).where(
                                InstanceSetting.key == "test_host"
                            )
                        )
                        updated_setting = result.scalar_one()
                        assert updated_setting.value == "example.com"
                        assert updated_setting.updated_by == "admin"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_update_integer_value():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            setting = InstanceSetting(
                key="test_timeout",
                value="300",
                category="Server",
                label="Test Timeout",
                value_type="integer",
            )
            session.add(setting)
            await session.commit()

        from contextlib import asynccontextmanager
        from mcp_anywhere.web.settings_routes import settings_update

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.form = AsyncMock(return_value={"setting_test_timeout": "600"})

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.get_current_user",
                    return_value=mock_user,
                ):
                    response = await settings_update(mock_request)

                    from starlette.responses import RedirectResponse

                    assert isinstance(response, RedirectResponse)

                    async with TestSessionLocal() as session:
                        from sqlalchemy import select

                        result = await session.execute(
                            select(InstanceSetting).where(
                                InstanceSetting.key == "test_timeout"
                            )
                        )
                        updated_setting = result.scalar_one()
                        assert updated_setting.value == "600"
                        assert updated_setting.updated_by == "admin"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_update_boolean_checked():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            setting = InstanceSetting(
                key="test_enabled",
                value="false",
                category="Server",
                label="Test Enabled",
                value_type="boolean",
            )
            session.add(setting)
            await session.commit()

        from contextlib import asynccontextmanager
        from mcp_anywhere.web.settings_routes import settings_update

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.form = AsyncMock(return_value={"setting_test_enabled": "on"})

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.get_current_user",
                    return_value=mock_user,
                ):
                    with patch(
                        "mcp_anywhere.web.settings_routes.DEFAULT_SETTINGS",
                        [
                            {
                                "key": "test_enabled",
                                "value": "false",
                                "category": "Server",
                                "label": "Test Enabled",
                                "value_type": "boolean",
                            }
                        ],
                    ):
                        response = await settings_update(mock_request)

                        async with TestSessionLocal() as session:
                            from sqlalchemy import select

                            result = await session.execute(
                                select(InstanceSetting).where(
                                    InstanceSetting.key == "test_enabled"
                                )
                            )
                            updated_setting = result.scalar_one()
                            assert updated_setting.value == "true"
                            assert updated_setting.updated_by == "admin"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_update_boolean_unchecked():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            setting = InstanceSetting(
                key="test_enabled",
                value="true",
                category="Server",
                label="Test Enabled",
                value_type="boolean",
            )
            session.add(setting)
            await session.commit()

        from contextlib import asynccontextmanager
        from mcp_anywhere.web.settings_routes import settings_update

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.form = AsyncMock(return_value={})

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.get_current_user",
                    return_value=mock_user,
                ):
                    with patch(
                        "mcp_anywhere.web.settings_routes.DEFAULT_SETTINGS",
                        [
                            {
                                "key": "test_enabled",
                                "value": "true",
                                "category": "Server",
                                "label": "Test Enabled",
                                "value_type": "boolean",
                            }
                        ],
                    ):
                        response = await settings_update(mock_request)

                        async with TestSessionLocal() as session:
                            from sqlalchemy import select

                            result = await session.execute(
                                select(InstanceSetting).where(
                                    InstanceSetting.key == "test_enabled"
                                )
                            )
                            updated_setting = result.scalar_one()
                            assert updated_setting.value == "false"
                            assert updated_setting.updated_by == "admin"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_update_multiple_settings():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            settings = [
                InstanceSetting(
                    key="setting1",
                    value="value1",
                    category="Test",
                    label="Setting 1",
                    value_type="string",
                ),
                InstanceSetting(
                    key="setting2",
                    value="100",
                    category="Test",
                    label="Setting 2",
                    value_type="integer",
                ),
                InstanceSetting(
                    key="setting3",
                    value="false",
                    category="Test",
                    label="Setting 3",
                    value_type="boolean",
                ),
            ]
            session.add_all(settings)
            await session.commit()

        from contextlib import asynccontextmanager
        from mcp_anywhere.web.settings_routes import settings_update

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.form = AsyncMock(
            return_value={
                "setting_setting1": "new_value",
                "setting_setting2": "200",
                "setting_setting3": "on",
            }
        )

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.get_current_user",
                    return_value=mock_user,
                ):
                    with patch(
                        "mcp_anywhere.web.settings_routes.DEFAULT_SETTINGS",
                        [
                            {
                                "key": "setting3",
                                "value": "false",
                                "category": "Test",
                                "label": "Setting 3",
                                "value_type": "boolean",
                            }
                        ],
                    ):
                        response = await settings_update(mock_request)

                        async with TestSessionLocal() as session:
                            from sqlalchemy import select

                            result = await session.execute(
                                select(InstanceSetting).order_by(InstanceSetting.key)
                            )
                            updated_settings = result.scalars().all()

                            assert updated_settings[0].value == "new_value"
                            assert updated_settings[0].updated_by == "admin"

                            assert updated_settings[1].value == "200"
                            assert updated_settings[1].updated_by == "admin"

                            assert updated_settings[2].value == "true"
                            assert updated_settings[2].updated_by == "admin"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_update_no_changes():

    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_db:
        db_path = tmp_db.name

    try:
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        TestSessionLocal = sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with TestSessionLocal() as session:
            setting = InstanceSetting(
                key="test_host",
                value="localhost",
                category="Server",
                label="Test Host",
                value_type="string",
                updated_by="previous_admin",
            )
            session.add(setting)
            await session.commit()

        from contextlib import asynccontextmanager
        from mcp_anywhere.web.settings_routes import settings_update

        @asynccontextmanager
        async def mock_session_context():
            async with TestSessionLocal() as session:
                yield session

        mock_request = MagicMock()
        mock_request.session = {}
        mock_request.form = AsyncMock(return_value={"setting_test_host": "localhost"})

        mock_user = MagicMock(spec=User)
        mock_user.username = "admin"
        mock_user.is_admin = True
        mock_user.is_authenticated = True

        with patch(
            "mcp_anywhere.web.settings_routes.get_async_session",
            side_effect=mock_session_context,
        ):
            with patch(
                "mcp_anywhere.web.user_routes.get_current_user",
                return_value=mock_user,
            ):
                with patch(
                    "mcp_anywhere.web.settings_routes.get_current_user",
                    return_value=mock_user,
                ):
                    response = await settings_update(mock_request)

                    async with TestSessionLocal() as session:
                        from sqlalchemy import select

                        result = await session.execute(
                            select(InstanceSetting).where(
                                InstanceSetting.key == "test_host"
                            )
                        )
                        setting_check = result.scalar_one()
                        assert setting_check.value == "localhost"
                        assert setting_check.updated_by == "previous_admin"

        await test_engine.dispose()

    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.mark.asyncio
async def test_settings_update_requires_admin():

    mock_request = MagicMock()
    mock_request.session = {}

    mock_user = MagicMock(spec=User)
    mock_user.username = "user"
    mock_user.is_admin = False
    mock_user.is_authenticated = True

    from mcp_anywhere.web.settings_routes import settings_update

    with patch(
        "mcp_anywhere.web.user_routes.get_current_user",
        return_value=mock_user,
    ):
        with patch(
            "mcp_anywhere.web.user_routes.templates.TemplateResponse"
        ) as mock_template:
            mock_template.return_value = MagicMock()

            response = await settings_update(mock_request)

            assert mock_template.called
            call_args = mock_template.call_args
            assert call_args[0][1] == "403.html"
            assert call_args[1]["status_code"] == 403


@pytest.mark.asyncio
async def test_settings_update_database_error():

    from contextlib import asynccontextmanager
    from mcp_anywhere.web.settings_routes import settings_update

    def mock_session_error():
        @asynccontextmanager
        async def _error_context():
            raise Exception("Database connection failed")
        return _error_context()

    mock_request = MagicMock()
    mock_request.session = {}
    mock_request.form = AsyncMock(return_value={"setting_test": "value"})

    mock_user = MagicMock(spec=User)
    mock_user.username = "admin"
    mock_user.is_admin = True
    mock_user.is_authenticated = True

    with patch(
        "mcp_anywhere.web.settings_routes.get_async_session",
        side_effect=mock_session_error,
    ):
        with patch(
            "mcp_anywhere.web.user_routes.get_current_user",
            return_value=mock_user,
        ):
            with patch(
                "mcp_anywhere.web.settings_routes.get_current_user",
                return_value=mock_user,
            ):
                response = await settings_update(mock_request)

                from starlette.responses import RedirectResponse
                from urllib.parse import unquote

                assert isinstance(response, RedirectResponse)
                location = response.headers["location"]
                assert "/admin/settings?error=" in location

                decoded_location = unquote(location)
                assert "Failed to update settings" in decoded_location