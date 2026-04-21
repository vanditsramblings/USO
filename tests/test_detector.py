"""Tests for auto-detection engine."""

from uso.detector import detect


def test_detect_python_environ():
    code = '''"""Fetch data from API."""
import os
url = os.environ.get("API_URL")
token = os.getenv("API_TOKEN")
secret = os.environ["DB_PASSWORD"]
'''
    result = detect(code, "py")
    assert result.description == "Fetch data from API."
    keys = {p.key for p in result.parameters}
    assert "API_URL" in keys
    assert "API_TOKEN" in keys
    assert "DB_PASSWORD" in keys
    # DB_PASSWORD should be detected as secret
    secrets = {p.key for p in result.parameters if p.is_secret}
    assert "DB_PASSWORD" in secrets


def test_detect_python_argparse():
    code = '''import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", required=True)
parser.add_argument("--batch-size", type=int)
'''
    result = detect(code, "py")
    keys = {p.key for p in result.parameters}
    assert "OUTPUT_DIR" in keys
    assert "BATCH_SIZE" in keys


def test_detect_python_tags():
    code = "import pandas as pd\ndf = pd.read_csv('data.csv')"
    result = detect(code, "py")
    assert "ETL" in result.tags


def test_detect_shell_vars():
    code = """#!/bin/bash
# Deploy containers to production
docker build -t $IMAGE_NAME .
curl -H "Authorization: Bearer ${API_TOKEN}" $DEPLOY_URL
"""
    result = detect(code, "sh")
    assert result.description == "Deploy containers to production"
    keys = {p.key for p in result.parameters}
    assert "IMAGE_NAME" in keys
    assert "API_TOKEN" in keys
    assert "DEPLOY_URL" in keys
    # API_TOKEN should be secret
    secrets = {p.key for p in result.parameters if p.is_secret}
    assert "API_TOKEN" in secrets
    assert "DevOps" in result.tags


def test_detect_javascript():
    code = """// Sync users from external API
const url = process.env.API_URL;
const secret = process.env['AUTH_SECRET'];
fetch(url);
"""
    result = detect(code, "js")
    assert "Sync users from external API" in result.description
    keys = {p.key for p in result.parameters}
    assert "API_URL" in keys
    assert "AUTH_SECRET" in keys
    secrets = {p.key for p in result.parameters if p.is_secret}
    assert "AUTH_SECRET" in secrets
    assert "API" in result.tags


def test_detect_unknown_runtime():
    result = detect("hello", "rb")
    assert result.description == ""
    assert result.parameters == []


def test_detect_python_docstring_multiline():
    code = '''"""This is the first line.
More details here.
"""
print("hi")
'''
    result = detect(code, "py")
    assert result.description == "This is the first line."


def test_detect_shell_skips_builtin_vars():
    code = "echo $HOME $USER $PATH $MY_VAR"
    result = detect(code, "sh")
    keys = {p.key for p in result.parameters}
    assert "HOME" not in keys
    assert "PATH" not in keys
    assert "MY_VAR" in keys
