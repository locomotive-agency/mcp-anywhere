"""Pydantic models for form validation."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServerFormData(BaseModel):
    """Form data for adding/editing MCP servers."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=100)
    github_url: str = Field(..., max_length=500)
    description: str | None = Field(None, max_length=500)
    runtime_type: str = Field(...)
    install_command: str = Field(..., min_length=1, max_length=500)
    start_command: str = Field(..., max_length=500)
    env_variables: list[dict] = Field(default_factory=list)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        """Validate GitHub URL format."""
        if v:
            pattern = r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$"
            if not re.match(pattern, v.rstrip("/")):
                raise ValueError("Please enter a valid GitHub repository URL")
        return v

    @field_validator("runtime_type")
    @classmethod
    def validate_runtime_type(cls, v):
        """Validate runtime type is one of allowed values."""
        allowed_types = ["npx", "uvx", "docker"]
        if v not in allowed_types:
            raise ValueError(f"Runtime type must be one of: {', '.join(allowed_types)}")
        return v


class AnalyzeFormData(BaseModel):
    """Form data for analyzing a GitHub repository."""

    model_config = ConfigDict(str_strip_whitespace=True)

    github_url: str = Field(..., max_length=500)

    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v):
        """Validate GitHub URL format."""
        if v:
            pattern = r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$"
            if not re.match(pattern, v.rstrip("/")):
                raise ValueError("Please enter a valid GitHub repository URL")
        return v
