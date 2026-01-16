import os
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from mcp_anywhere.base import Base
from mcp_anywhere.web.settings_model import InstanceSetting
from mcp_anywhere.web.settings_routes import (
    get_setting,
    get_setting_bool,
    get_setting_int,
    initialize_default_settings,
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